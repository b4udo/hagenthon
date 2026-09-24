"""Database in memoria — tutti i dati simulati stanno qui.

Perche' SQLite e non H2: H2 e' un database Java e non ha un driver Python che
non richieda una JVM. `sqlite3` e' nella libreria standard, quindi offre la
stessa proprieta' (in memoria, nessun file, azzerato a ogni riavvio,
interrogabile in SQL) **senza aggiungere una sola dipendenza** — e le
dipendenze di questo progetto sono congelate.

Il database e' popolato all'avvio da `data/mailbox.json`, che resta la fonte
leggibile del corpus. Da quel momento in poi l'applicazione legge solo dal
database: il JSON e' il seme, non il magazzino.

Nota sulla connessione: con `:memory:` ogni connessione avrebbe un database
tutto suo. Qui la connessione e' una sola, condivisa fra i thread di uvicorn e
protetta da un lock.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

PERCORSO_SEME = Path(__file__).resolve().parent / "data" / "mailbox.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS email (
    id              TEXT PRIMARY KEY,
    mittente_nome   TEXT NOT NULL,
    mittente_email  TEXT NOT NULL,
    oggetto         TEXT NOT NULL,
    corpo           TEXT NOT NULL,
    data_ricezione  TEXT NOT NULL,
    in_rubrica      INTEGER NOT NULL DEFAULT 0,
    allegati        TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS rubrica (
    email  TEXT PRIMARY KEY,
    nome   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS proprietario (
    chiave  TEXT PRIMARY KEY,
    valore  TEXT NOT NULL
);

-- Stato esternalizzato della pipeline: fuori dal contesto degli agenti,
-- interrogabile in SQL, ispezionabile in demo da /api/debug/stato.
CREATE TABLE IF NOT EXISTS stato_pipeline (
    email_id      TEXT PRIMARY KEY,
    risultato     TEXT NOT NULL,
    aggiornato_il TEXT NOT NULL
);

-- Le risposte che Maria ha effettivamente inviato. Alimenta il contatore
-- di autonomia: "azioni completate da sola".
CREATE TABLE IF NOT EXISTS invio (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id   TEXT NOT NULL,
    intento    TEXT NOT NULL,
    testo      TEXT NOT NULL,
    inviato_il TEXT NOT NULL
);
"""

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()


def connessione() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        with _lock:
            if _conn is None:
                _conn = sqlite3.connect(":memory:", check_same_thread=False)
                _conn.row_factory = sqlite3.Row
                _conn.executescript(SCHEMA)
                _popola(_conn)
    return _conn


def _popola(conn: sqlite3.Connection) -> None:
    if not PERCORSO_SEME.exists():
        return

    dati = json.loads(PERCORSO_SEME.read_text(encoding="utf-8"))

    proprietario = dati.get("proprietario", {})
    conn.executemany(
        "INSERT OR REPLACE INTO proprietario (chiave, valore) VALUES (?, ?)",
        [(k, str(v)) for k, v in proprietario.items()],
    )

    conn.executemany(
        "INSERT OR REPLACE INTO rubrica (email, nome) VALUES (?, ?)",
        [(c["email"], c["nome"]) for c in dati.get("rubrica", [])],
    )

    conn.executemany(
        """INSERT OR REPLACE INTO email
           (id, mittente_nome, mittente_email, oggetto, corpo,
            data_ricezione, in_rubrica, allegati)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                e["id"],
                e["mittente_nome"],
                e["mittente_email"],
                e["oggetto"],
                e["corpo"],
                e["data_ricezione"],
                1 if e.get("in_rubrica") else 0,
                json.dumps(e.get("allegati", []), ensure_ascii=False),
            )
            for e in dati.get("email", [])
        ],
    )
    conn.commit()


def reimposta() -> None:
    """Ricrea il database da zero. Usato dai test per isolarsi."""
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
        _conn = None


# ─────────────────────────── letture ───────────────────────────


def _riga_a_email(r: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": r["id"],
        "mittente_nome": r["mittente_nome"],
        "mittente_email": r["mittente_email"],
        "oggetto": r["oggetto"],
        "corpo": r["corpo"],
        "data_ricezione": r["data_ricezione"],
        "in_rubrica": bool(r["in_rubrica"]),
        "allegati": json.loads(r["allegati"]),
    }


def elenco_email() -> list[dict[str, Any]]:
    cur = connessione().execute(
        "SELECT * FROM email ORDER BY data_ricezione DESC, id ASC"
    )
    return [_riga_a_email(r) for r in cur.fetchall()]


def leggi_email(email_id: str) -> dict[str, Any] | None:
    cur = connessione().execute("SELECT * FROM email WHERE id = ?", (email_id,))
    r = cur.fetchone()
    return _riga_a_email(r) if r else None


def rubrica() -> list[dict[str, str]]:
    cur = connessione().execute("SELECT nome, email FROM rubrica ORDER BY nome")
    return [{"nome": r["nome"], "email": r["email"]} for r in cur.fetchall()]


def in_rubrica(indirizzo: str) -> bool:
    cur = connessione().execute(
        "SELECT 1 FROM rubrica WHERE lower(email) = lower(?)", (indirizzo,)
    )
    return cur.fetchone() is not None


def proprietario() -> dict[str, str]:
    cur = connessione().execute("SELECT chiave, valore FROM proprietario")
    return {r["chiave"]: r["valore"] for r in cur.fetchall()}


# ────────────────────── stato della pipeline ──────────────────────


def salva_stato(email_id: str, risultato_json: str, quando: str) -> None:
    conn = connessione()
    with _lock:
        conn.execute(
            """INSERT OR REPLACE INTO stato_pipeline
               (email_id, risultato, aggiornato_il) VALUES (?, ?, ?)""",
            (email_id, risultato_json, quando),
        )
        conn.commit()


def leggi_stato(email_id: str) -> str | None:
    cur = connessione().execute(
        "SELECT risultato FROM stato_pipeline WHERE email_id = ?", (email_id,)
    )
    r = cur.fetchone()
    return r["risultato"] if r else None


def dimentica_stato(email_id: str) -> None:
    conn = connessione()
    with _lock:
        conn.execute("DELETE FROM stato_pipeline WHERE email_id = ?", (email_id,))
        conn.commit()


def stati_salvati() -> list[dict[str, str]]:
    cur = connessione().execute(
        "SELECT email_id, aggiornato_il FROM stato_pipeline ORDER BY aggiornato_il DESC"
    )
    return [
        {"email_id": r["email_id"], "aggiornato_il": r["aggiornato_il"]}
        for r in cur.fetchall()
    ]


# ───────────────────────────── invii ─────────────────────────────


def registra_invio(email_id: str, intento: str, testo: str, quando: str) -> None:
    conn = connessione()
    with _lock:
        conn.execute(
            "INSERT INTO invio (email_id, intento, testo, inviato_il) VALUES (?, ?, ?, ?)",
            (email_id, intento, testo, quando),
        )
        conn.commit()


def invii() -> list[dict[str, Any]]:
    cur = connessione().execute("SELECT * FROM invio ORDER BY id")
    return [
        {
            "email_id": r["email_id"],
            "intento": r["intento"],
            "testo": r["testo"],
            "inviato_il": r["inviato_il"],
        }
        for r in cur.fetchall()
    ]


def conteggio_invii() -> int:
    cur = connessione().execute("SELECT COUNT(*) AS n FROM invio")
    return int(cur.fetchone()["n"])
