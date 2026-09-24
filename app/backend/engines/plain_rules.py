"""Burocratese italiano -> italiano comune.

## La lezione che ha dato forma a questo file

La prima versione sostituiva parola per parola. Su un'email vera del Comune
produceva «all'domanda», «dallei richiesto», «Le chiediamo di pertanto lei a
voler ritirare». Italiano rotto: **peggio dell'originale**, perche' l'originale
almeno era corretto.

La causa e' strutturale, non un bug da aggiustare: sostituire un sostantivo ne
cambia il genere e manda in pezzi articoli e preposizioni intorno. Un motore a
regole non sa concordare.

Quindi qui si lavora a due livelli, entrambi sicuri:

1. **Frasi intere** di pura formula: si cancellano. Nessuna concordanza da
   rispettare, perche' non resta niente.
2. **Locuzioni autonome**: si sostituiscono per intero, articolo compreso, cosi'
   la concordanza e' scritta nella sostituzione stessa.

Cio' che non rientra in questi due casi **resta com'e'**. Il valore vero lo
porta il riassunto Chi / Cosa / Entro quando, non la riscrittura integrale: e'
un limite dichiarato, ed e' esattamente cio' per cui esiste la seam LLM.

Regola sopra tutte: **non si tocca mai un numero, una data o un importo.**
"""

from __future__ import annotations

import re

# ── 1 · frasi intere da eliminare ──
# Se una frase contiene uno di questi marcatori, non aggiunge nulla per Maria.
FRASI_DI_PURA_FORMULA = (
    "non necessita di sottoscrizione autografa",
    "trasmessa in via telematica",
    "firmato digitalmente",
    "ai sensi del regolamento ue",
    "informativa sul trattamento dei dati",
    "il presente messaggio e' riservato",
    "il presente messaggio è riservato",
)

