"""Orchestratore — ordine, limiti e stato.

La regola che questi test difendono: l'orchestratore non ha il diritto di
restituire un errore all'interfaccia. Un agente che fallisce degrada la
pipeline, non la uccide.
"""

from __future__ import annotations

from app.backend import db, orchestrator
from app.backend.agents import triage, verificatore
from app.backend.contracts import (
    EsitoAgente,
    EsitoVerifica,
    ModalitaAgente,
    Semaforo,
)
from app.backend.state import store

TUTTE_LE_EMAIL = ("em-01", "em-02", "em-03", "em-04", "em-05", "em-06")


def _tracce_di(risultato, prefisso: str) -> list:
    return [t for t in risultato.tracce if t.agente.startswith(prefisso)]


def test_pipeline_completa_su_email_del_corpus(leggi_email):
    risultato = orchestrator.elabora(leggi_email("em-01"))

    assert risultato.email_id == "em-01"
    assert risultato.triage is not None and risultato.sicurezza is not None
    assert {f.tipo.value for f in risultato.fatti} >= {"data", "orario"}
    assert risultato.verifica is not None and risultato.verifica.passa is True
    assert risultato.semplificazione_mostrata is True
    assert len(risultato.bozze) == 3
    assert risultato.tracce


def test_semaforo_rosso_non_produce_bozze(leggi_email):
    risultato = orchestrator.elabora(leggi_email("em-03"))

    assert risultato.sicurezza is not None
    assert risultato.sicurezza.semaforo is Semaforo.ROSSO
    assert risultato.bozze == []
    compositore = _tracce_di(risultato, "06-compositore")
    assert compositore and compositore[0].nota.startswith("non eseguito")


def test_limite_di_tentativi_rispettato(monkeypatch, leggi_email):
    def verifica_sempre_fallita(fatti, testo, anno):
        return EsitoVerifica(
            passa=False, problemi=[], feedback_per_retry="riprova conservando i fatti"
        )

    monkeypatch.setattr(verificatore, "verifica", verifica_sempre_fallita)
    risultato = orchestrator.elabora(leggi_email("em-01"), riusa_stato=False)

    attesi = orchestrator.MAX_SIMPLIFY_RETRIES + 1
    assert len(_tracce_di(risultato, "05-verificatore")) == attesi
    assert len(_tracce_di(risultato, "04-semplificatore")) == attesi
    assert risultato.semplificazione_mostrata is False


def test_agente_in_errore_non_uccide_la_pipeline(monkeypatch, leggi_email):
    def esplode(*args, **kwargs):
        raise RuntimeError("guasto simulato")

    monkeypatch.setattr(triage, "esegui", esplode)
    risultato = orchestrator.elabora(leggi_email("em-01"), riusa_stato=False)

    traccia = _tracce_di(risultato, "01-triage")[0]
    assert traccia.esito is EsitoAgente.ERRORE
    assert "errore" in traccia.nota
    # Il fallback dichiarato dell'agente, non un'eccezione verso l'interfaccia.
    assert risultato.triage is not None and risultato.triage.confidenza == 0.0
    assert risultato.sicurezza is not None


def test_stato_persistito_e_riletto_dal_checkpoint(monkeypatch, leggi_email):
    email = leggi_email("em-02")
    primo = orchestrator.elabora(email)

    assert db.leggi_stato("em-02") is not None
    assert store.carica("em-02") is not None

    def esplode(*args, **kwargs):
        raise AssertionError("la pipeline non doveva essere rieseguita")

    monkeypatch.setattr(triage, "esegui", esplode)
    secondo = orchestrator.elabora(email)

    assert secondo.model_dump() == primo.model_dump()


def test_avvelena_fa_rifiutare_la_semplificazione(leggi_email):
    risultato = orchestrator.elabora(leggi_email("em-04"), avvelena=True)

    assert risultato.semplificazione_mostrata is False
    assert risultato.verifica is not None and risultato.verifica.passa is False
    assert risultato.verifica.problemi
    # L'espediente da demo non deve lasciare traccia nello stato salvato.
    assert db.leggi_stato("em-04") is None


def test_ogni_risultato_porta_le_tracce(leggi_email):
    for email_id in TUTTE_LE_EMAIL:
        risultato = orchestrator.elabora(leggi_email(email_id))

        assert risultato.tracce, email_id
        assert all(t.agente for t in risultato.tracce), email_id
        # LLM_MODE spento: nessuna seam attraversata, nessun token speso.
        assert risultato.token_usati == 0, email_id
        assert all(t.modalita is ModalitaAgente.REGOLE for t in risultato.tracce)
