# 03 · Estrazione fatti

> Esiste perché FactGuard deve sapere **cosa** proteggere prima che il semplificatore possa
> tradirlo. Questo agente produce la lista dei fatti che la versione semplificata dovrà
> conservare intatti.

**Implementazione:** `app/backend/engines/fact_extract.py`, chiamato direttamente
dall'orchestratore (traccia `03-estrazione-fatti`). Non ha un modulo in
`app/backend/agents/`: essendo **interamente deterministico e senza seam**, un involucro che
si limitasse a inoltrare la chiamata sarebbe un file in più da tenere allineato e nient'altro.
**Modalità:** regole · **Seam LLM: nessuna, mai** (vedi [`routing.md`](routing.md) §2)

---

## Scopo

Estrarre dal testo **originale** le date, gli importi e gli orari che sono *informazione
operativa*, con la loro forma normalizzata.

## Perché qui non c'è un LLM

Questo è l'input del verificatore. Se i fatti li estraesse un modello, FactGuard verificherebbe
una semplificazione contro un elenco potenzialmente allucinato: la verifica diventerebbe
circolare e la garanzia "semplificare senza tradire" sarebbe vuota. **Il controllo deve poggiare
su qualcosa che non può inventare.**

## Input

Il corpo dell'email, testo grezzo.

## Output

`EsitoEstrazione` — schema in [`contracts/esito-estrazione.schema.json`](contracts/esito-estrazione.schema.json).

```json
{
  "fatti": [
    { "tipo": "data",    "testo_originale": "14 ottobre",  "valore_normalizzato": "2026-10-14", "ancora": "appuntamento", "posizione": 142 },
    { "tipo": "orario",  "testo_originale": "ore 9:30",    "valore_normalizzato": "09:30",      "ancora": "ore",         "posizione": 156 },
    { "tipo": "importo", "testo_originale": "€ 1.247,83",  "valore_normalizzato": "1247.83",    "ancora": "importo",     "posizione": 310 }
  ]
}
```

---

## ★ Scope rigido — il vincolo che tiene in piedi la demo

**Si estraggono solo tre tipi**, e ciascuno **solo se ancorato a una parola chiave vicina**
(entro 40 caratteri):

| Tipo | Ancore | Forme riconosciute |
|---|---|---|
| `data` | `entro`, `scadenza`, `appuntamento`, `visita`, `giorno`, `data`, `il` | `14/10/2026` · `14-10-2026` · `14 ottobre 2026` · `14 ottobre` |
| `importo` | `importo`, `euro`, `€`, `totale`, `pagare`, `versare`, `pensione` | `€ 1.247,83` · `1.247,83 euro` · `1247,83 €` |
| `orario` | `ore`, `alle`, `orario` | `9:30` · `09:30` · `ore 9.30` |

**Non si estrae mai:**

| Escluso | Perché |
|---|---|
| Numeri di protocollo | *"Prot. 2026/14785"* contiene una cifra che somiglia a un anno |
| IBAN, codici fiscali | Lunghi, pieni di cifre, mai identici tra originale e semplificato |
| ★ Civici e CAP | **"Via Roma 15" letto come fatto → rifiuto ingiustificato → sul palco appare il fallback brutto.** È il falso positivo più probabile, ed è esplicitamente testato |
| Numeri di telefono | Stessa ragione |
| Percentuali, numeri di lista | *"1."*, *"2."* di un elenco puntato |

Allargare questo scope è la tentazione più forte e l'errore più costoso. La regola operativa:
**meglio proteggere tre fatti in modo affidabile che dieci in modo rumoroso.** Un rifiuto
ingiustificato distrugge la fiducia nel verificatore molto più di quanto un fatto non protetto
la costruisca.

## Passi

1. Scorri il testo con le espressioni regolari dei tre tipi.
2. Per ogni candidato, cerca un'ancora nei 40 caratteri precedenti. Nessuna ancora → **scarta**.
3. Normalizza (`app/backend/engines/normalize.py`):
   date → `AAAA-MM-GG`, importi → decimale con punto, orari → `HH:MM` a due cifre.
4. Per le date senza anno, usa l'anno di `clock.py`.
5. Deduplica per `(tipo, valore_normalizzato)`.

## Vincoli

- **`dateparser` è vietato.** Le date italiane si gestiscono a mano in `normalize.py`: è una
  dipendenza pesante che introdurrebbe comportamenti non deterministici proprio dove serve il
  contrario.
- L'anno mancante si risolve con `clock.py`, mai con `date.today()`: altrimenti le scadenze del
  corpus scadono e i test diventano non deterministici.
- Zero fatti è un esito **legittimo**, non un errore.

## Fallback

Lista vuota. Con zero fatti, FactGuard non ha niente da verificare e la semplificazione passa:
è corretto, perché non c'era nulla da tradire.
