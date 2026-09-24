# Efficienza dei token

> Il criterio *Efficienza dei token* premia chi consuma poco. Il modo più efficace per consumare poco è **non chiamare**. Questo documento affianca **due numeri**: quello del default, misurato, e quello della seam, stimato e dichiarato come tale.

Le regole che producono questi numeri sono in [`../agents/runtime/routing.md`](../agents/runtime/routing.md). Qui c'è la loro **conseguenza quantificata sul corpus di demo**.

---

## 1. Il default: 0 token per email

Con `LLM_MODE=off` — cioè clonando il repository ed eseguendo senza configurare nulla — la seam non viene attraversata e i sei agenti girano sui propri motori deterministici.

| Email | Token consumati |
|---|---:|
| `em-01` dott.ssa Bianchi | **0** |
| `em-02` Comune di Torino | **0** |
| `em-03` finta Poste Italiane | **0** |
| `em-04` INPS | **0** |
| `em-05` Luca | **0** |
| `em-06` newsletter | **0** |
| **Casella completa** | **0** |

Non è un'affermazione di principio: `RisultatoPipeline.token_usati` è un campo del contratto, viene esposto da `POST /api/email/{id}/elabora` e **mostrato in interfaccia** nel pannello «Come ha ragionato». Il test `test_modalita_off_non_attraversa_la_seam` asserisce `token_usati == 0` sulla pipeline completa.

> Il costo marginale di una casella processata è **zero**, e il dato sanitario e previdenziale **non lascia il dispositivo**.

Questo trasforma il criterio da mancanza in **scelta architetturale**: il prodotto è completo e dimostrabile senza mai attraversare la seam.

---

## 2. Le quattro leve, in ordine di impatto

| # | Leva | Effetto concreto |
|---|---|---|
| 1 | **Non chiamare** | Una chiamata evitata costa zero token e zero latenza. È la leva che vale più di tutte le altre messe insieme |
| 2 | **Cache sullo stato esternalizzato** | Ri-aprire un'email già vista **non ri-esegue la pipeline**: `orchestrator.elabora` legge il checkpoint da `state/store.py` e ritorna. In demo è il caso normale, non un'ottimizzazione |
| 3 | **Output strutturati** | I prompt chiedono JSON conforme allo schema, non prosa. Meno token in uscita e nessun parsing fragile |
| 4 | **Model tiering** | Haiku dove basta classificare, Sonnet solo sul linguaggio. Dichiarato in `routing.md` §2, implementato in `llm/client.py` (`MODELLO_TRIAGE`, `MODELLO_LINGUA`) |

### Tre agenti su sei non hanno una seam, e non per pigrizia

| Agente | Perché non c'è un LLM |
|---|---|
| **02 · Sicurezza** | Il verdetto deve essere **spiegabile a una persona di 74 anni** e tradursi in un'azione. Una probabilità non è né l'una né l'altra cosa |
| **03 · Estrazione fatti** | È l'input di FactGuard. Fatti estratti da un modello che allucina renderebbero la verifica **circolare** |
| **05 · Verificatore** | È il controllo: non può essere la cosa controllata. Resterebbe vero **anche con budget illimitato** |

Un agente usa un LLM solo se il compito è **linguistico**, **aperto** e ★ **verificabile a valle**. La terza è la più spesso dimenticata: *non si mette un LLM dove il suo errore non è rilevabile.*

---

## 3. Le regole di non-chiamata, e cosa producono sul corpus

Sono valutate **prima** di attraversare la seam, e sono codice: `orchestrator._serve_semplificare` è la traduzione eseguibile di `routing.md` §3.

