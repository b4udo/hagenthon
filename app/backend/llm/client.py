"""La seam LLM — due modalita', zero codice di rete.

    off     (default)  la seam non viene attraversata: valgono le regole
    replay             la seam viene attraversata per intero, e la risposta
                       arriva dalle fixture in app/fixtures/llm/

Non esiste una terza modalita'. In questo file non c'e' `import anthropic`, non
c'e' un client HTTP, non c'e' una lettura di ANTHROPIC_API_KEY. Non sono
disattivati: non esistono. `app/tests/test_llm_modes.py` lo verifica leggendo
staticamente i sorgenti, cosi' la garanzia e' eseguibile invece che dichiarata.

Cosa resta vero in `replay`: il prompt viene caricato da agents/runtime/prompts/,
le variabili sostituite, l'input reso in forma canonica, la chiave calcolata,
il JSON interpretato e validato con Pydantic dal chiamante, i token contati dal
campo `usage`. Solo il trasporto e' assente. Aggiungerlo domani non cambierebbe
nient'altro.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import fixtures

# Model tiering — dichiarato in agents/runtime/routing.md.
# Haiku dove basta classificare, Sonnet solo sul linguaggio.
MODELLO_TRIAGE = "claude-haiku-4-5-20251001"
MODELLO_LINGUA = "claude-sonnet-5"

# posta-chiara/app/backend/llm/client.py -> parents[3] == radice del repo
RADICE_PROMPT = Path(__file__).resolve().parents[3] / "agents" / "runtime" / "prompts"

MODALITA_VALIDE = ("off", "replay")


@dataclass(frozen=True)
class RispostaLLM:
    contenuto: str
    token: int
    modello: str


def modalita() -> str:
    valore = os.environ.get("LLM_MODE", "off").strip().lower()
    return valore if valore in MODALITA_VALIDE else "off"


def seam_attiva() -> bool:
    return modalita() == "replay"


def carica_prompt(nome: str) -> str:
    """Il prompt, letto da agents/runtime/prompts/<nome>.md.

    I prompt non sono duplicati in Python: sono *quel* file. E' il motivo per
    cui la documentazione della pipeline non puo' divergere dal suo
    comportamento — sono lo stesso artefatto.
    """
    percorso = RADICE_PROMPT / f"{nome}.md"
    return percorso.read_text(encoding="utf-8")


def rendi(modello_testo: str, variabili: dict[str, str]) -> str:
    reso = modello_testo
    for nome, valore in variabili.items():
        reso = reso.replace("{{" + nome + "}}", str(valore))
    return reso


def invoca(
    nome_prompt: str,
    modello: str,
    variabili: dict[str, str],
) -> RispostaLLM | None:
    """Attraversa la seam. None significa «usa le regole».

    None arriva in tre casi, tutti legittimi e tutti con lo stesso esito:
    modalita' `off`, fixture mancante, fixture malformata.
    """
    if not seam_attiva():
        return None

    try:
        testo_prompt = carica_prompt(nome_prompt)
    except OSError:
        return None

    reso = rendi(testo_prompt, variabili)
    dati = fixtures.leggi(fixtures.chiave(modello, nome_prompt, reso))
    if dati is None:
        return None

    return RispostaLLM(
        contenuto=dati["content"],
        token=fixtures.token_di(dati),
        modello=dati.get("model", modello),
    )
