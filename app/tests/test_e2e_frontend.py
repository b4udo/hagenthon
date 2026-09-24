"""Test end-to-end dell'interfaccia, con Playwright.

Verifica il percorso di Maria in un browser vero, perche' e' l'unico modo di
sapere se il prodotto funziona: la suite di unita' dimostra che la pipeline
calcola le cose giuste, non che una persona riesca a usarle.

Nessuna rete esterna: il server e' avviato qui, su 127.0.0.1, e il browser
parla solo con lui.

    python -m pytest app/tests/test_e2e_frontend.py -q

Se Playwright o il browser non sono installati, i test si saltano invece di
fallire: la suite principale non deve dipendere da una dipendenza opzionale.
"""

from __future__ import annotations

import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright non installato")

from playwright.sync_api import Page, expect, sync_playwright  # noqa: E402

RADICE = Path(__file__).resolve().parents[2]
TARGET_MINIMO_PX = 44  # il vincolo che viene dal tremore alla mano


def _porta_libera() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server() -> str:
    porta = _porta_libera()
    processo = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.backend.main:app",
         "--port", str(porta), "--log-level", "error"],
        cwd=RADICE,
        env={**__import__("os").environ, "PYTHONPATH": str(RADICE)},
    )
    base = f"http://127.0.0.1:{porta}"

    for _ in range(60):
        try:
            urllib.request.urlopen(f"{base}/api/salute", timeout=1)
            break
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.25)
    else:
        processo.terminate()
        pytest.fail("il server non si e' avviato")

    yield base

    processo.terminate()
    processo.wait(timeout=10)


@pytest.fixture(scope="module")
def browser():
    try:
        with sync_playwright() as p:
            try:
                b = p.chromium.launch()
            except Exception as errore:  # browser non scaricato
                pytest.skip(f"Chromium non disponibile: {errore}")
            yield b
            b.close()
    except Exception as errore:
        pytest.skip(f"Playwright non utilizzabile: {errore}")


@pytest.fixture
def page(browser, server) -> Page:
    contesto = browser.new_context(viewport={"width": 820, "height": 1180})
    pagina = contesto.new_page()
    pagina.goto(server)
    yield pagina
    contesto.close()


# ───────────────────────────── elenco ─────────────────────────────


def test_la_casella_mostra_le_sei_email(page: Page):
    page.wait_for_selector(".voce")
    assert page.locator(".voce").count() == 6


def test_ogni_email_riceve_un_semaforo(page: Page):
    page.wait_for_selector(".voce")
    # I verdetti arrivano dalla pipeline, uno per email, in modo asincrono.
    page.wait_for_function(
        "document.querySelectorAll('.pallino-attesa').length === 0", timeout=15000
    )
    assert page.locator(".pallino-verde, .pallino-giallo, .pallino-rosso").count() == 6


# ────────────────────── il percorso di Maria ──────────────────────


def test_percorso_completo_dal_medico_alla_risposta_inviata(page: Page):
    page.wait_for_selector(".voce")
    page.locator(".voce", has_text="Bianchi").first.click()

    # Il riassunto sostituisce il burocratese.
    expect(page.locator("#scheda-riassunto")).to_be_visible()
    expect(page.locator("#chi-scrive")).not_to_be_empty()
    expect(page.locator("#entro-quando")).not_to_be_empty()

    # Il riquadro bianco vuoto e' sostituito da tre scelte.
    intenti = page.locator(".intento")
    expect(intenti).to_have_count(3)

    page.locator(".intento", has_text="Confermo che vengo").click()

    bozza = page.locator("#testo-bozza")
    expect(bozza).to_be_visible()
    testo = bozza.input_value()
    assert "14 ottobre 2026" in testo, testo
    assert "09:30" in testo, testo

    page.locator("#btn-invia").click()
    expect(page.locator("#conferma-invio")).to_be_visible()
    expect(page.locator("#contatore-autonomia")).to_have_text("1")


def test_nessun_invio_senza_un_click_della_persona(page: Page):
    """Aprire e scegliere un intento non invia nulla."""
    page.wait_for_selector(".voce")
    # Il contatore non riparte da zero: il database in memoria vive quanto il
    # server, condiviso da tutti i test del modulo. Conta la differenza.
    prima = page.locator("#contatore-autonomia").inner_text()

    page.locator(".voce", has_text="Bianchi").first.click()
    page.locator(".intento").first.click()

    expect(page.locator("#conferma-invio")).to_be_hidden()
    assert page.locator("#contatore-autonomia").inner_text() == prima


