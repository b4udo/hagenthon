"""Indice Gulpease — leggibilita' per l'italiano.

    Gulpease = 89 + (300 * frasi - 10 * lettere) / parole

Scala 0-100. Sopra 80 il testo e' leggibile con la licenza elementare, sopra 60
con la licenza media. E' la metrica che rende misurabile il "prima / dopo" della
semplificazione invece di lasciarlo all'impressione.
"""

from __future__ import annotations

import re

_RE_PAROLE = re.compile(r"[a-zA-ZàèéìòùÀÈÉÌÒÙ0-9']+")
_RE_FRASI = re.compile(r"[.!?;]+")


def conta(testo: str) -> tuple[int, int, int]:
    parole = _RE_PAROLE.findall(testo)
    n_parole = len(parole)
    n_lettere = sum(len(p) for p in parole)
    n_frasi = len([f for f in _RE_FRASI.split(testo) if f.strip()])
    return n_parole, n_lettere, n_frasi


def gulpease(testo: str) -> float:
    """L'indice, arrotondato a una cifra. Testo vuoto => 0.0, non un errore."""
    n_parole, n_lettere, n_frasi = conta(testo)
    if n_parole == 0:
        return 0.0
    indice = 89 + (300 * n_frasi - 10 * n_lettere) / n_parole
    return round(max(0.0, min(100.0, indice)), 1)


def giudizio(indice: float) -> str:
    if indice >= 80:
        return "molto facile"
    if indice >= 60:
        return "facile"
    if indice >= 40:
        return "difficile"
    return "molto difficile"
