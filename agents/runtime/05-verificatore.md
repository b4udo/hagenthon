# 05 · Verificatore — FactGuard

> Esiste perché "semplificare" e "tradire" sono separati da una riga sottile, e senza un
> controllo quella riga la decide chi ha scritto il semplificatore. Se il sistema dice a Maria
> *"deve pagare 1.247 euro"* quando l'INPS ha scritto *"1.247,83"*, il danno non è teorico.

**Implementazione:** `app/backend/agents/verificatore.py`
**Modalità: regole. Seam LLM: nessuna, mai — per progetto.**

---

## Il principio

> **Il motore propone, il verificatore controlla, la persona decide.**

Il verificatore è **il pezzo tecnico centrale del prodotto** e la risposta diretta al vincolo
*"semplificare senza tradire"*. È anche il motivo per cui la seam LLM sul semplificatore è
difendibile: c'è qualcosa di deterministico che può rifiutarne l'output.

## Perché non sarà mai un LLM

Un verificatore che allucina è peggio di nessun verificatore: dà una garanzia falsa. Il controllo
non può essere fatto dalla stessa classe di strumento che produce ciò che deve controllare —
sarebbe come far rileggere il compito allo stesso studente. Questo non è un compromesso dovuto
al tempo: **è una proprietà voluta dell'architettura** e resterebbe vera con budget illimitato.

## Input

- I `Fatto` estratti dall'agente 03 **dall'originale**
- Il `testo_semplificato` prodotto dall'agente 04
- Il numero del tentativo corrente

## Output

`EsitoVerifica` — schema in [`contracts/esito-verifica.schema.json`](contracts/esito-verifica.schema.json).

```json
{
  "passa": false,
  "problemi": [
    {
      "tipo": "alterato",
      "fatto": { "tipo": "importo", "testo_originale": "€ 1.247,83", "valore_normalizzato": "1247.83" },
      "trovato": "€ 1.247",
      "spiegazione": "L'importo non corrisponde all'originale."
    }
  ],
  "feedback_per_retry": "L'importo 1.247,83 è stato riportato come 1.247. Riscrivi conservando l'importo esatto."
}
```

---

## Le tre classi di problema

| Tipo | Condizione | Esempio |
|---|---|---|
| `mancante` | Un fatto dell'originale non compare in nessuna forma nel semplificato | La data `14 ottobre` sparisce |
| `alterato` | Compare un valore dello stesso tipo, vicino ma diverso | `1.247,83` → `1.247` · `ore 9:30` → `ore 9:00` |
| `inventato` | Nel semplificato c'è un importo o una data completa che non esiste nell'originale | Il modello aggiunge "€ 50 di mora" |

**`inventato` si applica solo a importi e date complete.** Estenderlo agli orari o ai numeri
nudi lo farebbe scattare su marcatori di lista e su derivati legittimi ("fra 5 giorni"): falsi
positivi garantiti.

## ★ Il confronto avviene sui valori normalizzati

È la regola che rende il verificatore utile invece che fragile.

| Originale | Semplificato | Esito | Perché |
|---|---|---|---|
| `14/10/2026` | `14 ottobre 2026` | ✅ **passa** | Stesso `valore_normalizzato`: `2026-10-14` |
| `ore 9:30` | `alle 09:30` | ✅ **passa** | Entrambi `09:30` |
| `€ 1.247,83` | `1.247,83 euro` | ✅ **passa** | Entrambi `1247.83` |
| `€ 1.247,83` | `€ 1.247` | ❌ **alterato** | `1247.00 ≠ 1247.83` |
| `14 ottobre` | *(assente)* | ❌ **mancante** | — |

Un verificatore che confrontasse le stringhe grezze rifiuterebbe ogni riformattazione legittima
e sarebbe inutilizzabile: il semplificatore esiste **proprio** per riformattare.

## Vincoli

- Verifica **solo** i tre tipi dell'agente 03. Non inventa controlli propri.
- **Non corregge.** Rifiuta e spiega. La correzione è compito del semplificatore, al tentativo
  successivo.
- `feedback_per_retry` è rivolto al semplificatore, non a Maria: è l'unico testo del sistema che
  non deve essere in italiano semplice.
- Dopo `MAX_SIMPLIFY_RETRIES = 2` fallimenti, l'orchestratore smette. Non esiste un terzo
  tentativo.

## ★ Il limite da dichiarare, non nascondere

> **FactGuard verifica la *presenza* dei fatti, non il loro *ruolo*.**

Non distingue *"importo dovuto"* da *"importo già versato"*: vede che `1247.83` c'è in entrambi
i testi e passa. Un semplificatore che invertisse il senso della frase conservando il numero
supererebbe il controllo.

È il limite intrinseco di un verificatore sintattico, ed è scritto in `docs/AUTONOMIA-E-LIMITI.md`
e detto in presentazione. **È esattamente il punto in cui serve la revisione umana** — ed è il
motivo per cui l'originale resta sempre a un tocco di distanza.

## Fallback

Se il verificatore stesso solleva un'eccezione: `passa = False`. Un controllo che non è riuscito
non è un controllo superato. L'interfaccia mostra l'originale.

---

## ★ La modalità "email avvelenata" — dimostrare invece di affermare

Col semplificatore deterministico, FactGuard **non fallirebbe mai in demo**: le regole ricopiano
i fatti verbatim. Una giuria che non lo vede scattare lo classifica come decorazione.

L'endpoint `POST /api/email/{id}/elabora?avvelena=true` corrompe deliberatamente l'output del
semplificatore **prima** della verifica (`€ 1.247,83` → `€ 1.247`), e il rifiuto avviene dal vivo:

```
  ⚠  Verifica fallita: l'importo non corrisponde all'originale.
     Originale: € 1.247,83   ·   Versione semplificata: € 1.247
     → Semplificazione rifiutata. Mostro il testo originale.
```

La corruzione è **esplicita, isolata e visibile** in `orchestrator.py`: non altera il
semplificatore, non è attiva per default, e il parametro compare nell'URL. Un espediente da
demo nascosto nel codice di produzione sarebbe disonesto; questo è dichiarato in questo file,
nel README e in presentazione.

In `LLM_MODE=replay` lo stesso rifiuto avviene **senza il flag**: una delle fixture del
semplificatore è volutamente imperfetta. Vedi [`routing.md`](routing.md) §4.
