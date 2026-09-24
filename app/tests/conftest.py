"""Fixture condivise della suite.

Due sorgenti di non determinismo vanno neutralizzate prima di ogni test:
l'orologio (il corpus contiene scadenze del 2026) e il database in memoria,
che e' un singleton di modulo e quindi sopravvivrebbe da un test all'altro.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.backend import clock, db
from app.backend.contracts import Email, Fatto, TipoFatto
from app.backend.main import app

OGGI_DI_PROVA = "2026-10-06"


@pytest.fixture(autouse=True)
def ambiente_deterministico(monkeypatch):
    """Orologio fermo, seam LLM spenta, database ricreato da zero.

    E' autouse perche' nessun test deve dipendere dall'ambiente della macchina
    ne' dall'ordine di esecuzione.
    """
    monkeypatch.setenv("POSTA_CHIARA_OGGI", OGGI_DI_PROVA)
    monkeypatch.delenv("LLM_MODE", raising=False)
    db.reimposta()
    yield
    db.reimposta()


@pytest.fixture
def anno() -> int:
    return clock.anno_corrente()


@pytest.fixture
def email_minima() -> Email:
    return Email(
        id="em-prova",
        mittente_nome="Ufficio Esempio",
        mittente_email="ufficio@esempio.it",
        oggetto="Comunicazione di prova",
        corpo="Buongiorno, le scriviamo per una comunicazione di prova.",
        data_ricezione="2026-10-05",
    )


@pytest.fixture
def leggi_email():
    """Un'email del corpus, gia' validata contro il contratto."""

    def _leggi(email_id: str) -> Email:
        grezza = db.leggi_email(email_id)
        assert grezza is not None, f"email {email_id} assente dal corpus"
        return Email.model_validate(grezza)

    return _leggi


@pytest.fixture
def fatti_esempio() -> list[Fatto]:
    return [
        Fatto(
            tipo=TipoFatto.DATA,
            testo_originale="14/10/2026",
            valore_normalizzato="2026-10-14",
            ancora="appuntamento",
            posizione=10,
        ),
        Fatto(
            tipo=TipoFatto.ORARIO,
            testo_originale="ore 9:30",
            valore_normalizzato="09:30",
            ancora="ore",
            posizione=40,
        ),
    ]


@pytest.fixture
def client_api():
    with TestClient(app) as client:
        yield client
