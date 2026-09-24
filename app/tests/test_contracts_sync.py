"""Gli JSON Schema pubblicati devono corrispondere ai modelli Pydantic.

`agents/runtime/contracts/` e' un deliverable: e' cio' che un giurato legge per
capire i confini fra gli agenti. Se i modelli cambiano e gli schema no, la
cartella agents/ inizia a raccontare un sistema che non esiste piu'.

Questo test rende impossibile quella deriva, invece di raccomandare di evitarla.
"""

from __future__ import annotations

from app.backend.tools import genera_schemi


def test_ogni_contratto_ha_il_suo_schema():
    for nome in genera_schemi.MODELLI:
        percorso = genera_schemi.RADICE / f"{nome}.schema.json"
        assert percorso.exists(), (
            f"manca {percorso.name}. Rigenera con: "
            f"python -m app.backend.tools.genera_schemi"
        )


def test_gli_schema_sono_allineati_ai_modelli():
    disallineati = genera_schemi.verifica()
    assert not disallineati, (
        "schema non allineati ai modelli Pydantic: "
        + "; ".join(disallineati)
        + ". Rigenera con: python -m app.backend.tools.genera_schemi"
    )
