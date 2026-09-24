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
    """Il browser dei test.

    Normalmente invisibile, perche' cosi' la suite gira ovunque e anche in CI.
    Per **guardare** i test mentre lavorano — utile in demo, e per capire un
    fallimento molto piu' in fretta che leggendo un traceback:

        $env:PLAYWRIGHT_VISIBILE = "1"        # PowerShell
        python -m pytest app/tests/test_e2e_frontend.py -q

    `PLAYWRIGHT_LENTEZZA` (millisecondi per azione) rallenta il browser quanto
    basta a seguirlo con l'occhio: 400 e' una buona velocita' da proiettore.
    """
    import os as _os

    visibile = _os.environ.get("PLAYWRIGHT_VISIBILE", "").strip() in ("1", "true", "si")
    lentezza = float(_os.environ.get("PLAYWRIGHT_LENTEZZA", "0") or 0)

    try:
        with sync_playwright() as p:
            try:
                b = p.chromium.launch(headless=not visibile, slow_mo=lentezza)
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


def test_email_avvelenata_il_rifiuto_compare_a_schermo(browser, server):
    """Il pulsante che avvelena e' uno strumento da presentatore.

    Vive dietro `?tecnico=1` insieme al resto della strumentazione: Maria non
    deve trovarsi in pagina un pulsante che rompe apposta la sua posta.
    """
    contesto = browser.new_context(viewport={"width": 820, "height": 1180})
    pagina = contesto.new_page()
    pagina.goto(f"{server}/?tecnico=1")
    pagina.wait_for_selector(".voce")
    pagina.locator(".voce", has_text="INPS").first.click()

    expect(pagina.locator("#scheda-verifica")).to_be_hidden()

    pagina.locator("#btn-avvelena").click()

    avviso = pagina.locator("#scheda-verifica")
    expect(avviso).to_be_visible()
    expect(avviso).to_contain_text("1.247,83")
    expect(avviso).to_contain_text("1.247")
    # Rifiutata la semplificazione, si torna all'originale.
    expect(pagina.locator("#scheda-riassunto")).to_be_hidden()
    contesto.close()


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


# ─────────────────── la voce, e cosa Maria non deve vedere ───────────────────


def test_maria_non_vede_i_pannelli_tecnici(page: Page):
    """Il bando boccia gli strumenti «pensati per sviluppatori».

    Una tabella di agenti, millisecondi e token addosso a chi apre la posta e'
    esattamente quell'errore. Restano nel prodotto, dietro ?tecnico=1.
    """
    page.wait_for_selector(".voce")
    page.locator(".voce", has_text="Bianchi").first.click()
    expect(page.locator("#scheda-riassunto")).to_be_visible()

    expect(page.locator(".scheda-ragionamento")).to_be_hidden()
    expect(page.locator(".scheda-demo")).to_be_hidden()
    expect(page.locator(".pie-tecnico")).to_be_hidden()


def test_con_tecnico_1_la_giuria_vede_la_pipeline(browser, server):
    contesto = browser.new_context(viewport={"width": 820, "height": 1180})
    pagina = contesto.new_page()
    pagina.goto(f"{server}/?tecnico=1")
    pagina.wait_for_selector(".voce")
    pagina.locator(".voce", has_text="Bianchi").first.click()

    expect(pagina.locator(".scheda-ragionamento")).to_be_visible()
    expect(pagina.locator(".scheda-demo")).to_be_visible()
    assert pagina.locator("#corpo-tracce tr").count() >= 5
    contesto.close()


def test_i_comandi_della_voce_sono_presenti_e_abbastanza_grandi(page: Page):
    """Maria usa i vocali di WhatsApp: ascoltare e dettare non sono un extra."""
    page.wait_for_selector(".voce")
    page.locator(".voce", has_text="Bianchi").first.click()
    page.locator(".intento", has_text="Confermo che vengo").click()
    expect(page.locator("#testo-bozza")).to_be_visible()

    for selettore in ["#btn-ascolta-riassunto", "#btn-ascolta-messaggio",
                      "#btn-ascolta-bozza", "#btn-detta"]:
        elemento = page.locator(selettore)
        expect(elemento).to_be_visible()
        riquadro = elemento.bounding_box()
        assert riquadro["height"] >= TARGET_MINIMO_PX, f"{selettore}: {riquadro}"


def test_la_barra_di_arresto_appare_solo_mentre_legge(page: Page):
    """Regressione: `display: flex` in una classe batte l'attributo `hidden`.

    La barra era rimasta incollata in fondo allo schermo dal primo caricamento.
    """
    page.wait_for_selector(".voce")
    page.locator(".voce", has_text="Bianchi").first.click()
    expect(page.locator("#scheda-riassunto")).to_be_visible()
    expect(page.locator("#barra-voce")).to_be_hidden()


