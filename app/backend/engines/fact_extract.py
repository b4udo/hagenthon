"""Estrazione dei fatti da proteggere: date, importi, orari.

Lo scope e' volutamente stretto. Ogni tipo in piu' aumenta i falsi positivi, e
un rifiuto ingiustificato di FactGuard distrugge la fiducia nel verificatore
molto piu' di quanto un fatto non protetto la costruisca.

Due meccanismi tengono basso il rumore:

1. **Ancoraggio a parola chiave.** Un candidato conta come fatto solo se nei 40
   caratteri precedenti compare un'ancora ("entro", "importo", "ore", ...).
2. **Span gia' occupati.** Le date si estraggono per prime e prenotano la loro
   porzione di testo, cosi' "14.10.2026" non viene poi riletto come l'orario
   14:10 e "Via Roma 15" non diventa nulla del tutto.
"""

from __future__ import annotations

import re

from ..contracts import Fatto, TipoFatto
from . import normalize

FINESTRA_ANCORA = 40

ANCORE: dict[str, tuple[str, ...]] = {
    "data": (
        "entro",
        "scadenza",
        "scade",
        "appuntamento",
        "visita",
        "giorno",
        "data",
        "il",
        "del",
        "dal",
        "previsto",
        "fissata",
        "fissato",
    ),
    "importo": (
        "importo",
        "euro",
        "€",
        "totale",
        "pagare",
        "versare",
        "versato",
        "pensione",
        "netto",
        "lordo",
        "rata",
        "somma",
    ),
    "orario": ("ore", "alle", "orario", "ora"),
}

REGEX: dict[str, tuple[re.Pattern[str], ...]] = {
    "data": (normalize.RE_DATA_NUMERICA, normalize.RE_DATA_TESTUALE),
    "importo": (normalize.RE_IMPORTO,),
    "orario": (normalize.RE_ORARIO,),
}

# L'ordine conta: le date prenotano il loro span prima che orari e importi
# guardino il testo.
ORDINE = ("data", "importo", "orario")


def _ha_ancora(testo: str, inizio: int, tipo: str) -> str:
    finestra = testo[max(0, inizio - FINESTRA_ANCORA) : inizio].lower()
    for ancora in ANCORE[tipo]:
        if ancora == "€":
            if "€" in finestra:
                return ancora
        elif re.search(rf"\b{re.escape(ancora)}\b", finestra):
            return ancora
    return ""


def _si_sovrappone(inizio: int, fine: int, occupati: list[tuple[int, int]]) -> bool:
    return any(inizio < f and i < fine for i, f in occupati)


def estrai_fatti(testo: str, anno_default: int) -> list[Fatto]:
    """I fatti ancorati, deduplicati per (tipo, valore normalizzato)."""
    fatti: list[Fatto] = []
    occupati: list[tuple[int, int]] = []
    visti: set[tuple[str, str]] = set()

    for tipo in ORDINE:
        for pattern in REGEX[tipo]:
            for m in pattern.finditer(testo):
                if _si_sovrappone(m.start(), m.end(), occupati):
                    continue

                ancora = _ha_ancora(testo, m.start(), tipo)
                grezzo = m.group(0).strip()
                valore = normalize.normalizza(tipo, grezzo, anno_default)

                if valore is None:
                    continue

                # Lo span si prenota anche senza ancora: un numero che *somiglia*
                # a una data non deve poi essere riletto come orario.
                occupati.append((m.start(), m.end()))

                if not ancora:
                    continue
                if (tipo, valore) in visti:
                    continue

                visti.add((tipo, valore))
                fatti.append(
                    Fatto(
                        tipo=TipoFatto(tipo),
                        testo_originale=grezzo,
                        valore_normalizzato=valore,
                        ancora=ancora,
                        posizione=m.start(),
                    )
                )

    fatti.sort(key=lambda f: f.posizione)
    return fatti


def estrai_valori_grezzi(testo: str, anno_default: int) -> dict[str, list[tuple[str, str]]]:
    """Tutti i valori presenti nel testo, **senza** richiedere un'ancora.

    Serve a FactGuard per sapere cosa contiene davvero la versione semplificata:
    li' il semplificatore puo' aver riformulato la frase e fatto sparire
    l'ancora, ma il fatto deve esserci lo stesso.
    """
    risultato: dict[str, list[tuple[str, str]]] = {t: [] for t in ORDINE}
    occupati: list[tuple[int, int]] = []

    for tipo in ORDINE:
        for pattern in REGEX[tipo]:
            for m in pattern.finditer(testo):
                if _si_sovrappone(m.start(), m.end(), occupati):
                    continue
                grezzo = m.group(0).strip()
                valore = normalize.normalizza(tipo, grezzo, anno_default)
                if valore is None:
                    continue
                occupati.append((m.start(), m.end()))
                risultato[tipo].append((grezzo, valore))

    return risultato
