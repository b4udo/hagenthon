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
) -> tuple[EsitoSemplificazione, int]:
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
        cosa_vogliono=plain_rules.azione_richiesta(corpo)
        or "Le danno un'informazione. Non deve fare nulla.",
        entro_quando=_entro_quando(fatti),
        testo_semplificato=plain_rules.semplifica_testo(corpo),
    )


def _chi_scrive(mittente_nome: str, categoria: Categoria) -> str:
    match categoria:
        case Categoria.SANITA:
            return f"{mittente_nome}, per la sua salute"
        case Categoria.ENTE_PUBBLICO:
            return f"{mittente_nome}, un ufficio pubblico"
        case Categoria.PERSONA_CONOSCIUTA:
            return mittente_nome
        case Categoria.COMMERCIALE:
            return f"{mittente_nome} (pubblicita')"
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
