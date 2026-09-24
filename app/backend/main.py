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
from .agents import sicurezza
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


class AllegatoInviato(BaseModel):
    """I metadati dell'allegato, non i suoi byte.

    Il file resta nel browser. Questo prototipo non ha un trasporto di posta
    reale: caricare i byte darebbe l'impressione di una spedizione che non
    avviene, e metterebbe il documento d'identita' di una persona su un disco
    senza che nessuno l'abbia chiesto.
    """

    nome: str
    tipo: str = "sconosciuto"
    dimensione: int = 0


class RichiestaInvio(BaseModel):
    intento: str
    testo: str
    allegato: AllegatoInviato | None = None


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
def mailbox(cartella: str = db.IN_ARRIVO) -> dict:
    """La casella, una cartella per volta.

    `inviata` non contiene email ricevute ma le risposte di Maria: hanno un
    destinatario invece di un mittente, quindi arrivano da `posta_inviata()` e
    non dalla tabella `email`. Il frontend le distingue dal campo `tipo`.
    """
    if cartella not in db.CARTELLE:
        raise HTTPException(status_code=400, detail="Cartella sconosciuta")

    if cartella == db.INVIATA:
        elementi = db.posta_inviata()
        tipo = "inviata"
    else:
        elementi = db.elenco_email(cartella)
        tipo = "ricevuta"

    # `conteggi_cartelle()` conta gia' gli invii: richiederli a parte
    # ripeterebbe la stessa query, e con lei la stessa presa del lock.
    conteggi = db.conteggi_cartelle()
    return {
        "proprietario": db.proprietario(),
        "cartella": cartella,
        "tipo": tipo,
        "email": elementi,
        "conteggi": conteggi,
        "inviate": conteggi[db.INVIATA],
    }


@app.post("/api/email/{email_id}/elimina")
def elimina(email_id: str) -> dict:
    """Sposta nel cestino. Non cancella: l'email cambia cartella.

    Con un tremore alla mano, una cancellazione irreversibile e' esattamente
    l'errore che toglie autonomia invece di darla.
    """
    if not db.sposta(email_id, db.ELIMINATA):
        raise HTTPException(status_code=404, detail="Email non trovata")
    return {"cartella": db.ELIMINATA, "conteggi": db.conteggi_cartelle()}


@app.post("/api/email/{email_id}/ripristina")
def ripristina(email_id: str) -> dict:
    if not db.sposta(email_id, db.IN_ARRIVO):
        raise HTTPException(status_code=404, detail="Email non trovata")
    return {"cartella": db.IN_ARRIVO, "conteggi": db.conteggi_cartelle()}


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
    # Se Maria ha gia' risposto, l'interfaccia lo dice invece di riproporle le
    # stesse tre scelte come se non fosse successo niente.
    payload["gia_risposto"] = db.ha_risposto(email_id)
    payload["inoltrata"] = db.e_inoltrata(email_id)
    payload["cartella"] = grezza.get("cartella", db.IN_ARRIVO)
    return payload


def _leggibilita(email: Email, risultato) -> dict:
    """Tre misure, non una, perche' raccontano cose diverse.

    Il testo riscritto guadagna poco: un motore a regole non puo' rifondere i
    periodi senza rischiare di storpiarli, e non lo fa apposta. Il guadagno
    vero sta nel riassunto Chi / Cosa / Entro quando, che e' cio' che Maria
    legge per primo. Riportiamo entrambi: un solo numero, scelto fra i due,
    sarebbe una mezza verita'.
    """
    prima = gulpease.gulpease(email.corpo)
    s = risultato.semplificazione

    dopo = (
        gulpease.gulpease(s.testo_semplificato)
        if s and risultato.semplificazione_mostrata
        else None
    )

    riassunto = None
    if s and risultato.semplificazione_mostrata:
        testo_riassunto = " ".join(
            filter(None, [s.chi_scrive, s.cosa_vogliono, s.entro_quando])
        )
        riassunto = gulpease.gulpease(testo_riassunto)

    return {
        "prima": prima,
        "prima_giudizio": gulpease.giudizio(prima),
        "dopo": dopo,
        "dopo_giudizio": gulpease.giudizio(dopo) if dopo is not None else None,
        "riassunto": riassunto,
        "riassunto_giudizio": gulpease.giudizio(riassunto) if riassunto is not None else None,
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
        allegato=richiesta.allegato.model_dump() if richiesta.allegato else None,
    )
    return {
        "inviata": True,
        "completate_da_sola": db.conteggio_invii(),
        "allegato": richiesta.allegato.nome if richiesta.allegato else None,
    }


@app.post("/api/email/{email_id}/aiuto")
def chiedi_aiuto(email_id: str) -> dict:
    """Gira il messaggio a una persona di fiducia.

    Deve essere raggiungibile **sempre**, non solo quando il semaforo e'
    giallo: il momento in cui una persona si sente in difficolta' non coincide
    con il momento in cui il sistema ha dei dubbi. Legarlo al verdetto
    significherebbe offrire aiuto solo quando lo decidiamo noi.

    Chiedere aiuto non e' un fallimento del percorso: e' un esito legittimo, e
    viene registrato come le risposte.
    """
    if db.leggi_email(email_id) is None:
        raise HTTPException(status_code=404, detail="Email non trovata")

    a_chi = sicurezza.NOME_PERSONA_FIDUCIA
    db.registra_aiuto(
        email_id, a_chi, datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    return {
        "inoltrata": True,
        "a_chi": a_chi,
        "messaggio": f"Ho girato il messaggio a {a_chi}. La richiamerà lui.",
        "aiuti": db.conteggio_aiuti(),
    }


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