| Regola | Vale per | Motivo | Chi la fa scattare nel corpus |
|---|---|---|---|
| `LLM_MODE=off` | tutti | È il default. Il progetto è completo senza seam | tutte e 6 |
| Esiste un checkpoint per questa email | tutti | Ri-processarla costa **0** | tutte, dal secondo accesso in poi |
| Budget dell'email esaurito (`> 4000` token) | tutti | Si degrada a regole. La pipeline **non si interrompe mai** per budget | nessuna: la più cara del corpus si ferma a ~3.800 |
| Semaforo **rosso** | 4, 6 | Su phishing non si semplifica e non si compone: sarebbe spesa per un testo a cui l'utente non deve rispondere | `em-03` |
| Categoria `commerciale` | 4, 6 | Una pubblicità va messa in secondo piano, non tradotta, e non le si risponde | `em-06` |
| Categoria `persona_conosciuta` | 4 | Chi si conosce non scrive in burocratese | `em-05` |
| Corpo < 200 caratteri | 4 | Già breve e chiaro | nessuna nel corpus |
| Nessun fatto **e** corpo < 400 caratteri | 4 | Niente da preservare né da chiarire | nessuna nel corpus |

### L'effetto, contato

| Email | 01 Triage | 04 Semplificatore | 06 Compositore | Seam attraversate |
|---|:---:|:---:|:---:|:---:|
| `em-01` dott.ssa Bianchi | ● | ● | ● | 3 |
| `em-02` Comune di Torino | ● | ● | ● | 3 |
| `em-03` finta Poste | ● | — *rosso* | — *rosso* | 1 |
| `em-04` INPS | ● | ● | ● | 3 |
| `em-05` Luca | ● | — *in rubrica* | ● | 2 |
| `em-06` newsletter | ● | — *commerciale* | — *commerciale* | 1 |
| | 6 / 6 | **3 / 6** | 4 / 6 | **13** |

Tre letture dello stesso dato, tutte vere:

- **2 email su 6** (`em-03`, `em-06`) non attraversano **nessuna seam di linguaggio**: si fermano al triage, che è la seam sul modello piccolo.
- **Solo 3 email su 6** raggiungono il semplificatore, che è la seam più cara di tutte.
- Delle **18** possibili attraversate (6 email × 3 seam), le regole ne eliminano **5**, prima ancora di aver reso un prompt.

> `routing.md` §3 sintetizza questo effetto con «2 email su 6»: è la prima delle tre letture sopra. Il conteggio dettagliato è questa tabella, ottenuta eseguendo la pipeline sul corpus.

---

## 4. Il costo della seam in `replay` — **stima, non misura**

### ★ Il metodo, dichiarato prima dei numeri

> **Questi numeri sono una stima, calcolata sui file di prompt reali. Non sono misurati via API**, perché questo progetto **non ha mai chiamato un'API**: non c'è una chiave, non c'è una dipendenza `anthropic`, non c'è codice di rete in `app/`.

L'approssimazione usata è **`token ≈ caratteri / 4`**. È la regola empirica comunemente usata per il testo latino; sull'italiano, ricco di parole lunghe, tende a **sottostimare** leggermente. La dichiariamo così com'è: una stima dichiarata non è attaccabile, una stima presentata come misura sì.

Cosa è stato contato, esattamente:

| Voce | Come | Perché è onesta |
|---|---|---|
| **Input** | Il prompt **reso**: il file `.md` letto da `agents/runtime/prompts/`, con le variabili `{{…}}` sostituite dai valori veri dell'email del corpus | È letteralmente la stringa che il codice costruisce prima di calcolare l'hash della fixture. Non è un template idealizzato |
| **Output** | L'output dell'agente **serializzato in JSON**, nella forma imposta dal contratto Pydantic | La fixture contiene un `content` della stessa forma e dimensione: è la dimensione reale di un output conforme allo schema, non un numero scelto a mano |

### Dimensione dei prompt reali

| Prompt | File | Caratteri | ≈ token |
|---|---|---:|---:|
| 01 · Triage | `agents/runtime/prompts/triage.md` | 1 857 | ≈ 464 |
| 04 · Semplificatore | `agents/runtime/prompts/semplificatore.md` | 2 786 | ≈ 696 |
| 06 · Compositore | `agents/runtime/prompts/compositore.md` | 2 615 | ≈ 654 |

