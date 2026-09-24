"""Il contrasto AAA non è una promessa: è un calcolo, e qui si rifà a ogni run.

Il progetto dichiara **≥ 7:1 ovunque** (WCAG AAA, non AA) perché Maria ha una
cataratta iniziale. È l'affermazione di accessibilità più forte che facciamo,
ed è anche la più facile da rompere senza accorgersene: basta schiarire un
colore di mezzo tono durante un ritocco grafico.

Le coppie sono lette **dal foglio di stile vero**, non ricopiate qui: se
qualcuno cambia `--verde` in `style.css`, questo test cambia con lui.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

FOGLIO = Path(__file__).resolve().parents[1] / "frontend" / "style.css"

SOGLIA_AAA = 7.0


def _leggi_variabili() -> dict[str, str]:
    testo = FOGLIO.read_text(encoding="utf-8")
    return {
        nome: valore.lower()
        for nome, valore in re.findall(r"(--[a-z-]+):\s*(#[0-9a-fA-F]{6})\s*;", testo)
    }


def _luminanza(colore: str) -> float:
    grezzo = colore.lstrip("#")
    canali = [int(grezzo[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lineari = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canali]
    return 0.2126 * lineari[0] + 0.7152 * lineari[1] + 0.0722 * lineari[2]


def _rapporto(primo: str, secondo: str) -> float:
    a, b = _luminanza(primo), _luminanza(secondo)
    chiaro, scuro = max(a, b), min(a, b)
    return (chiaro + 0.05) / (scuro + 0.05)


# (testo, fondo, dove si vede) — ogni coppia che l'interfaccia mette davvero
# insieme. Aggiungerne una qui costa una riga; dimenticarla costa un requisito.
COPPIE = [
    ("--inchiostro", "--sfondo", "testo sulle schede"),
    ("--inchiostro", "--pagina", "testo sul fondo pagina"),
    ("--inchiostro-tenue", "--sfondo", "testo secondario sulle schede"),
    ("--inchiostro-tenue", "--pagina", "testo secondario sul fondo"),
    ("--inchiostro-tenue", "--sfondo-tenue", "peso allegato, originale citato"),
    ("--verde", "--sfondo", "verdetto verde"),
    ("--verde", "--verde-fondo", "pastiglia e semaforo verde"),
    ("--giallo", "--sfondo", "verdetto giallo"),
    ("--giallo", "--giallo-fondo", "pastiglia e semaforo giallo"),
    ("--rosso", "--sfondo", "verdetto rosso"),
    ("--rosso", "--rosso-fondo", "pastiglia e semaforo rosso"),
    ("--accento", "--sfondo", "collegamenti e «torna indietro»"),
    ("--accento-scuro", "--accento-fondo", "testo sui pulsanti tenui"),
    ("--blu", "--blu-fondo", "«Già risposto»"),
    ("--attesa", "--attesa-fondo", "«Guada sta verificando»"),
]

# Testo bianco sopra i fondi pieni dei pulsanti.
SU_PIENO = [
    ("--accento", "pulsanti principali"),
    ("--verde", "«Invia la risposta»"),
    ("--rosso", "«Ferma la lettura», «Scatta»"),
]


@pytest.mark.parametrize("testo,fondo,dove", COPPIE)
def test_ogni_coppia_raggiunge_il_contrasto_aaa(testo: str, fondo: str, dove: str):
    var = _leggi_variabili()
    assert testo in var, f"{testo} non è più definita in style.css"
    assert fondo in var, f"{fondo} non è più definita in style.css"

    rapporto = _rapporto(var[testo], var[fondo])
    assert rapporto >= SOGLIA_AAA, (
        f"{dove}: {var[testo]} su {var[fondo]} dà {rapporto:.2f}:1, "
        f"sotto il {SOGLIA_AAA}:1 dichiarato dal progetto"
    )


@pytest.mark.parametrize("fondo,dove", SU_PIENO)
def test_il_bianco_sui_pulsanti_pieni_raggiunge_l_aaa(fondo: str, dove: str):
    var = _leggi_variabili()
    rapporto = _rapporto("#ffffff", var[fondo])
    assert rapporto >= SOGLIA_AAA, (
        f"{dove}: bianco su {var[fondo]} dà {rapporto:.2f}:1"
    )


def test_il_testo_di_base_resta_a_venti_pixel():
    """La cataratta iniziale impone 20px: non è una preferenza estetica."""
    testo = FOGLIO.read_text(encoding="utf-8")
    assert re.search(r"html\s*\{[^}]*font-size:\s*20px", testo), (
        "la base di 20px è sparita da style.css"
    )


def test_le_aree_di_tocco_restano_almeno_quarantotto():
    testo = FOGLIO.read_text(encoding="utf-8")
    tocco = re.search(r"--tocco:\s*(\d+)px", testo)
    largo = re.search(r"--tocco-largo:\s*(\d+)px", testo)
    assert tocco and int(tocco.group(1)) >= 48, "il target minimo è sceso sotto 48px"
    assert largo and int(largo.group(1)) >= 48
