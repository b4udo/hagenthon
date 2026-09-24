"""API di Posta Chiara.

Nota di montaggio: StaticFiles va montato **per ultimo**, dopo le rotte /api.
Montato per primo su "/", le inghiottirebbe tutte.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel

from . import clock, db, orchestrator
from .contracts import Email
from .engines import gulpease
from .llm import client
from .state import store

CARTELLA_FRONTEND = Path(__file__).resolve().parents[1] / "frontend"

app = FastAPI(
    title="Posta Chiara",
    description=(
        "Client di posta semplificato e assistito. "
        "Nessuna chiave API: il progetto non contiene codice di rete."
    ),
    version="1.0.0",
)


@app.middleware("http")
async def niente_cache(request: Request, call_next):
    """In sviluppo il JS cachato costa venti minuti di diagnosi sbagliata."""
    risposta = await call_next(request)
    risposta.headers["Cache-Control"] = "no-store"
    return risposta


# ───────────────────────────── modelli ─────────────────────────────


class RichiestaInvio(BaseModel):
    intento: str
    testo: str


# ───────────────────────────── rotte ─────────────────────────────


@app.get("/api/salute")
def salute() -> dict:
    return {
        "stato": "ok",
        "oggi": clock.oggi().isoformat(),
        "llm_mode": client.modalita(),
        "chiave_api_richiesta": False,
    }


@app.get("/api/mailbox")
def mailbox() -> dict:
    return {
        "proprietario": db.proprietario(),
        "email": db.elenco_email(),
        "inviate": db.conteggio_invii(),
    }


@app.get("/api/email/{email_id}")
def dettaglio(email_id: str) -> dict:
    email = db.leggi_email(email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Email non trovata")
    return email


@app.post("/api/email/{email_id}/elabora")
def elabora(email_id: str, avvelena: bool = False, ricalcola: bool = False) -> dict:
    grezza = db.leggi_email(email_id)
    if grezza is None:
        raise HTTPException(status_code=404, detail="Email non trovata")

    email = Email.model_validate(grezza)
    proprietario = db.proprietario()

    risultato = orchestrator.elabora(
        email,
        nome_utente=proprietario.get("nome", "Maria Rossi"),
        avvelena=avvelena,
        riusa_stato=not ricalcola,
    )

    payload = risultato.model_dump()
    payload["leggibilita"] = _leggibilita(email, risultato)
    return payload


def _leggibilita(email: Email, risultato) -> dict:
    prima = gulpease.gulpease(email.corpo)
    dopo = (
        gulpease.gulpease(risultato.semplificazione.testo_semplificato)
        if risultato.semplificazione and risultato.semplificazione_mostrata
        else None
    )
    return {
        "prima": prima,
        "prima_giudizio": gulpease.giudizio(prima),
        "dopo": dopo,
        "dopo_giudizio": gulpease.giudizio(dopo) if dopo is not None else None,
    }


@app.post("/api/email/{email_id}/invia")
def invia(email_id: str, richiesta: RichiestaInvio) -> dict:
    """L'ultimo click e' sempre umano.

    Non esiste alcun percorso in cui il sistema invii da solo: questa rotta si
    raggiunge unicamente da un'azione esplicita di Maria, dopo che ha riletto
    la bozza.
    """
    if db.leggi_email(email_id) is None:
        raise HTTPException(status_code=404, detail="Email non trovata")
    if not richiesta.testo.strip():
        raise HTTPException(status_code=400, detail="Il testo della risposta e' vuoto")

    db.registra_invio(
        email_id,
        richiesta.intento,
        richiesta.testo,
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    return {"inviata": True, "completate_da_sola": db.conteggio_invii()}


@app.get("/api/autonomia")
def autonomia() -> dict:
    """Il contatore che rende misurabile il guadagno, non solo raccontabile."""
    return {
        "completate_da_sola": db.conteggio_invii(),
        "azioni": db.invii(),
    }


@app.get("/api/debug/stato")
def debug_stato() -> dict:
    """Lo stato esternalizzato, in chiaro. Si apre in demo."""
    return {"llm_mode": client.modalita(), "checkpoint": store.elenco()}


@app.exception_handler(Exception)
async def guasto_non_previsto(request: Request, exc: Exception) -> JSONResponse:
    """Nessun errore grezzo raggiunge Maria."""
    return JSONResponse(
        status_code=500,
        content={
            "errore": "Qualcosa non ha funzionato. Riprovi fra un momento.",
            "dettaglio_tecnico": str(exc),
        },
    )


# ★ Per ultimo, dopo tutte le rotte /api.
if CARTELLA_FRONTEND.exists():
    app.mount("/", StaticFiles(directory=CARTELLA_FRONTEND, html=True), name="frontend")
