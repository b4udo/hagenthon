# 02 · Sicurezza

> Esiste perché la truffa che arriva nella casella di Maria e la convocazione vera dell'INPS
> dicono le stesse due parole: *soldi* e *urgente*. Distinguerle è il valore più alto che questo
> prodotto può produrre, e sbagliare ha un costo reale.

**Implementazione:** `app/backend/agents/sicurezza.py` + `app/backend/engines/phishing_rules.py`
**Modalità:** regole · **Seam LLM: nessuna, mai** (vedi [`routing.md`](routing.md) §2)

---

## Scopo

Emettere un **semaforo** con un messaggio comprensibile e — obbligatoriamente — **un'azione che
Maria può eseguire**.

> Un semaforo senza pulsante è un checker travestito da assistente.
> **Nessun verdetto senza azione.**

## Perché qui non c'è un LLM

Il verdetto deve essere **spiegabile a una persona di 74 anni**: *"il nome dice Poste Italiane
ma l'indirizzo non è quello ufficiale"*. Una probabilità restituita da un modello non è
spiegabile, non è ripetibile, e soprattutto non si traduce in un'azione. Le regole sì: ogni
regola che scatta produce una riga in `segnali`, e ogni riga è una frase in italiano.

## Input

`Email` + `EsitoTriage`.

## Output

`EsitoSicurezza` — schema in [`contracts/esito-sicurezza.schema.json`](contracts/esito-sicurezza.schema.json).

```json
{
  "semaforo": "rosso",
  "messaggio": "Non rispondere a questa email. Sembra una truffa.",
  "segnali": [
    "Il nome dice «Poste Italiane» ma l'indirizzo non è di poste.it",
    "Chiede di fare qualcosa entro 24 ore per metterle fretta",
    "C'è un link che porta a un sito diverso da quello che mostra"
  ],
  "azione": {
    "tipo": "telefono",
    "etichetta": "Chiama Poste Italiane al numero ufficiale",
    "valore": "803 160"
  }
}
```

## Le regole

| Regola | Peso | Segnale mostrato a Maria |
|---|---|---|
| Il nome visualizzato cita un ente noto ma il dominio non è quello ufficiale | **rosso** | "Il nome dice «X» ma l'indirizzo non è di x.it" |
| Il testo del link e la destinazione reale non coincidono | **rosso** | "C'è un link che porta a un sito diverso da quello che mostra" |
| Lessico d'urgenza (`entro 24 ore`, `conto bloccato`, `sospensione immediata`, `verifica subito`) | +1 | "Chiede di fare qualcosa in fretta per metterle fretta" |
| Richiesta di credenziali, PIN, numero di carta | **rosso** | "Chiede dati che nessun ente chiede per email" |
| Mittente in rubrica | **verde** | — |
| Dominio istituzionale verificato **e** nessun segnale negativo | **verde** | — |
| Tutto il resto | **giallo** | "Non conosco questo mittente" |

Due segnali `+1` o più, senza un dominio verificato → **rosso**.

## Azione per ogni verdetto — nessuna eccezione

| Semaforo | Messaggio | Azione |
|---|---|---|
| 🔴 **rosso** | "Non rispondere a questa email." | `telefono` — il numero verde **ufficiale** dell'ente impersonato, preso da una tabella statica nel codice, mai dall'email |
| 🟡 **giallo** | "Non sono sicuro. Chiedi a una persona di fiducia." | `inoltra` — "Manda a Luca" |
| 🟢 **verde** | "Puoi rispondere tranquillamente." | `rispondi` — porta alla risposta guidata |

## Vincoli

- ★ **Il numero di telefono dell'azione non viene MAI estratto dall'email.** Su un'email di
  phishing, il numero nel corpo è il numero del truffatore. Viene da una tabella statica di
  recapiti istituzionali in `phishing_rules.py`. Questo è il vincolo più importante del file.
- ★ **Uno sconosciuto innocuo è giallo, mai verde.** Il verde è riservato a chi è in rubrica o a
  un dominio istituzionale verificato. La soglia è prudenziale per costruzione: il costo di un
  falso verde (Maria si fida di una truffa) è incomparabilmente più alto del costo di un falso
  giallo (Maria chiede al nipote).
- Il sistema non dice mai *"è sicura"*. Dice *"puoi rispondere"*: è un'affermazione sull'azione,
  non una garanzia sul mittente.
- Su semaforo rosso l'orchestratore **non compone bozze di risposta**. Vedi
  [`orchestrator.md`](orchestrator.md).

## Fallback

Semaforo **giallo**, messaggio *"Non sono riuscito a controllare questa email. Chiedi a una
persona di fiducia."*, azione `inoltra`. Il fallback non è mai verde: un controllo che non è
riuscito non è un controllo superato.
