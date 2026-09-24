"""Percorre il cammino di Maria in una finestra vera, lentamente.

Serve a **guardare** il prodotto mentre lavora: in demo, e come rete di
sicurezza se il portatile della presentazione fa i capricci. Ogni passo e'
annunciato sul terminale, cosi' si sa sempre cosa si sta vedendo.

    python scripts/demo_guidata.py            # ritmo normale
    python scripts/demo_guidata.py 1.8        # piu' lento, da proiettore

Sta fuori da `app/` come cattura_schermate.py: Playwright e' una libreria di
rete, e `app/tests/test_llm_modes.py` verifica che sotto `app/` non ce ne sia
nessuna.
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
RITMO = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0


def passo(numero: str, cosa: str, pausa: float = 2.2) -> None:
    print(f"\n  [{numero}] {cosa}")
    time.sleep(pausa * RITMO)


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


def demo() -> None:
    porta = porta_libera()
    server = avvia_server(porta)
    base = f"http://127.0.0.1:{porta}"
    print(f"server su {base}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=280 * RITMO)
            pagina = browser.new_context(
                viewport={"width": 900, "height": 1000}
            ).new_page()

            passo("1", "La casella di Maria: sei email, ognuna col suo semaforo")
            pagina.goto(base)
            pagina.wait_for_selector(".voce")
            pagina.wait_for_function(
                "document.querySelectorAll('.pallino-attesa').length === 0",
                timeout=20000,
            )
            time.sleep(2.0 * RITMO)

            passo("2", "Il medico: burocratese tradotto in Chi / Cosa / Entro quando")
            pagina.locator(".voce", has_text="Bianchi").first.click()
            pagina.wait_for_selector("#scheda-riassunto")

            passo("3", "I comandi della voce: ascoltare e dettare, non un extra")
            pagina.locator("#btn-ascolta-riassunto").scroll_into_view_if_needed()

            passo("4", "Il riquadro bianco vuoto diventa tre scelte")
            pagina.locator("#scheda-risposta").scroll_into_view_if_needed()
            pagina.locator(".intento", has_text="Confermo che vengo").click()
            pagina.wait_for_selector("#testo-bozza")

            passo("5", "Data e ora vengono dai fatti verificati, non da un modello", 3.0)

            passo("6", "L'avviso prima di dettare: l'unica cosa che esce dal dispositivo")
            pagina.locator("#btn-detta").click()
            pagina.wait_for_selector(".voce-avviso")
            time.sleep(2.4 * RITMO)
            pagina.locator("[data-no]").click()

            passo("7", "L'ultimo click e' sempre umano")
            pagina.locator("#btn-invia").click()
            pagina.wait_for_selector("#conferma-invio:not([hidden])")

            passo("8", "La finta Poste: rosso, e il numero viene dal codice, non dall'email")
            pagina.goto(base)
            pagina.wait_for_selector(".voce")
            pagina.locator(".voce", has_text="Poste").first.click()
            pagina.wait_for_selector("#semaforo")
            time.sleep(2.6 * RITMO)

            passo("9", "L'INPS dice soldi e urgente come la precedente, ma e' vera")
            pagina.goto(base)
            pagina.wait_for_selector(".voce")
            pagina.locator(".voce", has_text="INPS").first.click()
            pagina.wait_for_selector("#semaforo")
            time.sleep(2.4 * RITMO)

            passo("10", "Modo tecnico: qui la giuria vede la pipeline, Maria no")
            pagina.goto(f"{base}/?tecnico=1")
            pagina.wait_for_selector(".voce")
            pagina.locator(".voce", has_text="INPS").first.click()
            pagina.wait_for_selector("#semaforo")
            pagina.locator(".scheda-ragionamento").scroll_into_view_if_needed()
            pagina.locator(".scheda-ragionamento summary").click()
            time.sleep(3.0 * RITMO)

            passo("11", "«E se l'AI sbaglia?» — FactGuard rifiuta, dal vivo", 1.0)
            pagina.locator("#btn-avvelena").click()
            pagina.wait_for_selector("#scheda-verifica:not([hidden])")
            pagina.locator("#scheda-verifica").scroll_into_view_if_needed()
            time.sleep(4.5 * RITMO)

            print("\n  fine. Chiudo fra qualche secondo.")
            time.sleep(3.0 * RITMO)
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)


if __name__ == "__main__":
    demo()
