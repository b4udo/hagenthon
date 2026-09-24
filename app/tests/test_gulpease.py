"""Indice Gulpease — 89 + (300 * frasi - 10 * lettere) / parole."""

from __future__ import annotations

from app.backend.engines import gulpease

FRASE_BUROCRATICA = (
    "Si comunica che il certificato anagrafico richiesto risulta "
    "disponibile presso lo sportello competente."
)


def test_formula_su_una_frase_nota():
    assert gulpease.conta(FRASE_BUROCRATICA) == (13, 90, 1)
    # 89 + (300 * 1 - 10 * 90) / 13 = 42.8
    assert gulpease.gulpease(FRASE_BUROCRATICA) == 42.8
    assert gulpease.giudizio(42.8) == "difficile"


def test_testo_vuoto_vale_zero_senza_divisione_per_zero():
    assert gulpease.gulpease("") == 0.0
    assert gulpease.gulpease("   \n  ") == 0.0
