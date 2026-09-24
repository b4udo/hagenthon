"""Normalizzazione di date, importi e orari italiani.

Perche' a mano e non con `dateparser`: quella libreria e' esattamente cio' che
un agente cerca istintivamente per le date italiane, ma introduce inferenze non
deterministiche proprio nel punto in cui FactGuard ha bisogno del contrario.
Qui il comportamento e' interamente leggibile in ~80 righe.

La normalizzazione e' cio' che rende FactGuard utilizzabile: senza, "14/10/2026"
e "14 ottobre 2026" sarebbero due fatti diversi e ogni riformulazione legittima
verrebbe rifiutata.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

MESI = {
    "gennaio": 1,
    "febbraio": 2,
    "marzo": 3,
    "aprile": 4,
    "maggio": 5,
    "giugno": 6,
    "luglio": 7,
    "agosto": 8,
    "settembre": 9,
    "ottobre": 10,
    "novembre": 11,
    "dicembre": 12,
}

_ALT_MESI = "|".join(MESI)

# 14/10/2026 · 14-10-2026 · 14.10.2026 · 14/10/26
RE_DATA_NUMERICA = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b")

# 14 ottobre 2026 · 14 ottobre
RE_DATA_TESTUALE = re.compile(
    rf"\b(\d{{1,2}})\s+({_ALT_MESI})(?:\s+(\d{{4}}))?\b", re.IGNORECASE
)

# Numero con separatore delle migliaia, oppure cifre nude.
_NUM = r"\d{1,3}(?:\.\d{3})+|\d+"

# Un importo deve portare un marcatore di valuta oppure i decimali con la
# virgola. Senza questo vincolo, un CAP ("10121") o un civico ("15")
# finirebbero fra i fatti da proteggere, e FactGuard rifiuterebbe
# semplificazioni corrette.
RE_IMPORTO = re.compile(
    rf"€\s*(?:{_NUM})(?:,\d{{1,2}})?"
    rf"|(?:{_NUM}),\d{{1,2}}\s*(?:€|euro|eur)?"
    rf"|(?:{_NUM})\s*(?:€|euro|eur)\b",
    re.IGNORECASE,
)

RE_ORARIO = re.compile(r"\b(\d{1,2})[:.](\d{2})\b")


def normalizza_data(testo: str, anno_default: int) -> str | None:
    """Restituisce AAAA-MM-GG, oppure None se non e' una data valida."""
    m = RE_DATA_NUMERICA.search(testo)
    if m:
        giorno, mese, anno = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if anno < 100:
            anno += 2000
        return _componi(giorno, mese, anno)

    m = RE_DATA_TESTUALE.search(testo)
    if m:
        giorno = int(m.group(1))
        mese = MESI[m.group(2).lower()]
        anno = int(m.group(3)) if m.group(3) else anno_default
        return _componi(giorno, mese, anno)

    return None


def _componi(giorno: int, mese: int, anno: int) -> str | None:
    if not (1 <= mese <= 12 and 1 <= giorno <= 31):
        return None
    return f"{anno:04d}-{mese:02d}-{giorno:02d}"


def normalizza_importo(testo: str) -> str | None:
    """Restituisce un decimale con il punto e due cifre: "1247.83"."""
    t = re.sub(r"(?i)\b(euro|eur)\b", "", testo)
    t = t.replace("€", "").replace(" ", "").replace(" ", "").strip()
    if not t:
        return None

    if "," in t:
        # Convenzione italiana: il punto separa le migliaia, la virgola i decimali.
        t = t.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", t):
        # 1.247 => milleduecentoquarantasette, non 1 virgola 247.
        t = t.replace(".", "")

    try:
        return f"{Decimal(t):.2f}"
    except (InvalidOperation, ValueError):
        return None


def normalizza_orario(testo: str) -> str | None:
    """Restituisce HH:MM a due cifre. "9:30", "ore 9.30" => "09:30"."""
    m = RE_ORARIO.search(testo)
    if not m:
        return None
    ora, minuti = int(m.group(1)), int(m.group(2))
    if not (0 <= ora <= 23 and 0 <= minuti <= 59):
        return None
    return f"{ora:02d}:{minuti:02d}"


MESI_PER_NUMERO = {numero: nome for nome, numero in MESI.items()}


def formatta_data_italiana(iso: str) -> str:
    """"2026-10-14" => "14 ottobre 2026". Input non valido => invariato."""
    try:
        anno, mese, giorno = (int(p) for p in iso.split("-"))
        return f"{giorno} {MESI_PER_NUMERO[mese]} {anno}"
    except (ValueError, KeyError):
        return iso


def normalizza(tipo: str, testo: str, anno_default: int) -> str | None:
    if tipo == "data":
        return normalizza_data(testo, anno_default)
    if tipo == "importo":
        return normalizza_importo(testo)
    if tipo == "orario":
        return normalizza_orario(testo)
    return None
