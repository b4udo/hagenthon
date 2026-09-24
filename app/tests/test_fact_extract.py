"""Estrazione fatti — scope rigido.

Il falso positivo piu' probabile e' il civico o il CAP letti come importo: da
li' arriva un rifiuto ingiustificato di FactGuard, cioe' il fallback brutto
davanti alla giuria. E' testato esplicitamente.
"""

from __future__ import annotations

from app.backend.engines import fact_extract


def test_ancoraggio_a_parola_chiave(anno):
    testo = (
        "L'appuntamento è fissato per il 14 ottobre 2026 alle ore 9:30. "
        "L'importo da pagare è di € 1.247,83."
    )
    fatti = fact_extract.estrai_fatti(testo, anno)
    per_tipo = {f.tipo.value: f.valore_normalizzato for f in fatti}

    assert per_tipo == {"data": "2026-10-14", "orario": "09:30", "importo": "1247.83"}
    assert all(f.ancora for f in fatti)

    # Senza parola chiave nei 40 caratteri precedenti si scarta. Lo span resta
    # comunque prenotato, cosi' "14.10" non viene riletto come orario.
    senza_ancora = "Riferimento pratica numero 14.10.2026 assegnato all'ufficio."
    assert fact_extract.estrai_fatti(senza_ancora, anno) == []


def test_il_civico_non_e_un_importo(anno):
    # "pagare" e' un'ancora da importo ed e' vicinissima: deve bastare la
    # forma del numero a escluderlo.
    testo = "Le chiediamo di pagare presso la sede di Via Roma 15."
    assert fact_extract.estrai_fatti(testo, anno) == []


def test_il_cap_non_e_un_importo(anno):
    testo = "Deve versare presso lo sportello di Torino, 10121 Torino."
    assert fact_extract.estrai_fatti(testo, anno) == []


def test_la_data_di_una_citazione_normativa_non_e_un_fatto(anno):
    # Proteggerla costringerebbe il semplificatore a conservare il
    # riferimento di legge, cioe' esattamente cio' che deve eliminare.
    testo = (
        "Ai sensi degli artt. 33 e 40 del D.P.R. 28 dicembre 2000, n. 445, "
        "il certificato è disponibile."
    )
    fatti = fact_extract.estrai_fatti(testo, anno)
    assert all(f.valore_normalizzato != "2000-12-28" for f in fatti)


def test_testo_senza_fatti_da_lista_vuota(anno):
    testo = "Buongiorno signora, le scrivo solo per salutarla. A presto!"
    assert fact_extract.estrai_fatti(testo, anno) == []


def test_lo_stesso_valore_in_due_formati_viene_deduplicato(anno):
    testo = (
        "L'appuntamento del 14/10/2026 è confermato. "
        "La data del 14 ottobre 2026 resta valida."
    )
    date = [f for f in fact_extract.estrai_fatti(testo, anno) if f.tipo.value == "data"]
    assert len(date) == 1
    assert date[0].valore_normalizzato == "2026-10-14"
