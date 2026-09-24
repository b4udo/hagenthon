# Routing — model tiering e regole di non-chiamata

> Il criterio *Efficienza dei token* premia chi consuma poco. Il modo più efficace per consumare
> poco è **non chiamare**. Questo file dichiara, per ogni agente, quando l'LLM non va usato — che
> è una decisione di progetto, non un ripiego.

---

## 1. Principio: deterministico-first

Un agente usa un LLM **solo** se il compito ha tutte e tre queste proprietà:

1. **Linguistico** — richiede di riscrivere o generare italiano, non di classificare o confrontare.
2. **Aperto** — lo spazio degli input non è enumerabile con regole ragionevoli.
3. **Verificabile a valle** — esiste un controllo deterministico che può rifiutarne l'output.

La terza è la più importante e la più spesso dimenticata. **Non si mette un LLM dove il suo errore
non è rilevabile.** È il motivo per cui il verificatore non è e non sarà mai un modello: se
sbagliasse, nessuno se ne accorgerebbe, e l'intera promessa "semplificare senza tradire" crollerebbe.

---

## 2. Tabella di routing

| # | Agente | Modalità di default | Seam LLM | Modello dichiarato | Perché quel modello |
|---|---|---|---|---|---|
| 1 | Triage | regole | sì | **Haiku** | Classificazione a 5 classi su testo breve: il modello piccolo basta, quello grande è spreco |
| 2 | Sicurezza | regole | **no, mai** | — | Il verdetto deve essere **spiegabile** ("il dominio non è quello ufficiale"). Una probabilità non è un'azione |
| 3 | Estrazione fatti | regole | **no, mai** | — | È l'input di FactGuard. Un fatto estratto da un modello che allucina renderebbe la verifica circolare |
| 4 | Semplificatore | regole | sì | **Sonnet** | Riscrittura linguistica: è il caso d'uso legittimo. Ed è verificabile a valle da FactGuard |
| 5 | Verificatore | regole | **no, mai — per progetto** | — | Vedi §1, punto 3. È il controllo: non può essere la cosa controllata |
| 6 | Compositore | regole | sì | **Sonnet** | Genera italiano rivolto a un ente. Gli slot sono comunque riempiti solo con fatti verificati |

Tre agenti su sei **non hanno una seam LLM**, e non per pigrizia: per ciascuno la riga "perché"
sopra è la motivazione. È la risposta al criterio *Adeguatezza degli strumenti*: lo strumento
sbagliato nel posto sbagliato viene penalizzato quanto lo strumento mancante.

---

## 3. Quando NON chiamare, anche sulle seam attive

Regole valutate **prima** di attraversare la seam. Ognuna è un test in `app/tests/`.

| Regola | Agente | Motivo |
|---|---|---|
| `LLM_MODE=off` | tutti | Default. Il progetto è completo e dimostrabile senza mai attraversare la seam |
| Esiste un checkpoint in `state/data/<id>.json` | tutti | Ri-processare la stessa email costa **0**. La cache non è un'ottimizzazione: è il caso normale in demo |
| Budget dell'email esaurito (`> 4000` token) | tutti | Si degrada a regole. La pipeline non si interrompe mai per budget |
| Semaforo **rosso** | 4, 6 | Su phishing non si semplifica e non si compone. Non ha senso spendere token per un testo che l'utente non deve leggere né a cui deve rispondere |
| Categoria `commerciale` | 4 | Una newsletter va messa in secondo piano, non tradotta |
| Corpo < 200 caratteri | 4 | Il messaggio di Luca ("nonna, domenica vengo a pranzo") è già italiano semplice. Semplificarlo è spesa netta |
| Nessun fatto estratto e corpo < 400 caratteri | 4 | Non c'è niente da preservare né da chiarire |
| Il mittente è in rubrica | 4 | Una persona conosciuta non scrive in burocratese |

L'effetto combinato sul corpus di demo: in `replay`, **2 email su 6** attraversano davvero una
seam. Le altre 4 sono servite dalle regole a costo zero. Questo numero è in
`docs/TOKEN-EFFICIENCY.md` e non è un'ipotesi: è ciò che fanno le regole qui sopra.

---

## 4. Come è fatta la seam

Due modalità, dichiarate in `LLM_MODE`:

| Valore | Comportamento |
|---|---|
| `off` *(default)* | La seam non viene attraversata. L'agente usa il proprio motore a regole |
| `replay` | La seam viene attraversata **per intero** e la risposta è letta da `app/fixtures/llm/` |

**Non esiste una terza modalità.** `app/backend/llm/client.py` non contiene codice di rete: nessun
`import anthropic`, nessun client HTTP. Non è disattivato — non esiste. Il test
`app/tests/test_llm_modes.py` lo verifica leggendo staticamente i sorgenti di `app/`.

In `replay` il percorso eseguito è quello vero fino all'ultimo passo:

```
carica_prompt("semplificatore")        ← legge agents/runtime/prompts/semplificatore.md
   └─ sostituzione delle variabili
      └─ chiave = sha256(modello + prompt + input)
         └─ lettura di app/fixtures/llm/<chiave>.json
            └─ parsing del JSON di risposta
               └─ validazione Pydantic dell'output strutturato
                  └─ conteggio dei token dal campo `usage`
                     └─ FactGuard verifica un output che il codice non ha generato
```

Solo il trasporto è sostituito. Se domani si aggiungesse il trasporto HTTP, nient'altro
cambierebbe — ed è questo che rende la seam una scelta architetturale invece che una decorazione.

**Le fixture sono scritte a mano durante lo sviluppo, non sono registrazioni di chiamate API.**
Il progetto non ha mai usato una chiave. Vedi il README alla radice.

---

## 5. Efficienza — le quattro leve, in ordine di impatto

1. **Non chiamare** (§3). Una chiamata evitata costa zero token e zero latenza.
2. **Cache sullo stato esternalizzato.** Il costo marginale di una email già vista è zero.
3. **Output strutturati.** I prompt chiedono JSON conforme allo schema, non prosa. Meno token in
   uscita, e nessun parsing fragile.
4. **Model tiering** (§2). Haiku dove basta classificare, Sonnet solo sul linguaggio.

Misure in `docs/TOKEN-EFFICIENCY.md`.
