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
    allegati        TEXT NOT NULL DEFAULT '[]',
    -- 'in_arrivo' | 'eliminata'. La posta inviata non sta qui: e' la tabella
    -- `invio`, perche' una risposta non e' un'email ricevuta con un flag
    -- diverso — ha un destinatario invece di un mittente.
    cartella        TEXT NOT NULL DEFAULT 'in_arrivo'
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

# Rientrante di proposito: `interroga()` prende il lock e poi chiama
# `connessione()`, che puo' prenderlo a sua volta alla prima inizializzazione.
# Con un Lock semplice sarebbe un blocco immediato.
_lock = threading.RLock()


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


def interroga(sql: str, parametri: tuple = ()) -> list[sqlite3.Row]:
    """Ogni lettura passa da qui, sotto lock.

    Una connessione sqlite3 condivisa fra thread non tollera execute()
    concorrenti: solleva "bad parameter or other API misuse". Uvicorn serve
    gli endpoint sincroni da un threadpool e l'interfaccia chiede le sei
    email tutte insieme all'apertura, quindi la concorrenza non e' teorica —
    e' il caso normale. Proteggere solo le scritture non basta: il guasto si
    e' visto in un test end-to-end su browser vero.
    """
    with _lock:
        return connessione().execute(sql, parametri).fetchall()


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


IN_ARRIVO = "in_arrivo"
ELIMINATA = "eliminata"
INVIATA = "inviata"          # cartella virtuale: vive nella tabella `invio`

CARTELLE = (IN_ARRIVO, INVIATA, ELIMINATA)


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
        "cartella": r["cartella"],
    }


def elenco_email(cartella: str = IN_ARRIVO) -> list[dict[str, Any]]:
    """Le email di una cartella, con l'indicazione di quelle gia' risposte.

    `gia_risposto` non e' una colonna: e' il fatto che esista un invio legato a
    quell'email. Tenerlo derivato invece che memorizzato significa che non puo'
    andare fuori sincrono con la verita', che e' la tabella `invio`.
    """
    righe = interroga(
        "SELECT * FROM email WHERE cartella = ? ORDER BY data_ricezione DESC, id ASC",
        (cartella,),
    )
    risposte = id_con_risposta()
    elenco = []
    for r in righe:
        email = _riga_a_email(r)
        email["gia_risposto"] = email["id"] in risposte
        elenco.append(email)
    return elenco


def id_con_risposta() -> set[str]:
    """Gli id delle email a cui Maria ha gia' risposto."""
    return {r["email_id"] for r in interroga("SELECT DISTINCT email_id FROM invio")}


def conteggi_cartelle() -> dict[str, int]:
    in_arrivo = interroga(
        "SELECT COUNT(*) AS n FROM email WHERE cartella = ?", (IN_ARRIVO,)
    )[0]["n"]
    eliminate = interroga(
        "SELECT COUNT(*) AS n FROM email WHERE cartella = ?", (ELIMINATA,)
    )[0]["n"]
    return {
        IN_ARRIVO: int(in_arrivo),
        INVIATA: conteggio_invii(),
        ELIMINATA: int(eliminate),
    }


def sposta(email_id: str, cartella: str) -> bool:
    """Sposta un'email fra le cartelle. Falso se l'email non esiste.

    Eliminare e' reversibile per costruzione: l'email cambia cartella, non
    sparisce. Una cancellazione irreversibile con un tremore alla mano e' il
    genere di errore che toglie autonomia invece di darla.
    """
    if cartella not in (IN_ARRIVO, ELIMINATA):
        raise ValueError(f"cartella non valida: {cartella}")
    conn = connessione()
    with _lock:
        cursore = conn.execute(
            "UPDATE email SET cartella = ? WHERE id = ?", (cartella, email_id)
        )
        conn.commit()
        return cursore.rowcount > 0


def leggi_email(email_id: str) -> dict[str, Any] | None:
    righe = interroga("SELECT * FROM email WHERE id = ?", (email_id,))
    return _riga_a_email(righe[0]) if righe else None


def rubrica() -> list[dict[str, str]]:
    righe = interroga("SELECT nome, email FROM rubrica ORDER BY nome")
    return [{"nome": r["nome"], "email": r["email"]} for r in righe]


def in_rubrica(indirizzo: str) -> bool:
    return bool(
        interroga("SELECT 1 FROM rubrica WHERE lower(email) = lower(?)", (indirizzo,))
    )


def proprietario() -> dict[str, str]:
    return {r["chiave"]: r["valore"] for r in interroga("SELECT chiave, valore FROM proprietario")}


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
    righe = interroga(
        "SELECT risultato FROM stato_pipeline WHERE email_id = ?", (email_id,)
    )
    return righe[0]["risultato"] if righe else None


def dimentica_stato(email_id: str) -> None:
    conn = connessione()
    with _lock:
        conn.execute("DELETE FROM stato_pipeline WHERE email_id = ?", (email_id,))
        conn.commit()


def stati_salvati() -> list[dict[str, str]]:
    righe = interroga(
        "SELECT email_id, aggiornato_il FROM stato_pipeline ORDER BY aggiornato_il DESC"
    )
    return [
        {"email_id": r["email_id"], "aggiornato_il": r["aggiornato_il"]} for r in righe
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
    return [
        {
            "email_id": r["email_id"],
            "intento": r["intento"],
            "testo": r["testo"],
            "inviato_il": r["inviato_il"],
        }
        for r in interroga("SELECT * FROM invio ORDER BY id")
    ]


def conteggio_invii() -> int:
    return int(interroga("SELECT COUNT(*) AS n FROM invio")[0]["n"])


def posta_inviata() -> list[dict[str, Any]]:
    """Le risposte inviate, pronte da mostrare.

    Destinatario e oggetto vengono dall'email originale: una risposta non
    ripete quei dati, li eredita dal messaggio a cui risponde. Si legge con una
    join invece di duplicarli nella tabella `invio`, dove potrebbero divergere.
    """
    righe = interroga(
        """SELECT i.id, i.email_id, i.intento, i.testo, i.inviato_il,
                  e.mittente_nome, e.mittente_email, e.oggetto
           FROM invio i
           LEFT JOIN email e ON e.id = i.email_id
           ORDER BY i.id DESC"""
    )
    return [
        {
            "id": f"inv-{r['id']}",
            "email_id": r["email_id"],
            "destinatario_nome": r["mittente_nome"] or "(destinatario sconosciuto)",
            "destinatario_email": r["mittente_email"] or "",
            "oggetto": _oggetto_di_risposta(r["oggetto"]),
            "testo": r["testo"],
            "intento": r["intento"],
            "inviato_il": r["inviato_il"],
        }
        for r in righe
    ]


def _oggetto_di_risposta(oggetto: str | None) -> str:
    if not oggetto:
        return "Risposta"
    return oggetto if oggetto.lower().startswith("re:") else f"Re: {oggetto}"
