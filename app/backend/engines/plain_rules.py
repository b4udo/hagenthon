"""Burocratese italiano -> italiano comune.

Copre il burocratese *ricorrente* della posta istituzionale: convocazioni,
scadenze, certificati. Non copre il testo libero arbitrario, ed e' esattamente
per allargare questa copertura che esiste la seam LLM sul semplificatore.

Regola sopra tutte: **queste regole non toccano mai numeri, date o importi.**
Non riformattano nulla di cio' che FactGuard deve proteggere. Il modo piu'
semplice di superare un verificatore e' non dargli motivo di intervenire.
"""

from __future__ import annotations

import re

# Formule di rito: spariscono senza lasciare significato.
FORMULE_DA_RIMUOVERE = (
    r"ai sensi(?:\s+e\s+per\s+gli\s+effetti)?\s+(?:del|dell'|della|degli|di)[^,.;]*[,.;]?",
    r"a\s+norma\s+(?:del|dell'|della)[^,.;]*[,.;]?",
    r"con\s+la\s+presente\s*,?",
    r"si\s+comunica\s+che\s*",
    r"si\s+rende\s+noto\s+che\s*",
    r"la\s+presente\s+(?:comunicazione|nota)\s+",
    r"in\s+oggetto\s+(?:indicat[oa])?\s*,?",
    r"\(\s*D\.?\s*P\.?\s*R\.?[^)]*\)",
    r"\(\s*D\.?\s*Lgs\.?[^)]*\)",
    r"\bartt?\.\s*\d+[^,.;]*[,.;]?",
    r"\bcomma\s+\d+\s*",
)

# Lessico: il termine burocratico e il suo equivalente comune.
LESSICO = {
    "la S.V.": "lei",
    "la s.v.": "lei",
    "codesta spettabile": "la sua",
    "spettabile": "gentile",
    "convocazione": "appuntamento",
    "convocata": "attesa",
    "convocato": "atteso",
    "inoltrare istanza": "fare domanda",
    "presentare istanza": "fare domanda",
    "istanza": "domanda",
    "entro e non oltre": "entro",
    "recarsi presso": "andare",
    "recarsi": "andare",
    "munito di": "con",
    "munita di": "con",
    "esibire": "mostrare",
    "produrre la documentazione": "portare i documenti",
    "documentazione": "documenti",
    "provvedere al ritiro": "ritirare",
    "provvedere a": "",
    "si invita": "le chiediamo di",
    "si prega di": "le chiediamo di",
    "si prega": "le chiediamo",
    "e' fatto obbligo di": "deve",
    "in difetto": "altrimenti",
    "decorso il termine": "dopo questa data",
    "termine perentorio": "scadenza",
    "avente diritto": "chi ne ha diritto",
    "il sottoscritto": "io",
    "trasmettere": "mandare",
    "comunicazione": "lettera",
    "attestazione": "certificato",
    "erogazione": "pagamento",
    "importo netto in pagamento": "importo che riceve",
    "cedolino": "foglio della pensione",
    "sportello": "ufficio",
    "orario di apertura al pubblico": "orari",
}

MAX_PAROLE_FRASE = 25

_RE_SPAZI = re.compile(r"[ \t]{2,}")
_RE_RIGHE = re.compile(r"\n{3,}")


def semplifica_testo(testo: str) -> str:
    risultato = testo

    for schema in FORMULE_DA_RIMUOVERE:
        risultato = re.sub(schema, " ", risultato, flags=re.IGNORECASE)

    for burocratico, comune in LESSICO.items():
        risultato = re.sub(
            re.escape(burocratico), comune, risultato, flags=re.IGNORECASE
        )

    risultato = _spezza_frasi_lunghe(risultato)
    risultato = _ripulisci(risultato)
    return risultato


def _spezza_frasi_lunghe(testo: str) -> str:
    righe_finali = []
    for riga in testo.split("\n"):
        frasi = re.split(r"(?<=[.!?])\s+", riga)
        nuove = []
        for frase in frasi:
            parole = frase.split()
            if len(parole) <= MAX_PAROLE_FRASE:
                nuove.append(frase)
                continue
            # Si spezza su una congiunzione, non a meta' di un'informazione.
            spezzata = re.sub(
                r",\s+(e|ma|inoltre|nonche'|nonché|oltre a|pertanto|quindi)\s+",
                ". ",
                frase,
                count=2,
                flags=re.IGNORECASE,
            )
            nuove.append(spezzata)
        righe_finali.append(" ".join(nuove))
    return "\n".join(righe_finali)


def _ripulisci(testo: str) -> str:
    testo = _RE_SPAZI.sub(" ", testo)
    testo = re.sub(r"\s+([,.;:!?])", r"\1", testo)
    testo = re.sub(r"([,.;:])\1+", r"\1", testo)
    testo = re.sub(r"(?m)^[ \t]*[,.;:]\s*", "", testo)
    testo = _RE_RIGHE.sub("\n\n", testo)

    righe = []
    for riga in testo.split("\n"):
        riga = riga.strip()
        if riga:
            riga = riga[0].upper() + riga[1:]
        righe.append(riga)
    return "\n".join(righe).strip()


# ───────────── verbi d'azione, per «cosa vogliono» ─────────────

AZIONI = (
    ("confermare", "Le chiedono di confermare."),
    ("conferma", "Le chiedono di confermare."),
    ("ritirare", "Le chiedono di andare a ritirare un documento."),
    ("ritiro", "Le chiedono di andare a ritirare un documento."),
    ("pagare", "Le chiedono di pagare."),
    ("versare", "Le chiedono di pagare."),
    ("presentarsi", "Le chiedono di presentarsi di persona."),
    ("rispondere", "Le chiedono di rispondere."),
    ("compilare", "Le chiedono di compilare un modulo."),
    ("firmare", "Le chiedono di firmare."),
)


def azione_richiesta(testo: str) -> str | None:
    minuscolo = testo.lower()
    for parola, frase in AZIONI:
        if parola in minuscolo:
            return frase
    return None
