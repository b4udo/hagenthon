"""Sicurezza — regole spiegabili, e un'azione per ogni verdetto.

Il costo di un falso verde (Maria si fida di una truffa) non e' paragonabile a
quello di un falso giallo (Maria chiede al nipote). Le soglie qui sotto sono
prudenziali per costruzione.
"""

from __future__ import annotations

from app.backend.agents import sicurezza
from app.backend.contracts import Semaforo, TipoAzione
from app.backend.engines import phishing_rules

# Le due frasi dell'email INPS autentica che facevano scattare il falso
# positivo: nominare una credenziale non e' chiederla.
CORPO_INPS_AUTENTICO = (
    "Il documento è consultabile accedendo al servizio «Cedolino pensione» del "
    "portale istituzionale, previa autenticazione con le credenziali digitali "
    "personali.\n"
    "Si rammenta che l'Istituto non richiede mai, tramite posta elettronica, la "
    "comunicazione di credenziali di accesso, codici dispositivi o coordinate "
    "bancarie."
)


def test_dominio_che_imita_un_ente_e_rosso():
    semaforo, segnali, ente = phishing_rules.valuta(
        "Poste Italiane - Servizio Sicurezza Clienti",
        "no-reply@poste-sicurezza-clienti.info",
        "Avviso importante",
        "Gentile cliente, la informiamo di un accesso anomalo al suo conto.",
        in_rubrica=False,
    )

    assert semaforo == "rosso"
    assert ente is not None and ente["nome"] == "Poste Italiane"
    assert any("indirizzo non e' quello ufficiale" in s for s in segnali)


def test_link_mascherato_e_rosso():
    corpo = (
        "Per la verifica clicchi qui:\n"
        '<a href="https://sicurezza-clienti.example/verifica">'
        "https://www.poste.it/verifica</a>\nGrazie."
    )
    semaforo, segnali, _ = phishing_rules.valuta(
        "Servizio Clienti",
        "assistenza@verifica-conto.example",
        "Verifica del profilo",
        corpo,
        in_rubrica=False,
    )

    assert semaforo == "rosso"
    assert any("collegamento" in s for s in segnali)


def test_email_che_dichiara_di_non_chiedere_credenziali_non_e_segnalata():
    # Regressione: questa e' la comunicazione autentica dell'INPS.
    semaforo, segnali, _ = phishing_rules.valuta(
        "INPS - Istituto Nazionale Previdenza Sociale",
        "comunicazioni@inps.it",
        "Cedolino della pensione - mensilità di ottobre 2026",
        CORPO_INPS_AUTENTICO,
        in_rubrica=False,
    )

    assert semaforo == "verde"
    assert not any("dati riservati" in s for s in segnali)


def test_richiesta_esplicita_di_credenziali_e_rossa():
    corpo = (
        "Per completare la procedura le verranno richiesti: nome utente, "
        "password, codice PosteID e il numero della carta."
    )
    semaforo, segnali, _ = phishing_rules.valuta(
        "Servizio Clienti",
        "assistenza@verifica-conto.example",
        "Completi la verifica",
        corpo,
        in_rubrica=False,
    )

    assert semaforo == "rosso"
    assert any("dati riservati" in s for s in segnali)


def test_mittente_in_rubrica_e_verde():
    semaforo, _, _ = phishing_rules.valuta(
        "Luca Rossi",
        "luca.rossi92@gmail.com",
        "Ciao nonna, domenica vengo a pranzo!",
        "Ciao nonna, come stai? Domenica vengo a pranzo da te.",
        in_rubrica=True,
    )
    assert semaforo == "verde"


def test_sconosciuto_innocuo_e_giallo_mai_verde():
    semaforo, segnali, _ = phishing_rules.valuta(
        "Associazione Amici del Parco",
        "info@amicidelparco.example",
        "Festa di quartiere",
        "Buongiorno, la invitiamo alla festa di quartiere di sabato pomeriggio.",
        in_rubrica=False,
    )

    assert semaforo == "giallo"
    assert any("Non conosco questo mittente" in s for s in segnali)


def test_il_numero_suggerito_viene_dalla_tabella_statica():
    # Su una mail di phishing il numero nel corpo e' quello del truffatore.
    esito = sicurezza.esegui(
        "Poste Italiane - Sicurezza",
        "no-reply@poste-verifica.example",
        "Conto bloccato",
        "La invitiamo a chiamare subito il numero 06 999 888 777 per assistenza.",
        in_rubrica=False,
    )

    assert esito.semaforo is Semaforo.ROSSO
    assert esito.azione.tipo is TipoAzione.TELEFONO
    assert esito.azione.valore == phishing_rules.RECAPITI_UFFICIALI["poste italiane"]["telefono"]
    assert "999" not in (esito.azione.valore or "")
