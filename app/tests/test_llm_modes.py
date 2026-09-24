"""Le due modalita' della seam, e la garanzia «zero rete» resa eseguibile.

Il primo test non assume che il progetto non tocchi la rete: lo dimostra,
leggendo staticamente ogni sorgente di app/.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.backend import orchestrator
from app.backend.llm import client

RADICE_APP = Path(__file__).resolve().parents[1]

# I moduli che introdurrebbero un trasporto di rete. Non sono disattivati nel
# progetto: non esistono, e questo test e' cio' che lo tiene vero.
MODULI_VIETATI = ("anthropic", "requests", "urllib.request", "http.client", "httpx")
RADICI_DI_RETE = ("httpx", "requests", "urllib", "socket", "anthropic")


def _sorgenti_di_app() -> list[Path]:
    return [
        p
        for p in RADICE_APP.rglob("*.py")
        if "tests" not in p.relative_to(RADICE_APP).parts
    ]


def _moduli_importati(albero: ast.AST) -> set[str]:
    nomi: set[str] = set()
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.Import):
            nomi.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            base = nodo.module or ""
            if base:
                nomi.add(base)
                nomi.update(f"{base}.{alias.name}" for alias in nodo.names)
    return nomi


def _chiamate_di_rete(albero: ast.AST) -> set[str]:
    trovate: set[str] = set()
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute):
            oggetto = nodo.func.value
            if isinstance(oggetto, ast.Name) and oggetto.id in RADICI_DI_RETE:
                trovate.add(f"{oggetto.id}.{nodo.func.attr}")
    return trovate


def test_nessun_sorgente_di_app_puo_toccare_la_rete():
    sorgenti = _sorgenti_di_app()
    assert len(sorgenti) >= 10, "la scansione non ha trovato i sorgenti di app/"

    colpevoli: list[str] = []
    for percorso in sorgenti:
        albero = ast.parse(percorso.read_text(encoding="utf-8"), filename=str(percorso))

        for modulo in _moduli_importati(albero):
            if any(
                modulo == vietato or modulo.startswith(vietato + ".")
                for vietato in MODULI_VIETATI
            ):
                colpevoli.append(f"{percorso.name}: import {modulo}")

        for chiamata in _chiamate_di_rete(albero):
            colpevoli.append(f"{percorso.name}: chiamata {chiamata}")

    assert colpevoli == [], f"codice di rete in app/: {colpevoli}"


def test_modalita_off_non_attraversa_la_seam(monkeypatch, leggi_email):
    monkeypatch.setenv("LLM_MODE", "off")

    assert client.modalita() == "off"
    assert client.seam_attiva() is False
    assert client.invoca("triage", client.MODELLO_TRIAGE, {"oggetto": "x"}) is None

    risultato = orchestrator.elabora(leggi_email("em-01"))
    assert risultato.token_usati == 0


def test_replay_con_fixture_mancante_degrada_alle_regole(monkeypatch, leggi_email):
    monkeypatch.setenv("LLM_MODE", "replay")
    assert client.seam_attiva() is True

    # Variabili assurde: nessuna fixture scritta a mano puo' avere questa chiave.
    risposta = client.invoca(
        "semplificatore",
        client.MODELLO_LINGUA,
        {"corpo": "chiave-inesistente-" + "x" * 64},
    )
    assert risposta is None

    # La pipeline non si ferma mai per una fixture che manca.
    risultato = orchestrator.elabora(leggi_email("em-02"))
    assert risultato.tracce
    assert risultato.sicurezza is not None


def test_il_prompt_viene_letto_da_agents_runtime_prompts():
    assert client.RADICE_PROMPT.parts[-3:] == ("agents", "runtime", "prompts")

    if not client.RADICE_PROMPT.is_dir():
        pytest.skip("agents/runtime/prompts/ non esiste ancora")

    nomi = sorted(p.stem for p in client.RADICE_PROMPT.glob("*.md"))
    if not nomi:
        pytest.skip("nessun prompt scritto")

    testo = client.carica_prompt(nomi[0])
    assert testo.strip()
