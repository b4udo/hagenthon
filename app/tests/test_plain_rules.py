"""Regressioni del semplificatore a regole.

Questi casi vengono tutti da output sbagliati **visti eseguendo la pipeline sul
corpus**, non da un'analisi a tavolino. Sono qui perche' si ripresentino come
test rossi e non come una frase storta sullo schermo durante la demo.
"""

from __future__ import annotations

from app.backend.engines import plain_rules


# ───────── cecita' alla negazione ─────────
#
# Stessa classe di errore gia' corretta in phishing_rules, dove faceva passare
# per truffa l'INPS autentico. Qui trasformava una comunicazione informativa in
# una che pretende una risposta, e lo faceva nella scheda «Cosa le chiedono»:
# la prima cosa che Maria legge.


def test_non_rispondere_non_e_una_richiesta_di_rispondere():
    testo = (
        "La presente comunicazione è generata automaticamente: "
        "si prega di non rispondere a questo indirizzo."
    )
    assert plain_rules.azione_richiesta(testo) is None


def test_rispondere_senza_negazione_resta_una_richiesta():
    testo = "La preghiamo di rispondere entro il 10 ottobre 2026."
    assert plain_rules.azione_richiesta(testo) == "Le chiedono di rispondere."


def test_la_negazione_non_zittisce_una_richiesta_vera_altrove():
    """Una richiesta vera vale anche se altrove c'e' un verbo negato.

    L'INPS dice «non rispondere» in chiusura; se dicesse anche «si presenti
    allo sportello», quella richiesta dovrebbe comunque emergere.
    """
    testo = (
        "La invitiamo a presentarsi allo sportello. "
        "Si prega di non rispondere a questo indirizzo."
    )
    assert plain_rules.azione_richiesta(testo) == "Le chiedono di presentarsi di persona."


# ───────── locuzioni intere invece di singole parole ─────────


def test_cedolino_pensione_non_raddoppia_la_parola_pensione():
    """«cedolino pensione» → «foglio della pensione», non «... pensione pensione».

    Il nome del servizio INPS e' «Cedolino pensione»: sostituendo il solo
    «cedolino» resta un «pensione» orfano attaccato in coda.
    """
    reso = plain_rules.semplifica_testo(
        "Accedendo al servizio «Cedolino pensione» del portale istituzionale."
    )
    assert "pensione pensione" not in reso.lower()
    assert "foglio della pensione" in reso.lower()


def test_cedolino_da_solo_resta_tradotto():
    reso = plain_rules.semplifica_testo("È disponibile il cedolino di ottobre.")
    assert "foglio della pensione" in reso.lower()
