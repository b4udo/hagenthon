"""Compositore — la risposta si sceglie, non si scrive.

Uno slot senza fatto verificato si omette: la frase si accorcia, non si
inventa. Una bozza che afferma un orario sbagliato *a nome di Maria* e' peggio
di una bozza vaga.
"""

from __future__ import annotations

import re

from app.backend import db, orchestrator
from app.backend.agents import compositore
from app.backend.contracts import Categoria, Intento

TUTTE_LE_EMAIL = ("em-01", "em-02", "em-03", "em-04", "em-05", "em-06")


def test_i_tre_intenti_sono_sempre_proposti(fatti_esempio):
    bozze, token = compositore.esegui(
        "Studio medico dott.ssa Giulia Bianchi",
        Categoria.SANITA,
        fatti_esempio,
        "Maria Rossi",
    )

    assert [b.intento for b in bozze] == [
        Intento.CONFERMA,
        Intento.CHIEDI_INFO,
        Intento.NON_POSSO,
    ]
    assert token == 0
    assert all(b.etichetta and b.testo for b in bozze)
    conferma = bozze[0]
    assert "14 ottobre 2026" in conferma.testo and "09:30" in conferma.testo
    assert len(conferma.fatti_usati) == 2


def test_senza_fatti_non_inventa_data_ne_orario():
    bozze, _ = compositore.esegui(
        "Comune di Torino - Ufficio Anagrafe",
        Categoria.ENTE_PUBBLICO,
        [],
        "Maria Rossi",
    )

    assert len(bozze) == 3
    for bozza in bozze:
        assert re.search(r"\d", bozza.testo) is None, bozza.testo
        assert bozza.fatti_usati == []


def test_nessun_invio_automatico(monkeypatch, leggi_email):
    """L'ultimo click e' sempre umano: la pipeline produce bozze, non invii."""
    invii_registrati: list[tuple] = []
    reale = db.registra_invio
    monkeypatch.setattr(
        db, "registra_invio", lambda *a, **k: invii_registrati.append(a) or reale(*a, **k)
    )

    for email_id in TUTTE_LE_EMAIL:
        orchestrator.elabora(leggi_email(email_id))

    assert invii_registrati == []
    assert db.conteggio_invii() == 0
    assert db.invii() == []
