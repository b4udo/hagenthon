"""Cartelle della posta e stato «gia' risposto».

Due regole che il resto del sistema da' per scontate:

  - `gia_risposto` e' **derivato** dalla tabella `invio`, non memorizzato.
    Cosi' non puo' andare fuori sincrono con la verita'.
  - eliminare **sposta**, non cancella. Con un tremore alla mano una
    cancellazione irreversibile toglie autonomia invece di darla.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.backend import db
from app.backend.main import app


@pytest.fixture(autouse=True)
def database_pulito():
    db.reimposta()
    yield
    db.reimposta()


@pytest.fixture
def cliente():
    return TestClient(app)


def _rispondi(cliente: TestClient, email_id: str) -> None:
    cliente.post(f"/api/email/{email_id}/elabora")
    risposta = cliente.post(
        f"/api/email/{email_id}/invia",
        json={"intento": "conferma", "testo": "Confermo, grazie."},
    )
    assert risposta.status_code == 200


# ───────────────────────── già risposto ─────────────────────────


def test_una_email_senza_risposta_non_e_segnata(cliente: TestClient):
    dati = cliente.get("/api/mailbox").json()
    assert all(e["gia_risposto"] is False for e in dati["email"])


def test_dopo_l_invio_l_email_risulta_gia_risposta(cliente: TestClient):
    _rispondi(cliente, "em-01")

    dati = cliente.get("/api/mailbox").json()
    per_id = {e["id"]: e for e in dati["email"]}
    assert per_id["em-01"]["gia_risposto"] is True
    # Solo quella: rispondere a una non segna le altre.
    assert per_id["em-02"]["gia_risposto"] is False


def test_lo_stato_gia_risposto_arriva_anche_dalla_pipeline(cliente: TestClient):
    """Serve alla vista di lettura, che non passa dall'elenco."""
    prima = cliente.post("/api/email/em-01/elabora").json()
    assert prima["gia_risposto"] is False

    _rispondi(cliente, "em-01")

    dopo = cliente.post("/api/email/em-01/elabora").json()
    assert dopo["gia_risposto"] is True


def test_gia_risposto_e_derivato_non_memorizzato():
    """Togliendo l'invio, lo stato sparisce da solo: nessuna colonna da allineare."""
    db.connessione()
    assert db.id_con_risposta() == set()

    db.registra_invio("em-01", "conferma", "Confermo.", "2026-10-06T10:00:00+00:00")
    assert db.id_con_risposta() == {"em-01"}


# ───────────────────────── le tre cartelle ─────────────────────────


def test_la_posta_in_arrivo_e_la_cartella_predefinita(cliente: TestClient):
    dati = cliente.get("/api/mailbox").json()
    assert dati["cartella"] == "in_arrivo"
    assert dati["tipo"] == "ricevuta"
    assert len(dati["email"]) == 6


def test_i_conteggi_delle_tre_cartelle(cliente: TestClient):
    dati = cliente.get("/api/mailbox").json()
    assert dati["conteggi"] == {"in_arrivo": 6, "inviata": 0, "eliminata": 0}

    _rispondi(cliente, "em-01")
    cliente.post("/api/email/em-06/elimina")

    dati = cliente.get("/api/mailbox").json()
    assert dati["conteggi"] == {"in_arrivo": 5, "inviata": 1, "eliminata": 1}


def test_eliminare_sposta_e_si_puo_tornare_indietro(cliente: TestClient):
    assert cliente.post("/api/email/em-06/elimina").status_code == 200

    in_arrivo = cliente.get("/api/mailbox").json()
    assert "em-06" not in [e["id"] for e in in_arrivo["email"]]

    cestino = cliente.get("/api/mailbox?cartella=eliminata").json()
    assert [e["id"] for e in cestino["email"]] == ["em-06"]

    # L'email esiste ancora: e' stata spostata, non cancellata.
    assert cliente.get("/api/email/em-06").status_code == 200

    assert cliente.post("/api/email/em-06/ripristina").status_code == 200
    di_nuovo = cliente.get("/api/mailbox").json()
    assert "em-06" in [e["id"] for e in di_nuovo["email"]]


def test_la_posta_inviata_mostra_le_risposte_con_destinatario_e_oggetto(cliente: TestClient):
    _rispondi(cliente, "em-01")

    inviata = cliente.get("/api/mailbox?cartella=inviata").json()
    assert inviata["tipo"] == "inviata"
    assert len(inviata["email"]) == 1

    voce = inviata["email"][0]
    # Destinatario e oggetto sono ereditati dall'email a cui si risponde.
    assert "Bianchi" in voce["destinatario_nome"]
    assert voce["oggetto"].startswith("Re: ")
    assert voce["testo"] == "Confermo, grazie."


def test_l_oggetto_di_risposta_non_accumula_re(cliente: TestClient):
    """Rispondere a «Re: qualcosa» non produce «Re: Re: qualcosa»."""
    assert db._oggetto_di_risposta("Re: Conferma") == "Re: Conferma"
    assert db._oggetto_di_risposta("Conferma") == "Re: Conferma"
    assert db._oggetto_di_risposta(None) == "Risposta"


def test_una_cartella_sconosciuta_e_un_errore_esplicito(cliente: TestClient):
    assert cliente.get("/api/mailbox?cartella=archivio").status_code == 400


def test_eliminare_una_email_inesistente_da_404(cliente: TestClient):
    assert cliente.post("/api/email/em-999/elimina").status_code == 404


def test_non_si_puo_spostare_in_una_cartella_inventata():
    db.connessione()
    with pytest.raises(ValueError):
        db.sposta("em-01", "archivio")