# ───────────────────────── sicurezza ─────────────────────────


def test_la_truffa_e_rossa_e_non_propone_di_rispondere(page: Page):
    page.wait_for_selector(".voce")
    page.locator(".voce", has_text="Poste").first.click()

    expect(page.locator("#semaforo")).to_have_class(re.compile(r"semaforo-rosso"))
    expect(page.locator("#semaforo-messaggio")).to_contain_text("Non risponda")
    # Su un'email di phishing non si compone alcuna bozza.
    expect(page.locator("#scheda-risposta")).to_be_hidden()
    # Il verdetto porta comunque un'azione: il numero ufficiale.
    expect(page.locator("#btn-azione")).to_be_visible()
    expect(page.locator("#btn-azione")).to_contain_text("803 160")


def test_il_nipote_in_rubrica_e_verde(page: Page):
    page.wait_for_selector(".voce")
    page.locator(".voce", has_text="Luca").first.click()
    expect(page.locator("#semaforo")).to_have_class(re.compile(r"semaforo-verde"))


# ───────────────────────── FactGuard dal vivo ─────────────────────────


def test_email_avvelenata_il_rifiuto_compare_a_schermo(page: Page):
    page.wait_for_selector(".voce")
    page.locator(".voce", has_text="INPS").first.click()

    expect(page.locator("#scheda-verifica")).to_be_hidden()

    page.locator("#btn-avvelena").click()

    avviso = page.locator("#scheda-verifica")
    expect(avviso).to_be_visible()
    expect(avviso).to_contain_text("1.247,83")
    expect(avviso).to_contain_text("1.247")
    # Rifiutata la semplificazione, si torna all'originale.
    expect(page.locator("#scheda-riassunto")).to_be_hidden()


# ───────────────────────── accessibilita' ─────────────────────────


def test_la_pagina_dichiara_la_lingua_italiana(page: Page):
    assert page.get_attribute("html", "lang") == "it"


def test_i_bersagli_sono_abbastanza_grandi_per_una_mano_che_trema(page: Page):
    page.wait_for_selector(".voce")
    # Non la prima della lista: e' l'email di phishing, che di proposito non
    # propone bozze di risposta. Serve una schermata con tutti i controlli.
    page.locator(".voce", has_text="Bianchi").first.click()
    page.wait_for_selector(".intento")

    piccoli = []
    for i in range(page.locator("button:visible").count()):
        b = page.locator("button:visible").nth(i)
        riquadro = b.bounding_box()
        if riquadro and riquadro["height"] < TARGET_MINIMO_PX:
            piccoli.append((b.inner_text()[:30], round(riquadro["height"])))
    assert not piccoli, f"bersagli sotto {TARGET_MINIMO_PX}px: {piccoli}"


def test_il_testo_base_non_scende_sotto_i_venti_pixel(page: Page):
    dimensione = page.evaluate(
        "parseFloat(getComputedStyle(document.documentElement).fontSize)"
    )
    assert dimensione >= 20, f"base {dimensione}px, la cataratta iniziale chiede 20"


def test_si_naviga_e_si_apre_una_email_con_la_sola_tastiera(page: Page):
    page.wait_for_selector(".voce")
    # Si tabula finche' il fuoco non e' su una voce dell'elenco, poi Invio.
    for _ in range(12):
        page.keyboard.press("Tab")
        if page.evaluate("document.activeElement.classList.contains('voce')"):
            break
    else:
        pytest.fail("nessuna voce raggiungibile da tastiera")

    page.keyboard.press("Enter")
    expect(page.locator("#vista-lettura")).to_be_visible()


def test_il_fuoco_si_sposta_sulla_vista_di_lettura(page: Page):
    """Chi usa la tastiera non deve restare indietro quando cambia schermata."""
    page.wait_for_selector(".voce")
    page.locator(".voce").first.click()
    expect(page.locator("#btn-indietro")).to_be_focused()


def test_i_cambi_di_stato_passano_da_una_regione_aria_live(page: Page):
    page.wait_for_selector(".voce")
    page.locator(".voce").first.click()
    assert page.get_attribute("#semaforo", "aria-live") == "polite"
    assert page.get_attribute("#autonomia", "aria-live") == "polite"
