"""Contratti Pydantic — il confine tipato fra gli agenti della pipeline.

Ogni agente di agents/runtime/ dichiara qui il proprio output. Gli schema JSON
in agents/runtime/contracts/ sono generati da questi modelli: se un modello
cambia e lo schema no, test_contracts_sync.py diventa rosso.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


# ───────────────────────────── input ─────────────────────────────


class Allegato(BaseModel):
    nome: str
    tipo: str = "altro"  # pdf | immagine | altro
    dimensione_kb: int = 0


class Email(BaseModel):
    id: str
    mittente_nome: str
    mittente_email: str
    oggetto: str
    corpo: str
    data_ricezione: str  # ISO
    allegati: list[Allegato] = Field(default_factory=list)
    in_rubrica: bool = False


# ──────────────────────── 01 · triage ────────────────────────


class Categoria(StrEnum):
    SANITA = "sanita"
    ENTE_PUBBLICO = "ente_pubblico"
    PERSONA_CONOSCIUTA = "persona_conosciuta"
    COMMERCIALE = "commerciale"
    SCONOSCIUTO = "sconosciuto"


class Priorita(StrEnum):
    AZIONE_RICHIESTA = "azione_richiesta"
    INFORMATIVA = "informativa"
    SECONDO_PIANO = "secondo_piano"


class EsitoTriage(BaseModel):
    categoria: Categoria
    priorita: Priorita
    motivo: str
    confidenza: float = Field(ge=0.0, le=1.0)


# ─────────────────────── 02 · sicurezza ───────────────────────


class Semaforo(StrEnum):
    VERDE = "verde"
    GIALLO = "giallo"
    ROSSO = "rosso"


class TipoAzione(StrEnum):
    TELEFONO = "telefono"
    INOLTRA = "inoltra"
    RISPONDI = "rispondi"
    NESSUNA = "nessuna"


class AzioneSuggerita(BaseModel):
    tipo: TipoAzione
    etichetta: str
    valore: str | None = None


class EsitoSicurezza(BaseModel):
    semaforo: Semaforo
    messaggio: str
    segnali: list[str] = Field(default_factory=list)
    azione: AzioneSuggerita


# ──────────────────── 03 · estrazione fatti ────────────────────


class TipoFatto(StrEnum):
    DATA = "data"
    IMPORTO = "importo"
    ORARIO = "orario"


class Fatto(BaseModel):
    tipo: TipoFatto
    testo_originale: str
    valore_normalizzato: str
    ancora: str = ""
    posizione: int = 0


class EsitoEstrazione(BaseModel):
    fatti: list[Fatto] = Field(default_factory=list)


# ─────────────────── 04 · semplificatore ───────────────────


class EsitoSemplificazione(BaseModel):
    chi_scrive: str
    cosa_vogliono: str
    entro_quando: str | None = None
    testo_semplificato: str


# ──────────────── 05 · verificatore (FactGuard) ────────────────


class TipoProblema(StrEnum):
    MANCANTE = "mancante"
    ALTERATO = "alterato"
    INVENTATO = "inventato"


class ProblemaVerifica(BaseModel):
    tipo: TipoProblema
    fatto: Fatto | None = None
    trovato: str | None = None
    spiegazione: str


class EsitoVerifica(BaseModel):
    passa: bool
    problemi: list[ProblemaVerifica] = Field(default_factory=list)
    feedback_per_retry: str | None = None


# ──────────────────── 06 · compositore ────────────────────


class Intento(StrEnum):
    CONFERMA = "conferma"
    CHIEDI_INFO = "chiedi_info"
    NON_POSSO = "non_posso"


class BozzaRisposta(BaseModel):
    intento: Intento
    etichetta: str
    testo: str
    fatti_usati: list[Fatto] = Field(default_factory=list)


# ───────────────────── orchestratore ─────────────────────


class ModalitaAgente(StrEnum):
    REGOLE = "regole"
    LLM_REPLAY = "llm-replay"


class EsitoAgente(StrEnum):
    OK = "ok"
    FALLBACK = "fallback"
    ERRORE = "errore"


class TracciaAgente(BaseModel):
    """Una riga del pannello «Come ha ragionato».

    Rende la pipeline ispezionabile invece che magica: e' il modo piu'
    economico di mostrare la profondita' agentica a chi ha cinque minuti.
    """

    agente: str
    modalita: ModalitaAgente = ModalitaAgente.REGOLE
    durata_ms: int = 0
    esito: EsitoAgente = EsitoAgente.OK
    nota: str = ""
    token: int = 0


class RisultatoPipeline(BaseModel):
    email_id: str
    triage: EsitoTriage | None = None
    sicurezza: EsitoSicurezza | None = None
    fatti: list[Fatto] = Field(default_factory=list)
    semplificazione: EsitoSemplificazione | None = None
    verifica: EsitoVerifica | None = None
    bozze: list[BozzaRisposta] = Field(default_factory=list)

    # Falso => FactGuard ha rifiutato: l'interfaccia mostra l'originale.
    # Sta nel contratto, non in un if del frontend.
    semplificazione_mostrata: bool = False

    tracce: list[TracciaAgente] = Field(default_factory=list)
    token_usati: int = 0