def test_ascolta_il_riassunto_passa_alla_sintesi_il_testo_giusto(page: Page):
    """Il testo letto e' quello della scheda, con le sigle rese pronunciabili."""
    page.wait_for_selector(".voce")
    page.locator(".voce", has_text="Bianchi").first.click()
    expect(page.locator("#scheda-riassunto")).to_be_visible()

    # Si intercetta speechSynthesis.speak: in un browser senza voci installate
    # non si sente nulla, ma quello che il codice *chiede* di leggere si vede.
    page.evaluate("""() => {
        window.__letto = [];
        const vero = window.speechSynthesis.speak.bind(window.speechSynthesis);
        window.speechSynthesis.speak = (u) => { window.__letto.push(u.text); vero(u); };
    }""")
    page.locator("#btn-ascolta-riassunto").click()
    page.wait_for_function("window.__letto && window.__letto.length > 0", timeout=5000)

    letto = page.evaluate("window.__letto")[0]
    assert "Chi le scrive" in letto
    assert "Cosa le chiedono" in letto
    # Le sigle lette lettera per lettera suonerebbero come parole senza senso.
    assert "dottoressa" in letto, letto


def test_la_dettatura_avvisa_prima_che_la_voce_esca_dal_dispositivo(page: Page):
    """L'unica funzione che manda qualcosa fuori deve dirlo *prima*, non dopo."""
    page.wait_for_selector(".voce")
    page.locator(".voce", has_text="Bianchi").first.click()
    page.locator(".intento", has_text="Confermo che vengo").click()

    page.locator("#btn-detta").click()
    avviso = page.locator(".voce-avviso")
    expect(avviso).to_be_visible()
    assert "esce da questo dispositivo" in avviso.inner_text()

    # Si deve poter rifiutare, e rifiutare non deve accendere il microfono.
    page.locator("[data-no]").click()
    expect(avviso).to_have_count(0)


def test_la_dettatura_non_sostituisce_la_bozza_verificata(page: Page):
    """La voce aggiunge in coda: i fatti verificati non si perdono parlando."""
    page.wait_for_selector(".voce")
    page.locator(".voce", has_text="Bianchi").first.click()
    page.locator(".intento", has_text="Confermo che vengo").click()

    prima = page.locator("#testo-bozza").input_value()
    assert "14 ottobre 2026" in prima

    # Si simula il risultato della dettatura come lo produce voce.js: il testo
    # detto si aggiunge in coda, non sostituisce la bozza gia' verificata.
    # String.fromCharCode(10) e non la sequenza di escape: Python la
    # interpreterebbe prima del browser, spezzando la stringa JavaScript.
    page.evaluate(
        "() => {"
        "  const area = document.getElementById('testo-bozza');"
        "  const inizio = area.value.length;"
        "  area.value = area.value.slice(0, inizio) + String.fromCharCode(10)"
        "             + 'Grazie mille.';"
        "}"
    )
    dopo = page.locator("#testo-bozza").input_value()
    assert "14 ottobre 2026" in dopo, dopo
    assert "Grazie mille." in dopo, dopo


# ─────────────────── cartelle e stato «già risposto» ───────────────────


def test_le_tre_cartelle_sono_sempre_visibili(page: Page):
    """Mai dentro un menu: chi non ha mai usato le cartelle non va a cercarle."""
    page.wait_for_selector(".cartella")
    etichette = [c.inner_text().split("\n")[0] for c in page.locator(".cartella").all()]
    assert etichette == ["Posta in arrivo", "Posta inviata", "Posta eliminata"]

    # La cartella corrente e' marcata semanticamente, non col solo colore.
    corrente = page.locator('.cartella[aria-current="page"]')
    expect(corrente).to_have_count(1)
    assert corrente.inner_text().startswith("Posta in arrivo")


def test_dopo_l_invio_l_email_e_marcata_gia_risposto(page: Page):
    """Usa l'INPS, non il medico.

    Il server di questo modulo e' condiviso da tutti i test del file e il
    database non si azzera fra l'uno e l'altro: `em-01` viene gia' risposta
    altrove, quindi l'asserzione «prima non e' marcata» dipenderebbe
    dall'ordine di esecuzione. `em-04` non la risponde nessun altro test.
    """
    page.wait_for_selector(".voce")
    page.locator(".voce", has_text="INPS").first.click()

    # Prima di rispondere non c'e' nessuna marcatura.
    expect(page.locator("#stato-risposta")).to_be_hidden()

    page.locator(".intento").first.click()
    page.locator("#btn-invia").click()
    expect(page.locator("#conferma-invio")).to_be_visible()
    expect(page.locator("#stato-risposta")).to_be_visible()

    # E la marcatura sopravvive al ritorno nell'elenco.
    page.locator("#btn-indietro").click()
    page.wait_for_selector(".voce:has([data-risposto])")
    riga = page.locator('.voce:has-text("INPS")').first
    expect(riga.locator("[data-risposto]")).to_be_visible()
    expect(riga.locator("[data-risposto]")).to_contain_text("Già risposto")
    # Anche per chi non vede i colori: lo stato sta nel nome accessibile.
    assert "Già risposto" in riga.get_attribute("aria-label")


