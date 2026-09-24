"""Stato esternalizzato della pipeline.

Lo stato vive fuori dal contesto degli agenti, in una tabella interrogabile in
SQL. Tre conseguenze concrete, tutte verificabili:

1. **Riprendibilita'** — se il processo cade a meta', al riavvio si rilegge il
   checkpoint invece di rifare tutto.
2. **Costo marginale zero** — ri-aprire un'email gia' vista non ri-esegue la
   pipeline e non consuma token.
3. **Ispezionabilita'** — /api/debug/stato mostra cosa ha deciso ogni agente.
   Lo stato non e' una variabile in memoria di cui fidarsi sulla parola.

Il database e' in memoria, quindi il punto 1 vale entro la vita del processo.
E' un limite dichiarato, non nascosto: vedi docs/AUTONOMIA-E-LIMITI.md.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .. import db
from ..contracts import RisultatoPipeline


def salva(risultato: RisultatoPipeline) -> None:
    db.salva_stato(
        risultato.email_id,
        risultato.model_dump_json(),
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def carica(email_id: str) -> RisultatoPipeline | None:
    grezzo = db.leggi_stato(email_id)
    if grezzo is None:
        return None
    try:
        return RisultatoPipeline.model_validate_json(grezzo)
    except ValueError:
        # Stato illeggibile o di una versione precedente del contratto:
        # si ignora e si ricalcola. Mai un errore all'utente.
        db.dimentica_stato(email_id)
        return None


def dimentica(email_id: str) -> None:
    db.dimentica_stato(email_id)


def elenco() -> list[dict[str, str]]:
    return db.stati_salvati()
