"""01 · Triage — categoria e priorita'.

Specifica: agents/runtime/01-triage.md

Il triage non giudica la sicurezza: `sconosciuto` non significa «sospetto».
Quel verdetto appartiene all'agente 02, che ha regole proprie. Sovrapporre le
due cose produrrebbe due fonti di verita' in disaccordo.
"""

from __future__ import annotations

import json

from ..contracts import Categoria, EsitoTriage, Priorita
from ..engines.phishing_rules import dominio_di
from ..llm import client

DOMINI_SANITA = ("aslcittaditorino.it", "asl", "ospedale", "studiobianchi", "medico")
DOMINI_ENTE = ("inps.it", "comune.torino.it", "agenziaentrate.gov.it", ".gov.it")

MARCATORI_COMMERCIALI = (
    "offerta",
    "offerte",
    "sconto",
    "sconti",
    "promozione",
    "promozioni",
    "newsletter",
    "disiscriv",
    "saldi",
    "volantino",
)

MARCATORI_AZIONE = (
    "confermare",
    "conferma",
    "entro",
    "scadenza",
    "presentarsi",
    "rispondere",
    "ritirare",
    "ritiro",
    "pagare",
    "compilare",
)


def esegui(
    mittente_nome: str,
    mittente_email: str,
    oggetto: str,
    corpo: str,
    in_rubrica: bool,
) -> tuple[EsitoTriage, int]:
    """Restituisce (esito, token consumati)."""
    risposta = _prova_seam(mittente_nome, mittente_email, oggetto, corpo)
    if risposta is not None:
        return risposta

    return _a_regole(mittente_nome, mittente_email, oggetto, corpo, in_rubrica), 0


def _a_regole(
    mittente_nome: str,
    mittente_email: str,
    oggetto: str,
    corpo: str,
    in_rubrica: bool,
) -> EsitoTriage:
    dominio = dominio_di(mittente_email)
    testo = f"{oggetto} {corpo}".lower()

    # L'appartenenza alla rubrica NON decide la categoria: lo studio medico
    # e' in rubrica ma resta sanita', e trattarlo come "persona conosciuta"
    # gli toglierebbe la semplificazione proprio nel caso d'uso principale.
    # La rubrica pesa sulla sicurezza (agente 02), non qui.
    if any(s in dominio for s in DOMINI_SANITA):
        categoria = Categoria.SANITA
        confidenza = 0.9
        motivo = f"Le scrive {mittente_nome} per motivi di salute."
    elif any(dominio.endswith(d.lstrip(".")) or d in dominio for d in DOMINI_ENTE):
        categoria = Categoria.ENTE_PUBBLICO
        confidenza = 0.9
        motivo = f"Le scrive {mittente_nome}, un ufficio pubblico."
    elif in_rubrica:
        categoria = Categoria.PERSONA_CONOSCIUTA
        confidenza = 0.95
        motivo = f"Le scrive {mittente_nome}, che conosce."
    elif any(m in testo for m in MARCATORI_COMMERCIALI):
        return EsitoTriage(
            categoria=Categoria.COMMERCIALE,
            priorita=Priorita.SECONDO_PIANO,
            motivo="E' pubblicita'. Puo' leggerla con calma o lasciarla stare.",
            confidenza=0.85,
        )
    else:
        categoria = Categoria.SCONOSCIUTO
        confidenza = 0.5
        motivo = "Non conosco chi le scrive."

    priorita = (
        Priorita.AZIONE_RICHIESTA
        if any(m in testo for m in MARCATORI_AZIONE)
        else Priorita.INFORMATIVA
    )

    return EsitoTriage(
        categoria=categoria, priorita=priorita, motivo=motivo, confidenza=confidenza
    )


def _prova_seam(
    mittente_nome: str, mittente_email: str, oggetto: str, corpo: str
) -> tuple[EsitoTriage, int] | None:
    """La seam LLM. None => il chiamante usa le regole."""
    risposta = client.invoca(
        "triage",
        client.MODELLO_TRIAGE,
        {
            "mittente_nome": mittente_nome,
            "mittente_email": mittente_email,
            "oggetto": oggetto,
            "corpo": corpo[:1500],
        },
    )
    if risposta is None:
        return None

    try:
        return EsitoTriage.model_validate(json.loads(risposta.contenuto)), risposta.token
    except (json.JSONDecodeError, ValueError):
        # Output non conforme allo schema: si degrada alle regole.
        return None


def fallback() -> EsitoTriage:
    return EsitoTriage(
        categoria=Categoria.SCONOSCIUTO,
        priorita=Priorita.INFORMATIVA,
        motivo="Non sono riuscito a capire di cosa si tratta.",
        confidenza=0.0,
    )