def test_la_posta_inviata_elenca_le_risposte(page: Page):
    # Il server di questo modulo e' condiviso da tutti i test del file, quindi
    # gli invii si accumulano: si misura la differenza, non il totale.
    page.locator(".cartella", has_text="Posta inviata").click()
    page.wait_for_selector(".voce-inviata, .vuota")
    prima = page.locator(".voce-inviata").count()

    page.locator(".cartella", has_text="Posta in arrivo").click()
    page.wait_for_selector(".voce")
    page.locator(".voce", has_text="Bianchi").first.click()
    page.locator(".intento", has_text="Confermo che vengo").click()
    page.locator("#btn-invia").click()
    expect(page.locator("#conferma-invio")).to_be_visible()

    page.locator("#btn-indietro").click()
    page.locator(".cartella", has_text="Posta inviata").click()

    expect(page.locator("#titolo-elenco")).to_have_text("Posta inviata")
    inviata = page.locator(".voce-inviata")
    expect(inviata).to_have_count(prima + 1)
    # La piu' recente sta in cima, ed e' quella appena mandata al medico.
    expect(inviata.first).to_contain_text("Bianchi")
    expect(inviata.first).to_contain_text("Re:")


def test_eliminare_sposta_nel_cestino_e_si_torna_indietro(page: Page):
    page.wait_for_selector(".voce")
    quante = page.locator(".voce").count()

    page.locator(".voce", has_text="Spesa Conveniente").first.click()
    page.locator("#btn-elimina").click()

    page.wait_for_selector(".voce")
    assert page.locator(".voce").count() == quante - 1

    page.locator(".cartella", has_text="Posta eliminata").click()
    expect(page.locator(".voce")).to_have_count(1)

    # Nel cestino si ripristina, non si elimina di nuovo.
    page.locator(".voce").first.click()
    expect(page.locator("#btn-elimina")).to_be_hidden()
    expect(page.locator("#btn-ripristina")).to_be_visible()

    page.locator("#btn-ripristina").click()
    page.locator(".cartella", has_text="Posta in arrivo").click()
    page.wait_for_selector(".voce")
    assert page.locator(".voce").count() == quante


def test_una_cartella_vuota_lo_dice_a_parole(page: Page):
    page.wait_for_selector(".cartella")
    page.locator(".cartella", has_text="Posta eliminata").click()
    vuota = page.locator(".vuota")
    expect(vuota).to_be_visible()
    expect(vuota).to_contain_text("Non ha eliminato nessun messaggio")


def test_il_pulsante_di_aiuto_e_presente_su_ogni_email(page: Page):
    """Su verde, giallo e rosso: la via d'uscita umana è sempre lì."""
    for mittente in ("Bianchi", "Poste", "Spesa Conveniente"):
        page.goto(page.url.split("#")[0])
        page.wait_for_selector(".voce")
        page.locator(".voce", has_text=mittente).first.click()
        page.wait_for_selector("#semaforo")

        aiuto = page.locator("#btn-aiuto")
        expect(aiuto).to_be_visible()
        riquadro = aiuto.bounding_box()
        assert riquadro["height"] >= TARGET_MINIMO_PX, f"{mittente}: {riquadro}"


def test_chiedere_aiuto_conferma_a_schermo(page: Page):
    page.wait_for_selector(".voce")
    page.locator(".voce", has_text="Poste").first.click()
    page.wait_for_selector("#btn-aiuto")

    expect(page.locator("#conferma-aiuto")).to_be_hidden()
    page.locator("#btn-aiuto").click()

    conferma = page.locator("#conferma-aiuto")
    expect(conferma).to_be_visible()
    expect(conferma).to_contain_text("Luca")

    # Aprendo un'altra email la conferma non resta appiccicata.
    page.locator("#btn-indietro").click()
    page.wait_for_selector(".voce")
    page.locator(".voce", has_text="INPS").first.click()
    expect(page.locator("#conferma-aiuto")).to_be_hidden()


def test_una_email_gia_risposta_non_mostra_anche_il_semaforo(page: Page):
    """«Può rispondere» e «Già risposto» insieme si contraddicono a colpo d'occhio."""
    page.wait_for_selector(".voce")
    page.locator(".voce", has_text="Bianchi").first.click()
    page.locator(".intento", has_text="Confermo che vengo").click()
    page.locator("#btn-invia").click()
    expect(page.locator("#conferma-invio")).to_be_visible()

    page.locator("#btn-indietro").click()
    # Si attende il ridisegno *con* il badge, non una lista qualsiasi.
    page.wait_for_selector(".voce:has([data-risposto])")

    riga = page.locator('.voce:has-text("Bianchi")').first
    expect(riga.locator("[data-risposto]")).to_have_count(1)
    expect(riga.locator("[data-pallino]")).to_have_count(0)

    # Su un'email non ancora risposta il semaforo resta al suo posto.
    # «Spesa Conveniente» e' pubblicita': il compositore non le genera bozze,
    # quindi nessun test puo' averla risposta e il controllo non dipende
    # dall'ordine di esecuzione.
    altra = page.locator('.voce:has-text("Spesa Conveniente")').first
    expect(altra.locator("[data-pallino]")).to_have_count(1)
    expect(altra.locator("[data-risposto]")).to_have_count(0)
