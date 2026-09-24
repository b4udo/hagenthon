"""Cattura le schermate del prodotto con Playwright.

Servono a due cose: le immagini del deck e le **schermate di riserva** da
mostrare se durante la demo qualcosa non parte. Sono generate dal prodotto
vero, non disegnate: se l'interfaccia cambia, basta rilanciare.

    python scripts/cattura_schermate.py

Sta fuori da `app/` di proposito. `app/tests/test_llm_modes.py` verifica che
nessun sorgente sotto `app/` importi una libreria di rete, e Playwright lo e':
metterlo li' farebbe fallire la garanzia "zero rete" che il progetto dichiara.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

RADICE = Path(__file__).resolve().parents[1]
USCITA = RADICE / "presentation" / "img"
VIEWPORT = {"width": 820, "height": 1180}


def porta_libera() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def avvia_server(porta: int) -> subprocess.Popen:
    processo = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.backend.main:app",
         "--port", str(porta), "--log-level", "error"],
        cwd=RADICE,
        env={**os.environ, "PYTHONPATH": str(RADICE)},
    )
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{porta}/api/salute", timeout=1)
            return processo
        except (urllib.error.URLError, OSError):
            time.sleep(0.25)
    processo.terminate()
    raise SystemExit("il server non si e' avviato")


def cattura() -> None:
    USCITA.mkdir(parents=True, exist_ok=True)
    porta = porta_libera()
    server = avvia_server(porta)
    base = f"http://127.0.0.1:{porta}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            pagina = browser.new_context(
                viewport=VIEWPORT, device_scale_factor=2
            ).new_page()

            pagina.goto(base)
            pagina.wait_for_selector(".voce")
            pagina.wait_for_function(
                "document.querySelectorAll('.pallino-attesa').length === 0",
                timeout=20000,
            )
            salva(pagina, "01-casella.png")

            # Lettura semplificata + riassunto
            pagina.locator(".voce", has_text="Bianchi").first.click()
            pagina.wait_for_selector("#scheda-riassunto")
            salva(pagina, "02-lettura-semplificata.png")

            # Risposta guidata, con la bozza aperta
            pagina.locator(".intento", has_text="Confermo che vengo").click()
            pagina.wait_for_selector("#testo-bozza")
            pagina.locator("#scheda-risposta").scroll_into_view_if_needed()
            salva(pagina, "03-risposta-guidata.png")
            # Ritaglio stretto: la schermata intera, dentro una slide, diventa
            # una striscia illeggibile. Per il deck serve il solo riquadro.
            ritaglia(pagina, "#scheda-risposta", "07-risposta-dettaglio.png")
            ritaglia(pagina, "#scheda-riassunto", "08-riassunto-dettaglio.png")

            # Semaforo rosso con il numero ufficiale
            pagina.goto(base)
            pagina.wait_for_selector(".voce")
            pagina.locator(".voce", has_text="Poste").first.click()
            pagina.wait_for_selector("#semaforo")
            salva(pagina, "04-truffa-semaforo-rosso.png")

            # FactGuard che rifiuta, dal vivo.
            # ?tecnico=1 e' obbligatorio: il pulsante «E se l'AI sbaglia?» e'
            # uno strumento da presentatore e sta dietro il modo tecnico, dove
            # Maria non lo trova. Senza il parametro resta nascosto e il click
            # va in timeout.
            pagina.goto(f"{base}/?tecnico=1")
            pagina.wait_for_selector(".voce")
            pagina.locator(".voce", has_text="INPS").first.click()
            pagina.wait_for_selector("#semaforo")
            pagina.locator("#btn-avvelena").click()
            pagina.wait_for_selector("#scheda-verifica:not([hidden])")
            pagina.locator("#scheda-verifica").scroll_into_view_if_needed()
            salva(pagina, "05-factguard-rifiuto.png")
            ritaglia(pagina, "#scheda-verifica", "06-factguard-dettaglio.png")

            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)

    print(f"\nschermate in {USCITA}")


def salva(pagina, nome: str) -> None:
    pagina.screenshot(path=USCITA / nome, full_page=True)
    print("catturata", nome)


def ritaglia(pagina, selettore: str, nome: str) -> None:
    pagina.locator(selettore).screenshot(path=USCITA / nome)
    print("catturata", nome, f"(solo {selettore})")


if __name__ == "__main__":
    cattura()
