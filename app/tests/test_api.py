"""L'API vista dal frontend. Nessuna chiamata esce dal processo."""

from __future__ import annotations


def test_salute_dichiara_che_non_serve_una_chiave_api(client_api):
    risposta = client_api.get("/api/salute")

    assert risposta.status_code == 200
    corpo = risposta.json()
    assert corpo["chiave_api_richiesta"] is False
    assert corpo["llm_mode"] == "off"
    assert corpo["oggi"] == "2026-10-06"


def test_la_mailbox_contiene_sei_email(client_api):
    corpo = client_api.get("/api/mailbox").json()

    assert len(corpo["email"]) == 6
    assert corpo["proprietario"]["nome"] == "Maria Rossi"
    assert corpo["inviate"] == 0


def test_elabora_restituisce_le_tracce(client_api):
    risposta = client_api.post("/api/email/em-01/elabora")

    assert risposta.status_code == 200
    corpo = risposta.json()
    assert corpo["email_id"] == "em-01"
    assert corpo["tracce"]
    assert corpo["leggibilita"]["prima"] > 0


def test_email_inesistente_da_404(client_api):
    assert client_api.post("/api/email/em-99/elabora").status_code == 404


def test_l_invio_incrementa_il_contatore_di_autonomia(client_api):
    assert client_api.get("/api/autonomia").json()["completate_da_sola"] == 0

    risposta = client_api.post(
        "/api/email/em-01/invia",
        json={"intento": "conferma", "testo": "Confermo la presenza. Maria Rossi"},
    )

    assert risposta.status_code == 200
    assert risposta.json() == {"inviata": True, "completate_da_sola": 1}
    assert client_api.get("/api/autonomia").json()["completate_da_sola"] == 1
