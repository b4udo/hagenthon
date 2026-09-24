"""Lettura delle fixture della seam LLM.

Le fixture sono output di esempio **scritti durante lo sviluppo**, conformi agli
schema in agents/runtime/contracts/. Non sono registrazioni di chiamate API:
questo progetto non ha mai usato una chiave, e nel repository non ce n'e' una.

Il file contiene solo `model`, `content` e `usage`. Nessun header, nessun campo
di autenticazione: non c'e' nulla da cui una credenziale possa trapelare.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# app/backend/llm/fixtures.py -> parents[2] == app/
RADICE_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "llm"


def chiave(modello: str, nome_prompt: str, input_reso: str) -> str:
    """sha256 di (modello + prompt + input), tronco a 16 caratteri.

    La stessa funzione produce il nome del file quando la fixture viene scritta
    e quando viene letta: e' l'unico punto in cui i due lati devono accordarsi.
    """
    grezzo = f"{modello}\x00{nome_prompt}\x00{input_reso}".encode("utf-8")
    return hashlib.sha256(grezzo).hexdigest()[:16]


def leggi(chiave_fixture: str) -> dict | None:
    """La fixture, oppure None se non esiste.

    None non e' un errore: il chiamante degrada alle regole. In demo questo
    significa che una fixture dimenticata non fa cadere nulla, ma lascia una
    traccia rumorosa nel log.
    """
    percorso = RADICE_FIXTURE / f"{chiave_fixture}.json"
    if not percorso.exists():
        logger.warning(
            "FIXTURE MANCANTE %s — la seam LLM degrada alle regole deterministiche.",
            percorso.name,
        )
        return None

    try:
        dati = json.loads(percorso.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as errore:
        logger.warning("FIXTURE ILLEGGIBILE %s: %s", percorso.name, errore)
        return None

    if "content" not in dati:
        logger.warning("FIXTURE MALFORMATA %s: manca 'content'.", percorso.name)
        return None

    return dati


def token_di(dati: dict) -> int:
    uso = dati.get("usage") or {}
    return int(uso.get("input_tokens", 0)) + int(uso.get("output_tokens", 0))