# ── 2 · locuzioni autonome, sostituite per intero ──
# Ordine: dalla piu' lunga alla piu' corta, cosi' la specifica vince sulla
# generica. Ogni sostituzione include l'articolo quando serve alla concordanza.
LOCUZIONI: tuple[tuple[str, str], ...] = (
    # formule di richiesta
    (r"si\s+invita\s+(?:pertanto\s+)?la\s+S\.?\s*V\.?\s+a\s+voler\s+provvedere\s+al\s+ritiro\s+del",
     "le chiediamo di ritirare il"),
    (r"si\s+invita\s+(?:pertanto\s+)?la\s+S\.?\s*V\.?\s+a\s+voler\s+provvedere\s+al\s+ritiro",
     "le chiediamo di ritirare"),
    # La citazione normativa per intero, fino al numero di legge: lasciarne
    # fuori la coda produce un mozzicone tipo "le comunichiamo che, n. 445,".
    # Il punto di "artt." impedisce di usare [^.]*: si limita la lunghezza.
    (r"(?:ai\s+sensi|a\s+norma)\b.{0,140}?\bn\.\s*\d+\s*,\s*", ""),
    (r"(?:ai\s+sensi|a\s+norma)\s+(?:e\s+per\s+gli\s+effetti\s+)?(?:del|dell'|della|degli|dei|di)\b[^,.]*[,]?\s*", ""),
    (r"si\s+invita\s+(?:pertanto\s+)?la\s+S\.?\s*V\.?\s+a\s+voler\s+",
     "le chiediamo di "),
    (r"si\s+invita\s+(?:pertanto\s+)?la\s+S\.?\s*V\.?\s+a\s+", "le chiediamo di "),
    (r"la\s+S\.?\s*V\.?\s+e'\s+invitata\s+a\s+", "le chiediamo di "),
    (r"si\s+prega\s+di\s+voler\s+", "le chiediamo di "),
    (r"si\s+prega\s+di\s+", "le chiediamo di "),
    (r"la\s+preghiamo\s+cortesemente\s+di\s+volerci\s+", "le chiediamo di "),
    (r"la\s+preghiamo\s+cortesemente\s+di\s+voler\s+", "le chiediamo di "),
    (r"la\s+preghiamo\s+di\s+voler\s+", "le chiediamo di "),
    (r"la\s+preghiamo\s+di\s+", "le chiediamo di "),
    (r"la\s+invitiamo\s+a\s+voler\s+", "le chiediamo di "),
    (r"in\s+mancanza\s+di\s+riscontro\s+entro\s+il\s+termine\s+indicato",
     "se non risponde entro questa data"),
    (r"in\s+mancanza\s+di\s+riscontro", "se non risponde"),
    (r"l'orario\s+riservato\s+potr[aà]\s+essere\s+assegnato\s+ad\s+altro\s+paziente",
     "il suo posto potrà essere dato a un altro paziente"),
    (r"in\s+merito\s+alla?\s+", "per "),
    (r"gi[aà]\s+concordat[ao]", "che avevate fissato"),
    (r"le\s+ricordiamo\s+di\s+portare\s+con\s+s[eé]", "porti con sé"),
    (r"e'\s+fatto\s+obbligo\s+di\s+", "deve "),
    (r"è\s+fatto\s+obbligo\s+di\s+", "deve "),
    (r"provvedere\s+al\s+ritiro\s+del", "ritirare il"),
    (r"provvedere\s+al\s+ritiro", "ritirare"),

    # riferimenti e protocolli
    (r"con\s+riferimento\s+all'istanza\s+acquisita\s+agli\s+atti\s+di\s+questo\s+ufficio",
     "riguardo alla domanda che ci ha presentato"),
    (r"con\s+riferimento\s+all'istanza", "riguardo alla sua domanda"),
    (r"acquisita\s+agli\s+atti\s+di\s+questo\s+ufficio", "che abbiamo ricevuto"),
    (r"e\s+protocollata\s+al\s+n\.\s*[\w/]+", ""),
    (r"ai\s+sensi\s+e\s+per\s+gli\s+effetti\s+degli?\s+artt?\.[^,]*,", ""),
    (r"ai\s+sensi\s+dell['a-z]*\s+artt?\.[^,]*,", ""),
    (r"nonch[eé]\s+della\s+vigente\s+disciplina\s+regolamentare\s+comunale[^,.]*", ""),

    # esiti e disponibilita'
    (r"e'\s+stato\s+predisposto\s+ed\s+e'\s+da\s+ritenersi\s+disponibile\s+per\s+il\s+ritiro",
     "è pronto"),
    (r"è\s+stato\s+predisposto\s+ed\s+è\s+da\s+ritenersi\s+disponibile\s+per\s+il\s+ritiro",
     "è pronto"),
    (r"(?:e'|è)\s+da\s+ritenersi\s+disponibile", "è disponibile"),
    (r"dalla\s+S\.?\s*V\.?\s+richiest[oa]", "che ha chiesto"),
    (r"da\s+lei\s+richiest[oa]", "che ha chiesto"),

    # termini e scadenze
    (r"entro\s+e\s+non\s+oltre\s+il\s+giorno", "entro il"),
    (r"entro\s+e\s+non\s+oltre", "entro"),
    (r"decorso\s+inutilmente\s+il\s+termine\s+sopra\s+indicato", "dopo questa data"),
    (r"decorso\s+il\s+termine", "dopo questa data"),
    (r"termine\s+perentorio", "scadenza"),
    (r"sar[aà]\s+archiviata\s+d'ufficio\s+senza\s+ulteriore\s+comunicazione",
     "la pratica sarà chiusa e dovrà rifare la domanda"),

    # documenti e presenza
    (r"previa\s+esibizione\s+di\s+documento\s+di\s+riconoscimento\s+in\s+corso\s+di\s+validit[aà]",
     "portando un documento valido"),
    (r"previa\s+esibizione\s+di", "mostrando"),
    (r"documento\s+di\s+riconoscimento\s+in\s+corso\s+di\s+validit[aà]", "un documento valido"),
    (r"in\s+corso\s+di\s+validit[aà]", "valido"),
    (r"recarsi\s+presso", "andare"),
    (r"orari\s+di\s+apertura\s+al\s+pubblico", "orari"),
    (r"negli\s+orari\s+di\s+seguito\s+indicati", "in questi orari"),
    (r"di\s+seguito\s+indicati", ""),

    # formule di apertura / chiusura
    (r"con\s+la\s+presente\s+si\s+comunica\s+che", "le scriviamo per dirle che"),
    (r"si\s+comunica\s+che", "le comunichiamo che"),
    (r"si\s+rende\s+noto\s+che", "le facciamo sapere che"),
    (r"si\s+rammenta\s+che", "le ricordiamo che"),
    (r"la\s+informiamo\s+che", "le facciamo sapere che"),
    (r"resta\s+salva\s+la\s+facolt[aà]\s+dell'interessata\s+di\s+presentare\s+nuova\s+istanza",
     "può sempre presentare una nuova domanda"),
    (r"fatta\s+salva\s+la\s+facolt[aà]\s+dell'interessata\s+di\s+presentare\s+nuova\s+istanza",
     "potrà presentare una nuova domanda"),

    # deleghe
    (r"[eè]'?\s*ammessa\s+la\s+delega\s+a\s+soggetto\s+terzo",
     "può mandare un'altra persona al posto suo"),
    (r"corredata\s+di\s+copia\s+fotostatica\s+del\s+documento\s+di\s+identit[aà]\s+del\s+delegante",
     "con la fotocopia del suo documento"),
    (r"redatta\s+in\s+forma\s+scritta", "scritta su un foglio"),

    # sostantivi con articolo, cosi' il genere resta coerente
    (r"\ball'istanza\b", "alla domanda"),
    (r"\bdell'istanza\b", "della domanda"),
    (r"\bl'istanza\b", "la domanda"),
    (r"\bnuova\s+istanza\b", "nuova domanda"),
    (r"\bistanza\b", "domanda"),
    (r"\bla\s+presente\s+comunicazione\b", "questa lettera"),
    (r"\bcodesto\s+ufficio\b", "il nostro ufficio"),
    (r"\bquesto\s+ufficio\b", "il nostro ufficio"),
    (r"\bsportello\s+n\.\s*(\d+)", r"sportello numero \1"),
    (r"\bil\s+cedolino\b", "il foglio della pensione"),
    (r"\bcedolino\b", "foglio della pensione"),
)