Sono i template a vuoto: il costo per email è superiore, perché `{{corpo}}` viene sostituito con l'email vera.

### Stima per email, sul corpus di demo

Valori in token, arrotondati, input + output. Una cella vuota è una regola di non-chiamata che ha funzionato.

| Email | 01 Triage | 04 Semplificatore | 06 Compositore | **Totale** |
|---|---:|---:|---:|---:|
| `em-01` dott.ssa Bianchi | ≈ 758 | ≈ 1 238 | ≈ 1 391 | **≈ 3 387** |
| `em-02` Comune di Torino | ≈ 905 | ≈ 1 415 | ≈ 1 465 | **≈ 3 785** |
| `em-03` finta Poste | ≈ 836 | — | — | **≈ 836** |
| `em-04` INPS | ≈ 857 | ≈ 1 448 | ≈ 971 | **≈ 3 276** |
| `em-05` Luca | ≈ 607 | — | ≈ 931 | **≈ 1 538** |
| `em-06` newsletter | ≈ 722 | — | — | **≈ 722** |
| **Casella completa (6 email)** | | | | **≈ 13 544** |
| **Media per email** | | | | **≈ 2 257** |

Tre osservazioni che i numeri rendono possibili:

1. **Il budget non è decorativo.** `BUDGET_TOKEN_EMAIL = 4000` e l'email più cara del corpus si ferma a **≈ 3 785**: il limite è tarato appena sopra il caso peggiore reale, non messo lì a caso. Superarlo degrada a regole senza fermare la pipeline.
2. **Le regole di non-chiamata valgono ≈ 5 200 token** sul corpus, stimati con lo stesso metodo sulle 5 attraversate eliminate. Senza di esse il totale sarebbe **≈ 18 700** invece di ≈ 13 500: **il 28% della spesa non viene sostenuto**, e non per compressione dei prompt ma per decisione di routing.
3. **Un retry moltiplica il semplificatore.** Se FactGuard rifiuta, il ciclo ricomincia con il `feedback_per_retry` in coda al prompt. Con `MAX_SIMPLIFY_RETRIES = 2` i tre tentativi del solo agente 04 su `em-02` valgono ≈ 4 200 token, cioè più del budget di una singola email: è **esattamente il caso per cui il budget esiste** (`BUDGET_TOKEN_EMAIL`, vedi [`../agents/runtime/orchestrator.md`](../agents/runtime/orchestrator.md) §limiti — al superamento si degrada a regole, la pipeline non si ferma).

### E la seconda volta?

**Zero.** Il checkpoint è già in `stato_pipeline`, `orchestrator.elabora` lo rilegge e ritorna senza eseguire un solo agente. Durante una demo, in cui la stessa email viene aperta, chiusa e riaperta, il costo reale è quello della **prima** apertura e basta.

---

## 5. I due numeri, affiancati

| | `off` *(default)* | `replay` |
|---|---:|---:|
| Casella completa, 6 email | **0 token — misurato** | **≈ 13 544 token — stimato** |
| Media per email | **0** | ≈ 2 257 |
| Seconda apertura della stessa email | 0 | 0 |
| Chiave API necessaria | nessuna | nessuna |
| Funziona a rete staccata | sì | sì |

Il confronto dimostra che la scelta deterministica è **quantificata, non subita**: sappiamo quanto costerebbe attraversare la seam, e abbiamo deciso di non attraversarla per default. È un'informazione molto più forte di un solo numero.

> Le fixture lette in `replay` sono **output di esempio scritti durante lo sviluppo**, conformi agli schema in `agents/runtime/contracts/`. **Non sono registrazioni di chiamate API.** Il campo `usage` che alimenta il contatore riporta la stima documentata in questo file, non un numero inventato. Vedi [`../README.md`](../README.md) e [`AUTONOMIA-E-LIMITI.md`](AUTONOMIA-E-LIMITI.md).
