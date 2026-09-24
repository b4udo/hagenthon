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


# ───────────────────── chiedere aiuto a una persona ─────────────────────


def test_si_puo_chiedere_aiuto_su_qualunque_email(cliente: TestClient):
    """La via d'uscita umana non dipende dal verdetto del semaforo.

    Il momento in cui una persona si sente in difficoltà non coincide con il
    momento in cui il sistema ha dei dubbi: legare l'aiuto al giallo vuol dire
    offrirlo solo quando lo decidiamo noi.
    """
    for email_id in ("em-01", "em-03", "em-04", "em-05", "em-06"):
        risposta = cliente.post(f"/api/email/{email_id}/aiuto")
        assert risposta.status_code == 200, email_id
        corpo = risposta.json()
        assert corpo["inoltrata"] is True
        assert corpo["a_chi"] == "Guada"


def test_la_richiesta_di_aiuto_viene_registrata(cliente: TestClient):
    assert db.conteggio_aiuti() == 0
    cliente.post("/api/email/em-03/aiuto")
    assert db.conteggio_aiuti() == 1
    assert db.id_con_aiuto() == {"em-03"}


def test_chiedere_aiuto_su_una_email_inesistente_da_404(cliente: TestClient):
    assert cliente.post("/api/email/em-999/aiuto").status_code == 404


def test_chiedere_aiuto_non_conta_come_risposta_inviata(cliente: TestClient):
    """Sono due esiti diversi: «ho risposto da sola» e «ho chiesto aiuto».

    Contarli insieme gonfierebbe il contatore di autonomia con l'esatto
    contrario dell'autonomia.
    """
    cliente.post("/api/email/em-03/aiuto")
    assert cliente.get("/api/autonomia").json()["completate_da_sola"] == 0
    dati = cliente.get("/api/mailbox").json()
    assert all(e["gia_risposto"] is False for e in dati["email"])


# ───────────────────── allegati alla risposta ─────────────────────


def test_si_puo_allegare_un_documento_alla_risposta(cliente: TestClient):
    cliente.post("/api/email/em-02/elabora")
    risposta = cliente.post(
        "/api/email/em-02/invia",
        json={
            "intento": "conferma",
            "testo": "Ecco il documento richiesto.",
            "allegato": {
                "nome": "carta_identita.jpg",
                "tipo": "image/jpeg",
                "dimensione": 218_000,
            },
        },
    )
    assert risposta.status_code == 200
    assert risposta.json()["allegato"] == "carta_identita.jpg"

    inviata = cliente.get("/api/mailbox?cartella=inviata").json()["email"][0]
    assert inviata["allegato"]["nome"] == "carta_identita.jpg"
    assert inviata["allegato"]["tipo"] == "image/jpeg"
    assert inviata["allegato"]["dimensione"] == 218_000


def test_l_allegato_e_facoltativo(cliente: TestClient):
    cliente.post("/api/email/em-01/elabora")
    risposta = cliente.post(
        "/api/email/em-01/invia", json={"intento": "conferma", "testo": "Confermo."}
    )
    assert risposta.status_code == 200
    assert risposta.json()["allegato"] is None
    assert cliente.get("/api/mailbox?cartella=inviata").json()["email"][0]["allegato"] is None


def test_del_file_si_conservano_solo_i_metadati(cliente: TestClient):
    """I byte non arrivano mai al server, e il contratto non li prevede.

    È posta sanitaria e previdenziale: un documento d'identità finito su un
    disco perché «serviva per la demo» è esattamente ciò che non deve
    succedere.
    """
    cliente.post("/api/email/em-02/elabora")
    cliente.post(
        "/api/email/em-02/invia",
        json={
            "intento": "conferma",
            "testo": "Allegato.",
            "allegato": {"nome": "foto.jpg", "tipo": "image/jpeg", "dimensione": 900},
            "contenuto": "QUESTI-BYTE-NON-DEVONO-ENTRARE",
        },
    )
    salvato = cliente.get("/api/mailbox?cartella=inviata").json()["email"][0]["allegato"]
    assert set(salvato) == {"nome", "tipo", "dimensione"}


# ───────────────────── «Guada sta verificando» ─────────────────────


def test_una_email_inoltrata_risulta_in_verifica(cliente: TestClient):
    dati = cliente.get("/api/mailbox").json()
    assert all(e["inoltrata"] is False for e in dati["email"])

    cliente.post("/api/email/em-03/aiuto")

    per_id = {e["id"]: e for e in cliente.get("/api/mailbox").json()["email"]}
    assert per_id["em-03"]["inoltrata"] is True
    assert per_id["em-01"]["inoltrata"] is False

    # Serve anche alla vista di lettura, che non passa dall'elenco.
    assert cliente.post("/api/email/em-03/elabora").json()["inoltrata"] is True


def test_inoltrata_e_gia_risposto_sono_stati_indipendenti(cliente: TestClient):
    cliente.post("/api/email/em-01/elabora")
    cliente.post("/api/email/em-01/aiuto")
    per_id = {e["id"]: e for e in cliente.get("/api/mailbox").json()["email"]}
    assert per_id["em-01"]["inoltrata"] is True
    assert per_id["em-01"]["gia_risposto"] is False
