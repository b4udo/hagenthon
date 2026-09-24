"""02 · Sicurezza — semaforo e azione.

Specifica: agents/runtime/02-sicurezza.md

Nessuna seam LLM, per scelta. Un semaforo senza pulsante e' un checker
travestito da assistente: qui ogni verdetto porta un'azione eseguibile.
"""

from __future__ import annotations

from ..contracts import AzioneSuggerita, EsitoSicurezza, Semaforo, TipoAzione
from ..engines import phishing_rules

NOME_PERSONA_FIDUCIA = "Luca"

MESSAGGI = {
    "rosso": "Non risponda a questa email. Sembra una truffa.",
    "giallo": f"Non sono sicuro. Chieda a {NOME_PERSONA_FIDUCIA} prima di rispondere.",
    "verde": "Puo' rispondere tranquillamente.",
}


def esegui(
    mittente_nome: str,
    mittente_email: str,
    oggetto: str,
    corpo: str,
    in_rubrica: bool,
) -> EsitoSicurezza:
    semaforo, segnali, ente = phishing_rules.valuta(
        mittente_nome, mittente_email, oggetto, corpo, in_rubrica
    )
    return EsitoSicurezza(
        semaforo=Semaforo(semaforo),
        messaggio=MESSAGGI[semaforo],
        segnali=segnali,
        azione=_azione(semaforo, ente),
    )


def _azione(semaforo: str, ente: dict | None) -> AzioneSuggerita:
    if semaforo == "rosso":
        # ★ Il numero viene dalla tabella statica, mai dal corpo dell'email:
        # su una mail di phishing il numero nel testo e' del truffatore.
        if ente:
            return AzioneSuggerita(
                tipo=TipoAzione.TELEFONO,
                etichetta=f"Chiami {ente['nome']} al numero ufficiale",
                valore=str(ente["telefono"]),
            )
        return AzioneSuggerita(
            tipo=TipoAzione.INOLTRA,
            etichetta=f"Manda questa email a {NOME_PERSONA_FIDUCIA}",
            valore=None,
        )

    if semaforo == "giallo":
        return AzioneSuggerita(
            tipo=TipoAzione.INOLTRA,
            etichetta=f"Manda questa email a {NOME_PERSONA_FIDUCIA}",
            valore=None,
        )

    return AzioneSuggerita(
        tipo=TipoAzione.RISPONDI,
        etichetta="Prepara una risposta",
        valore=None,
    )


def fallback() -> EsitoSicurezza:
    """Un controllo che non e' riuscito non e' un controllo superato."""
    return EsitoSicurezza(
        semaforo=Semaforo.GIALLO,
        messaggio=(
            "Non sono riuscito a controllare questa email. "
            f"Chieda a {NOME_PERSONA_FIDUCIA} prima di rispondere."
        ),
        segnali=["Il controllo di sicurezza non e' andato a buon fine."],
        azione=AzioneSuggerita(
            tipo=TipoAzione.INOLTRA,
            etichetta=f"Manda questa email a {NOME_PERSONA_FIDUCIA}",
            valore=None,
        ),
    )
