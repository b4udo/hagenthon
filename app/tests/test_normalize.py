"""Normalizzazione — la base su cui poggia FactGuard.

Se "14/10/2026" e "14 ottobre 2026" non producessero lo stesso valore, il
verificatore rifiuterebbe ogni riformulazione legittima.
"""

from __future__ import annotations

from app.backend.engines import normalize


def test_la_stessa_data_in_tre_formati_ha_lo_stesso_valore(anno):
    atteso = "2026-10-14"
    assert normalize.normalizza_data("14/10/2026", anno) == atteso
    assert normalize.normalizza_data("14 ottobre 2026", anno) == atteso
    assert normalize.normalizza_data("14-10-2026", anno) == atteso


def test_la_data_senza_anno_usa_l_anno_dell_orologio(anno):
    # Mai date.today(): il corpus scadrebbe da solo.
    assert normalize.normalizza_data("14 ottobre", anno) == "2026-10-14"


def test_lo_stesso_importo_con_simbolo_o_con_la_parola_euro(anno):
    assert normalize.normalizza_importo("€ 1.234,50") == "1234.50"
    assert normalize.normalizza_importo("1.234,50 euro") == "1234.50"


def test_il_punto_delle_migliaia_non_e_una_virgola_decimale():
    # "1.247" vale milleduecentoquarantasette, non 1 virgola 247.
    assert normalize.normalizza_importo("1.247") == "1247.00"
    assert normalize.normalizza_importo("1.247,83") == "1247.83"


def test_l_orario_a_una_cifra_diventa_a_due_cifre():
    assert normalize.normalizza_orario("ore 9:30") == "09:30"
    assert normalize.normalizza_orario("09:30") == "09:30"
    assert normalize.normalizza_orario("ore 9.30") == "09:30"


def test_una_data_impossibile_non_e_una_data(anno):
    assert normalize.normalizza_data("32/13/2026", anno) is None
    assert normalize.normalizza_data("nessuna data qui", anno) is None


def test_formatta_data_italiana_e_l_inverso_leggibile():
    assert normalize.formatta_data_italiana("2026-10-14") == "14 ottobre 2026"
    # Input non valido: si restituisce invariato invece di sollevare.
    assert normalize.formatta_data_italiana("non-una-data") == "non-una-data"