MAX_PAROLE_FRASE = 28

_RE_SPAZI = re.compile(r"[ \t]{2,}")
_RE_RIGHE = re.compile(r"\n{3,}")


def semplifica_testo(testo: str) -> str:
    righe = [_semplifica_riga(r) for r in testo.split("\n")]
    return _ripulisci("\n".join(righe))


def _semplifica_riga(riga: str) -> str:
    if not riga.strip():
        return ""

    # Le locuzioni si applicano alla riga intera PRIMA di dividerla in frasi.
    # Dividere per prima cosa spezzerebbe "la S.V. a voler provvedere" sul
    # punto di "S.V.", e mezza locuzione non corrisponde piu' a nulla.
    for schema, sostituzione in LOCUZIONI:
        riga = re.sub(schema, sostituzione, riga, flags=re.IGNORECASE)

    tenute = []
    for frase in re.split(r"(?<=[.!?])\s+", riga):
        if any(m in frase.lower() for m in FRASI_DI_PURA_FORMULA):
            continue  # pura formula: non aggiunge nulla
        frase = _spezza_se_lunga(frase).strip()
        if frase:
            tenute.append(frase)

    return " ".join(tenute)


def _spezza_se_lunga(frase: str) -> str:
    """Spezza i periodi lunghi. E' la leva piu' forte sulla leggibilita'.

    L'indice Gulpease premia le frasi corte molto piu' delle parole corte: un
    periodo burocratico di 60 parole resta illeggibile anche dopo aver
    sostituito ogni termine difficile. Si taglia solo su virgole e punti e
    virgola, mai dentro un'informazione.
    """
    if len(frase.split()) <= MAX_PAROLE_FRASE:
        return frase

    # Il punto e virgola e' un marcatore di burocratese: diventa un punto.
    frase = re.sub(r"\s*;\s*", ". ", frase)

    frase = re.sub(
        r",\s+(?:e\s+)?(inoltre|nonch[eé]|pertanto|quindi|altres[iì])\s+",
        ". ",
        frase,
        flags=re.IGNORECASE,
    )

    pezzi = []
    for parte in re.split(r"(?<=\.)\s+", frase):
        pezzi.extend(_taglia_in_sicurezza(parte))
    return " ".join(pezzi)


