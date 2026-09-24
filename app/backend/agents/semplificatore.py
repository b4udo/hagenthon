"""04 · Semplificatore — Chi scrive · Cosa vogliono · Entro quando.

Specifica: agents/runtime/04-semplificatore.md

Il suo output non raggiunge mai l'interfaccia senza passare dall'agente 05:
questo agente non ha l'ultima parola sul proprio risultato.
"""

from __future__ import annotations

import json

from ..contracts import Categoria, EsitoSemplificazione, Fatto
from ..engines import normalize, plain_rules
from ..llm import client

ANCORE_SCADENZA = ("entro", "scadenza", "scade", "termine")


def esegui(
    mittente_nome: str,
    oggetto: str,
    corpo: str,
    categoria: Categoria,
    fatti: list[Fatto],
    feedback: str | None = None,
    solo_regole: bool = False,
) -> tuple[EsitoSemplificazione, int]:
    """`solo_regole` e' come l'orchestratore fa rispettare il budget di token.

    Senza questo interruttore il budget sarebbe misurabile ma non vincolante:
    l'orchestratore ne annotava il superamento e poi attraversava la seam
    lo stesso. Un limite che non limita non e' un limite.
    """
    if not solo_regole:
        risposta = _prova_seam(mittente_nome, oggetto, corpo, fatti, feedback)
        if risposta is not None:
            return risposta

    return _a_regole(mittente_nome, corpo, categoria, fatti), 0


def _a_regole(
    mittente_nome: str,
    corpo: str,
    categoria: Categoria,
    fatti: list[Fatto],
) -> EsitoSemplificazione:
    return EsitoSemplificazione(
        chi_scrive=_chi_scrive(mittente_nome, categoria),
        cosa_vogliono=_cosa_vogliono(corpo, fatti),
        entro_quando=_entro_quando(fatti),
        testo_semplificato=plain_rules.semplifica_testo(corpo),
    )


def _cosa_vogliono(corpo: str, fatti: list[Fatto]) -> str:
    """La richiesta, e **a cosa si riferisce**.

    «Le chiedono di confermare.» e' vero e inutile: confermare cosa? La riga
    che Maria legge per prima deve bastare da sola, senza costringerla a
    scendere nel testo per capire di che appuntamento si parla.

    I complementi vengono **solo dai fatti gia' estratti e ancorati**: data,
    orario, importo. Nessuna inferenza sul contenuto, quindi nessun rischio di
    aggiungere qualcosa che nell'originale non c'e'.
    """
    azione = plain_rules.azione_richiesta(corpo)
    if azione is None:
        base = "Le danno un'informazione. Non deve fare nulla."
        importo = _primo(fatti, "importo")
        # Un'informativa su un importo senza dire l'importo non informa.
        return f"{base} Riguarda {importo}." if importo else base

    pezzi: list[str] = []
    data = _primo_normalizzato(fatti, "data")
    orario = _primo(fatti, "orario")
    importo = _primo(fatti, "importo")

    if data:
        pezzi.append(f"del {normalize.formatta_data_italiana(data)}")
    if orario:
        pezzi.append(f"alle {orario}")
    if importo:
        pezzi.append(f"per {importo}")

    if not pezzi:
        return azione
    # ★ Frase a parte, non complemento attaccato al verbo.
    #
    # «Le chiedono di confermare del 14 ottobre» e' italiano rotto: il
    # complemento giusto dipende dal verbo («confermare **l'appuntamento**
    # del…», «ritirare **il documento** del…»), e il verbo qui e' una variabile.
    # Una seconda frase autonoma regge con qualunque azione senza doverne
    # conoscere l'oggetto — la stessa ragione per cui il semplificatore lavora
    # su locuzioni intere invece che su singole parole.
    return f"{azione} Si tratta {' '.join(pezzi)}."


def _primo(fatti: list[Fatto], tipo: str) -> str | None:
    for fatto in fatti:
        if fatto.tipo.value == tipo:
            return fatto.testo_originale
    return None


def _primo_normalizzato(fatti: list[Fatto], tipo: str) -> str | None:
    for fatto in fatti:
        if fatto.tipo.value == tipo:
            return fatto.valore_normalizzato
    return None


def _chi_scrive(mittente_nome: str, categoria: Categoria) -> str:
    match categoria:
        case Categoria.SANITA:
            return f"{mittente_nome}, per la sua salute"
        case Categoria.ENTE_PUBBLICO:
            return f"{mittente_nome}, un ufficio pubblico"
        case Categoria.PERSONA_CONOSCIUTA:
            return mittente_nome
        case Categoria.COMMERCIALE:
            return f"{mittente_nome} (pubblicità)"
        case _:
            return mittente_nome


def _entro_quando(fatti: list[Fatto]) -> str | None:
    """Solo da un fatto gia' estratto. Una scadenza inventata e' un danno."""
    for fatto in fatti:
        if fatto.tipo.value == "data" and fatto.ancora in ANCORE_SCADENZA:
            return f"Entro il {normalize.formatta_data_italiana(fatto.valore_normalizzato)}"
    return None


def _prova_seam(
    mittente_nome: str,
    oggetto: str,
    corpo: str,
    fatti: list[Fatto],
    feedback: str | None,
) -> tuple[EsitoSemplificazione, int] | None:
    elenco_fatti = "\n".join(
        f"- {f.tipo.value}: {f.testo_originale}" for f in fatti
    ) or "(nessuno)"

    risposta = client.invoca(
        "semplificatore",
        client.MODELLO_LINGUA,
        {
            "mittente_nome": mittente_nome,
            "oggetto": oggetto,
            "corpo": corpo[:3000],
            "fatti": elenco_fatti,
            "feedback": feedback or "(primo tentativo)",
        },
    )
    if risposta is None:
        return None

    try:
        dati = json.loads(risposta.contenuto)
        return EsitoSemplificazione.model_validate(dati), risposta.token
    except (json.JSONDecodeError, ValueError):
        return None
