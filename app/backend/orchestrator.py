"""L'orchestratore della pipeline.

Specifica: agents/runtime/orchestrator.md

Non e' un LLM. E' l'unico punto che possiede l'ordine degli agenti, i limiti e
lo stato. Una regola sopra tutte:

    l'orchestratore non ha il diritto di restituire un errore all'interfaccia.

Maria deve sempre vedere qualcosa. Nel caso peggiore, l'email originale.
"""

from __future__ import annotations

import logging
import time
from typing import Callable, TypeVar

from . import clock
from .agents import compositore, semplificatore, sicurezza, triage, verificatore
from .contracts import (
    Categoria,
    Email,
    EsitoAgente,
    EsitoSemplificazione,
    EsitoVerifica,
    ModalitaAgente,
    RisultatoPipeline,
    Semaforo,
    TracciaAgente,
)
from .engines import fact_extract
from .llm import client
from .state import store

logger = logging.getLogger(__name__)

MAX_SIMPLIFY_RETRIES = 2
TIMEOUT_AGENTE_MS = 2000
BUDGET_TOKEN_EMAIL = 4000
SOGLIA_CORPO_BREVE = 200
SOGLIA_CORPO_SENZA_FATTI = 400

T = TypeVar("T")


class _Corsa:
    """Accumula tracce e token lungo la pipeline."""

    def __init__(self) -> None:
        self.tracce: list[TracciaAgente] = []
        self.token = 0

    def budget_residuo(self) -> bool:
        return self.token < BUDGET_TOKEN_EMAIL

    def esegui(
        self,
        nome: str,
        azione: Callable[[], tuple[T, int]],
        ripiego: Callable[[], T],
        nota: str = "",
    ) -> T:
        """Esegue un agente isolandone i guasti.

        Un'eccezione non uccide la pipeline: la degrada. Il superamento del
        tempo massimo e' un controllo a valle (una scadenza, non una
        cancellazione preventiva): con motori a regole e' la lettura onesta.
        """
        inizio = time.perf_counter()
        try:
            valore, token = azione()
            esito = EsitoAgente.OK
        except Exception as errore:  # noqa: BLE001 — la rete di sicurezza e' qui
            logger.warning("agente %s fallito: %s", nome, errore)
            valore, token, esito = ripiego(), 0, EsitoAgente.ERRORE
            nota = nota or f"errore: {errore}"

        durata = int((time.perf_counter() - inizio) * 1000)

        if esito is EsitoAgente.OK and durata > TIMEOUT_AGENTE_MS:
            logger.warning("agente %s oltre il tempo massimo (%d ms)", nome, durata)
            valore, token, esito = ripiego(), 0, EsitoAgente.FALLBACK
            nota = f"oltre {TIMEOUT_AGENTE_MS} ms, applicato il ripiego"

        self.token += token
        self.tracce.append(
            TracciaAgente(
                agente=nome,
                modalita=ModalitaAgente.LLM_REPLAY if token else ModalitaAgente.REGOLE,
                durata_ms=durata,
                esito=esito,
                nota=nota,
                token=token,
            )
        )
        return valore

    def salta(self, nome: str, perche: str) -> None:
        self.tracce.append(
            TracciaAgente(
                agente=nome,
                modalita=ModalitaAgente.REGOLE,
                durata_ms=0,
                esito=EsitoAgente.OK,
                nota=f"non eseguito: {perche}",
                token=0,
            )
        )


def _serve_semplificare(email: Email, semaforo: Semaforo, categoria: Categoria, fatti) -> str:
    """Stringa vuota => si semplifica. Altrimenti, il motivo per non farlo.

    Le regole di non-chiamata di agents/runtime/routing.md, rese eseguibili.
    """
    if semaforo is Semaforo.ROSSO:
        return "email sospetta, non si semplifica un testo a cui non va risposto"
    if categoria is Categoria.COMMERCIALE:
        return "pubblicita': va messa in secondo piano, non tradotta"
    if categoria is Categoria.PERSONA_CONOSCIUTA:
        # La categoria, non la rubrica: lo studio medico e' in rubrica ma
        # scrive comunque in burocratese, e va semplificato.
        return "una persona conosciuta non scrive in burocratese"
    if len(email.corpo) < SOGLIA_CORPO_BREVE:
        return "messaggio gia' breve e chiaro"
    if not fatti and len(email.corpo) < SOGLIA_CORPO_SENZA_FATTI:
        return "nessun fatto da preservare e testo gia' corto"
    return ""


