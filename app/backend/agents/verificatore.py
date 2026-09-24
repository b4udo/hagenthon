"""05 · Verificatore — FactGuard.

Specifica: agents/runtime/05-verificatore.md

Il motore propone, il verificatore controlla, la persona decide.

Questo modulo non chiama e non chiamera' mai un modello linguistico. Un
verificatore che allucina e' peggio di nessun verificatore, perche' da' una
garanzia falsa. Il controllo non puo' appartenere alla stessa classe di
strumento della cosa controllata.
"""

from __future__ import annotations

from ..contracts import (
    EsitoVerifica,
    Fatto,
    ProblemaVerifica,
    TipoProblema,
)
from ..engines import fact_extract

# Solo importi e date complete. Estendere agli orari o ai numeri nudi farebbe
# scattare "inventato" sui marcatori di lista ("1.", "2.") e sui derivati
# legittimi ("fra 5 giorni").
TIPI_CON_INVENZIONE = ("importo", "data")

_ETICHETTA = {"data": "la data", "importo": "l'importo", "orario": "l'orario"}


def verifica(
    fatti_originale: list[Fatto],
    testo_semplificato: str,
    anno_default: int,
) -> EsitoVerifica:
    """Confronta i fatti dell'originale con quelli del testo semplificato.

    Il confronto avviene sui **valori normalizzati**: "14/10/2026" e
    "14 ottobre 2026" sono lo stesso fatto. Confrontare le stringhe grezze
    rifiuterebbe ogni riformulazione legittima, cioe' esattamente il lavoro per
    cui il semplificatore esiste.
    """
    presenti = fact_extract.estrai_valori_grezzi(testo_semplificato, anno_default)
    problemi: list[ProblemaVerifica] = []

    attesi_per_tipo: dict[str, set[str]] = {}
    for fatto in fatti_originale:
        attesi_per_tipo.setdefault(fatto.tipo.value, set()).add(fatto.valore_normalizzato)

    # Valori "orfani": compaiono nel semplificato ma non corrispondono ad alcun
    # fatto dell'originale. Sono gli unici candidati a spiegare un'alterazione;
    # quelli che restano alla fine sono invenzioni.
    orfani: dict[str, list[tuple[str, str]]] = {
        tipo: [(g, v) for g, v in valori if v not in attesi_per_tipo.get(tipo, set())]
        for tipo, valori in presenti.items()
    }

    # ── fatti dell'originale: presenti, alterati o spariti ──
    for fatto in fatti_originale:
        tipo = fatto.tipo.value
        if fatto.valore_normalizzato in {v for _, v in presenti.get(tipo, [])}:
            continue

        candidati = orfani.get(tipo, [])
        if candidati:
            # Un orfano spiega una sola alterazione: si consuma.
            grezzo_trovato, _ = candidati.pop(0)
            problemi.append(
                ProblemaVerifica(
                    tipo=TipoProblema.ALTERATO,
                    fatto=fatto,
                    trovato=grezzo_trovato,
                    spiegazione=(
                        f"{_ETICHETTA[tipo].capitalize()} non corrisponde "
                        f"all'originale: {fatto.testo_originale} e' diventato {grezzo_trovato}."
                    ),
                )
            )
        else:
            problemi.append(
                ProblemaVerifica(
                    tipo=TipoProblema.MANCANTE,
                    fatto=fatto,
                    trovato=None,
                    spiegazione=(
                        f"{_ETICHETTA[tipo].capitalize()} "
                        f"{fatto.testo_originale} non compare nella versione semplificata."
                    ),
                )
            )

    # ── cio' che resta orfano e' comparso dal nulla ──
    for tipo in TIPI_CON_INVENZIONE:
        for grezzo, _ in orfani.get(tipo, []):
            problemi.append(
                ProblemaVerifica(
                    tipo=TipoProblema.INVENTATO,
                    fatto=None,
                    trovato=grezzo,
                    spiegazione=(
                        f"Nella versione semplificata compare {grezzo}, "
                        f"che non e' presente nell'originale."
                    ),
                )
            )

    passa = not problemi
    return EsitoVerifica(
        passa=passa,
        problemi=problemi,
        feedback_per_retry=None if passa else _feedback(problemi),
    )


def _feedback(problemi: list[ProblemaVerifica]) -> str:
    """Istruzioni per il semplificatore al tentativo successivo.

    Unico testo del sistema che non e' rivolto a Maria: qui il destinatario e'
    il semplificatore, quindi e' imperativo e specifico invece che gentile.
    """
    righe = ["La versione semplificata non conserva i fatti dell'originale."]
    for p in problemi:
        if p.tipo is TipoProblema.MANCANTE and p.fatto:
            righe.append(f"- Manca {p.fatto.testo_originale}: riportalo esattamente.")
        elif p.tipo is TipoProblema.ALTERATO and p.fatto:
            righe.append(
                f"- {p.fatto.testo_originale} e' stato riportato come {p.trovato}: "
                f"usa il valore esatto dell'originale."
            )
        elif p.tipo is TipoProblema.INVENTATO:
            righe.append(f"- {p.trovato} non esiste nell'originale: eliminalo.")
    righe.append("Riscrivi conservando ogni data, importo e orario alla lettera.")
    return "\n".join(righe)


def avvelena(testo: str) -> str:
    """Corrompe l'importo dell'INPS: 1.247,83 -> 1.247.

    Serve alla demo. Col semplificatore deterministico FactGuard non fallirebbe
    mai davanti alla giuria, e un controllo che non si vede scattare viene letto
    come decorazione.

    E' dichiarato qui, in agents/runtime/05-verificatore.md e nel README; non e'
    mai attivo per default e si raggiunge solo con ?avvelena=true.
    """
    return testo.replace("1.247,83", "1.247").replace("1247,83", "1247")
