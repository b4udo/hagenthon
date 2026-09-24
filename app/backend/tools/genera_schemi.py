"""Genera gli JSON Schema in agents/runtime/contracts/ dai modelli Pydantic.

Gli schema non si scrivono a mano. Scritti a mano diventerebbero una seconda
fonte di verita' destinata a divergere dai modelli al primo refactoring, ed e'
esattamente la sovrapposizione che il progetto dichiara di non avere.

    python -m app.backend.tools.genera_schemi           # scrive
    python -m app.backend.tools.genera_schemi --verifica # solo controllo

`app/tests/test_contracts_sync.py` esegue la variante --verifica: se un
modello cambia e lo schema no, la suite diventa rossa.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .. import contracts

RADICE = Path(__file__).resolve().parents[3] / "agents" / "runtime" / "contracts"

MODELLI = {
    "email": contracts.Email,
    "esito-triage": contracts.EsitoTriage,
    "esito-sicurezza": contracts.EsitoSicurezza,
    "esito-estrazione": contracts.EsitoEstrazione,
    "esito-semplificazione": contracts.EsitoSemplificazione,
    "esito-verifica": contracts.EsitoVerifica,
    "bozza-risposta": contracts.BozzaRisposta,
    "traccia-agente": contracts.TracciaAgente,
    "risultato-pipeline": contracts.RisultatoPipeline,
}


def schema_di(modello) -> str:
    return json.dumps(modello.model_json_schema(), indent=2, ensure_ascii=False) + "\n"


def genera() -> list[Path]:
    RADICE.mkdir(parents=True, exist_ok=True)
    scritti = []
    for nome, modello in MODELLI.items():
        percorso = RADICE / f"{nome}.schema.json"
        percorso.write_text(schema_di(modello), encoding="utf-8")
        scritti.append(percorso)
    return scritti


def verifica() -> list[str]:
    """I nomi degli schema disallineati rispetto ai modelli."""
    disallineati = []
    for nome, modello in MODELLI.items():
        percorso = RADICE / f"{nome}.schema.json"
        if not percorso.exists():
            disallineati.append(f"{nome}: schema mancante")
        elif percorso.read_text(encoding="utf-8") != schema_di(modello):
            disallineati.append(f"{nome}: schema diverso dal modello Pydantic")
    return disallineati


if __name__ == "__main__":
    if "--verifica" in sys.argv:
        problemi = verifica()
        for p in problemi:
            print("DISALLINEATO:", p)
        print("tutti gli schema sono allineati" if not problemi else f"{len(problemi)} disallineati")
        sys.exit(1 if problemi else 0)

    for percorso in genera():
        print("scritto", percorso.name)