# Parole con cui puo' legittimamente iniziare una frase nuova. Tagliare prima
# di una di queste non spezza mai un'informazione a meta'.
INIZI_DI_CLAUSOLA = (
    "in", "per", "con", "dal", "dalla", "se", "quando", "il", "la", "le",
    "lo", "gli", "e", "oppure", "entro", "presso", "secondo", "nel", "nella",
    "questo", "questa", "tale", "dopo", "prima", "inoltre", "altrimenti",
)

_RE_VIRGOLA_SICURA = re.compile(r"(?<![0-9]),\s+(?=([a-zà-ù]+))")


def _taglia_in_sicurezza(parte: str, profondita: int = 0) -> list[str]:
    """Spezza alla virgola piu' centrale, ma solo dove e' sicuro.

    Due guardie, entrambe nate da un errore vero: una versione precedente
    sceglieva la virgola piu' vicina alla meta' senza guardare cosa c'era
    intorno, e produceva «Via dell'Esempio 12. 10122 Torino» — un indirizzo
    tagliato in due. Quindi: mai dopo una cifra, mai prima di una cifra, e
    solo se la parola seguente puo' davvero aprire una frase.

    Se nessun punto e' sicuro, la frase resta lunga: e' un esito accettabile,
    spezzare un'informazione non lo e'.
    """
    if len(parte.split()) <= MAX_PAROLE_FRASE or profondita >= 3:
        return [parte]

    candidati = [
        m.start()
        for m in _RE_VIRGOLA_SICURA.finditer(parte)
        if m.group(1).lower() in INIZI_DI_CLAUSOLA
    ]
    if not candidati:
        return [parte]

    meta = len(parte) // 2
    taglio = min(candidati, key=lambda p: abs(p - meta))
    sinistra = parte[:taglio].rstrip(" ,")
    destra = parte[taglio + 1 :].strip()

    return _taglia_in_sicurezza(sinistra + ".", profondita + 1) + _taglia_in_sicurezza(
        destra, profondita + 1
    )


def _ripulisci(testo: str) -> str:
    testo = _RE_SPAZI.sub(" ", testo)
    testo = re.sub(r"\s+([,.;:!?])", r"\1", testo)
    testo = re.sub(r"([,;:])\s*([,;:.])", r"\2", testo)
    testo = re.sub(r"\.{2,}", ".", testo)
    testo = re.sub(r"(?m)^[ \t]*[,.;:]\s*", "", testo)
    testo = re.sub(r",\s*\.", ".", testo)
    # Residuo tipico dopo aver tolto un inciso: "le comunichiamo che, il ...".
    testo = re.sub(r"\bche,\s+", "che ", testo)
    testo = _RE_RIGHE.sub("\n\n", testo)

    # Dopo aver spezzato un periodo, la nuova frase deve iniziare maiuscola.
    # La cifra dopo "n. 445" non viene toccata: la regola chiede una lettera.
    testo = re.sub(
        r"([.!?]\s+)([a-zà-ù])", lambda m: m.group(1) + m.group(2).upper(), testo
    )

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
