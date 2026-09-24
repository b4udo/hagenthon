"""FactGuard — il pezzo tecnico centrale del prodotto.

Le righe della tabella «confronto normalizzato» di
agents/runtime/05-verificatore.md sono altrettanti test: il confronto avviene
sui valori normalizzati, mai sulle stringhe grezze.
"""

from __future__ import annotations

from app.backend.agents import verificatore
from app.backend.contracts import Fatto, TipoFatto, TipoProblema


def _fatto(tipo: str, originale: str, valore: str, ancora: str = "") -> Fatto:
    return Fatto(
        tipo=TipoFatto(tipo),
        testo_originale=originale,
        valore_normalizzato=valore,
        ancora=ancora,
    )


DATA_14 = _fatto("data", "14/10/2026", "2026-10-14", "appuntamento")
DATA_10 = _fatto("data", "10 ottobre 2026", "2026-10-10", "entro")
IMPORTO = _fatto("importo", "€ 1.247,83", "1247.83", "importo")
ORARIO = _fatto("orario", "ore 9:30", "09:30", "ore")


def test_fatto_preservato_passa(anno):
    esito = verificatore.verifica(
        [IMPORTO, ORARIO],
        "Deve incassare 1.247,83 euro. L'orario è alle 09:30.",
        anno,
    )
    assert esito.passa is True
    assert esito.problemi == []


def test_stessa_data_in_formato_diverso_passa(anno):
    # La riga che prova che la normalizzazione serve: il semplificatore esiste
    # proprio per riformattare.
    esito = verificatore.verifica(
        [DATA_14], "L'appuntamento è il 14 ottobre 2026.", anno
    )
    assert esito.passa is True


def test_importo_alterato_viene_rifiutato(anno):
    esito = verificatore.verifica([IMPORTO], "Deve pagare € 1.247 in banca.", anno)

    assert esito.passa is False
    assert [p.tipo for p in esito.problemi] == [TipoProblema.ALTERATO]
    problema = esito.problemi[0]
    assert problema.fatto is not None
    assert problema.fatto.valore_normalizzato == "1247.83"
    assert "1.247" in (problema.trovato or "")


def test_orario_alterato_viene_rifiutato(anno):
    esito = verificatore.verifica([ORARIO], "L'appuntamento è alle ore 9:00.", anno)

    assert esito.passa is False
    assert [p.tipo for p in esito.problemi] == [TipoProblema.ALTERATO]


def test_data_sparita_e_segnalata_come_mancante(anno):
    esito = verificatore.verifica(
        [DATA_14], "Le chiedono di confermare la sua presenza.", anno
    )

    assert esito.passa is False
    assert [p.tipo for p in esito.problemi] == [TipoProblema.MANCANTE]
    assert esito.problemi[0].trovato is None


def test_fatto_sparito_e_mancante_non_alterato(anno):
    # Con due date nell'originale e una sola nel semplificato, la seconda e'
    # *mancante*: la prima non puo' spiegarne l'alterazione.
    esito = verificatore.verifica(
        [DATA_14, DATA_10], "L'appuntamento resta il 14 ottobre 2026.", anno
    )

    assert esito.passa is False
    assert [p.tipo for p in esito.problemi] == [TipoProblema.MANCANTE]
    assert esito.problemi[0].fatto is not None
    assert esito.problemi[0].fatto.valore_normalizzato == "2026-10-10"


def test_importo_inventato_viene_segnalato(anno):
    esito = verificatore.verifica(
        [DATA_14],
        "L'appuntamento è il 14 ottobre 2026. Deve pagare anche € 50 di mora.",
        anno,
    )

    assert esito.passa is False
    assert [p.tipo for p in esito.problemi] == [TipoProblema.INVENTATO]
    assert esito.problemi[0].fatto is None
    assert "50" in (esito.problemi[0].trovato or "")


def test_senza_fatti_la_verifica_passa(anno):
    # Zero fatti e' un esito legittimo: non c'era nulla da tradire.
    esito = verificatore.verifica([], "Un testo semplice, senza dati da proteggere.", anno)
    assert esito.passa is True
    assert esito.problemi == []


def test_feedback_per_retry_solo_quando_fallisce(anno):
    passato = verificatore.verifica([DATA_14], "Ci vediamo il 14 ottobre 2026.", anno)
    fallito = verificatore.verifica([DATA_14], "Ci vediamo presto.", anno)

    assert passato.feedback_per_retry is None
    assert fallito.feedback_per_retry
    # E' rivolto al semplificatore: deve nominare il fatto da ripristinare.
    assert "14/10/2026" in fallito.feedback_per_retry


def test_avvelena_corrompe_davvero_l_importo(anno):
    originale = "L'importo netto in pagamento è pari a € 1.247,83."
    avvelenato = verificatore.avvelena(originale)

    assert "1.247,83" not in avvelenato
    assert "€ 1.247" in avvelenato
    assert verificatore.verifica([IMPORTO], avvelenato, anno).passa is False