def elabora(
    email: Email,
    nome_utente: str = "Maria Rossi",
    avvelena: bool = False,
    riusa_stato: bool = True,
) -> RisultatoPipeline:
    # Ri-processare un'email gia' vista costa zero: in demo e' il caso normale.
    if riusa_stato and not avvelena:
        salvato = store.carica(email.id)
        if salvato is not None:
            return salvato

    corsa = _Corsa()
    anno = clock.anno_corrente()

    # ── 1 · triage ──
    esito_triage = corsa.esegui(
        "01-triage",
        lambda: triage.esegui(
            email.mittente_nome,
            email.mittente_email,
            email.oggetto,
            email.corpo,
            email.in_rubrica,
        ),
        triage.fallback,
    )

    # ── 2 · sicurezza ──
    esito_sicurezza = corsa.esegui(
        "02-sicurezza",
        lambda: (
            sicurezza.esegui(
                email.mittente_nome,
                email.mittente_email,
                email.oggetto,
                email.corpo,
                email.in_rubrica,
            ),
            0,
        ),
        sicurezza.fallback,
    )

    # ── 3 · estrazione fatti ──
    fatti = corsa.esegui(
        "03-estrazione-fatti",
        lambda: (fact_extract.estrai_fatti(email.corpo, anno), 0),
        lambda: [],
    )

    # ── 4+5 · ciclo semplifica / verifica ──
    semplificazione: EsitoSemplificazione | None = None
    verifica: EsitoVerifica | None = None
    mostrata = False

    motivo_salto = _serve_semplificare(
        email, esito_sicurezza.semaforo, esito_triage.categoria, fatti
    )
    if motivo_salto:
        corsa.salta("04-semplificatore", motivo_salto)
        corsa.salta("05-verificatore", "niente da verificare")
    else:
        feedback: str | None = None
        for tentativo in range(MAX_SIMPLIFY_RETRIES + 1):
            etichetta = f"04-semplificatore (tentativo {tentativo + 1})"

            if not corsa.budget_residuo():
                corsa.salta(etichetta, "budget di token esaurito, si usano le regole")

            semplificazione = corsa.esegui(
                etichetta,
                lambda f=feedback: semplificatore.esegui(
                    email.mittente_nome,
                    email.oggetto,
                    email.corpo,
                    esito_triage.categoria,
                    fatti,
                    f,
                ),
                lambda: EsitoSemplificazione(
                    chi_scrive=email.mittente_nome,
                    cosa_vogliono="Non sono riuscito a riassumere questa email.",
                    entro_quando=None,
                    testo_semplificato=email.corpo,
                ),
            )

            testo = semplificazione.testo_semplificato
            if avvelena:
                # Espediente da demo, dichiarato: vedi 05-verificatore.md.
                testo = verificatore.avvelena(testo)
                semplificazione = semplificazione.model_copy(
                    update={"testo_semplificato": testo}
                )

            verifica = corsa.esegui(
                f"05-verificatore (tentativo {tentativo + 1})",
                lambda: (verificatore.verifica(fatti, testo, anno, email.corpo), 0),
                lambda: EsitoVerifica(
                    passa=False,
                    problemi=[],
                    feedback_per_retry=None,
                ),
            )

            if verifica.passa:
                mostrata = True
                break

            feedback = verifica.feedback_per_retry

        if not mostrata:
            logger.info("FactGuard ha rifiutato: si mostra l'originale per %s", email.id)

    # ── 6 · compositore ──
    bozze = []
    if esito_sicurezza.semaforo is Semaforo.ROSSO:
        corsa.salta(
            "06-compositore",
            "email sospetta: l'azione giusta e' telefonare all'ente, non rispondere",
        )
    elif esito_triage.categoria is Categoria.COMMERCIALE:
        corsa.salta("06-compositore", "a una pubblicita' non si risponde")
    else:
        fatti_verificati = fatti if mostrata else fatti
        bozze = corsa.esegui(
            "06-compositore",
            lambda: compositore.esegui(
                email.mittente_nome, esito_triage.categoria, fatti_verificati, nome_utente
            ),
            lambda: [],
        )

    risultato = RisultatoPipeline(
        email_id=email.id,
        triage=esito_triage,
        sicurezza=esito_sicurezza,
        fatti=fatti,
        semplificazione=semplificazione,
        verifica=verifica,
        bozze=bozze,
        semplificazione_mostrata=mostrata,
        tracce=corsa.tracce,
        token_usati=corsa.token,
    )

    if not avvelena:
        store.salva(risultato)
    return risultato


def modalita_llm() -> str:
    return client.modalita()
