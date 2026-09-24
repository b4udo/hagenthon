**Tema 01 · Accessibilità Digitale**

# Posta Chiara

> Un client di posta che si mette **accanto** a chi si ferma davanti al riquadro bianco vuoto: legge l'email, dice se è una truffa, la traduce dal burocratese e prepara la risposta da scegliere con un pulsante.

L'utente è **Maria Rossi, 74 anni** ([`docs/PERSONA.md`](docs/PERSONA.md)). Il punto in cui oggi si ferma è documentato, misurato e risolto: [`docs/PERCORSO-ASSISTITO.md`](docs/PERCORSO-ASSISTITO.md).

---

## Avvio rapido

```powershell
py -V:3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.backend.main:app --port 8123
```

Poi si apre **<http://localhost:8123>**.

> **Nessuna chiave API, nessuna configurazione, nessuna rete.**
> Non c'è un `.env` da compilare, non c'è un segreto da procurarsi, non c'è una chiamata verso l'esterno.
> Clonare ed eseguire i quattro comandi qui sopra è l'intera procedura.

Su Linux/macOS o con Python 3.13 (rete di sicurezza): `python3 -m venv .venv && source .venv/bin/activate`, il resto è identico.

| Variabile | Default | A cosa serve |
|---|---|---|
| `LLM_MODE` | `off` | `off` \| `replay` — vedi la sezione qui sotto |
| `POSTA_CHIARA_OGGI` | `2026-10-06` | «Oggi» iniettabile (`app/backend/clock.py`): senza, le scadenze del corpus scadrebbero da sole |

Entrambe sono documentate in [`.env.example`](.env.example). Entrambe sono facoltative.

---

## ★ Dove sta l'AI — detto con precisione

Questa è la sezione che risponde alla domanda *«ma allora dov'è l'AI?»*, e la risposta onesta è anche la più forte.

> **L'AI ha progettato e scritto l'intero sistema**: i 9 agenti di build, i prompt, i contratti, il codice, i test.
> **A runtime il default è deterministico, di proposito**: verificabile, ripetibile, a costo zero, e la posta sanitaria e previdenziale di una persona anziana **non lascia il dispositivo**.
> **La seam LLM esiste, è completa, e si può vedere attraversata.**

### Due modalità, nessuna terza

| `LLM_MODE` | Cosa succede | Per chi |
|---|---|---|
| **`off`** *(default)* | La seam non viene attraversata: valgono i motori a regole. **0 token per email.** | Chi clona ed esegue senza configurare nulla |
| **`replay`** | La seam viene attraversata **per intero** e la risposta è letta da `app/fixtures/llm/`, indicizzata per hash di *(modello + prompt + input reso)* | La dimostrazione del percorso LLM in funzione |

### Non esiste codice di rete in `app/`

Nel progetto non c'è `import anthropic`, non c'è un client HTTP, non c'è una lettura di `ANTHROPIC_API_KEY`. Non sono disattivati: **non esistono**. Il pacchetto `anthropic` non è fra le dipendenze, e la sua assenza da [`requirements.txt`](requirements.txt) è dichiarata lì come scelta.

Questa non è un'affermazione: è un test. [`app/tests/test_llm_modes.py`](app/tests/test_llm_modes.py) apre **ogni sorgente Python di `app/`** (esclusi i test), ne costruisce l'AST e fallisce se trova un import di `anthropic`, `requests`, `urllib.request`, `http.client`, `httpx` o una chiamata su una di quelle radici. La garanzia è eseguibile, non dichiarata.

Conseguenza sulla configurazione sicura: **non esiste una chiave da proteggere.** `.env` è in `.gitignore` dal primo commit, ma la vera misura è che non c'è nulla da mettere in `.env`.

### ★ Cosa sono le fixture di `replay`

> Le fixture in `app/fixtures/llm/` sono **output di esempio scritti durante lo sviluppo**, conformi agli schema in [`agents/runtime/contracts/`](agents/runtime/contracts/).
> **Non sono registrazioni di chiamate API.** Questo progetto non ha mai usato una chiave, e nel repository non ce n'è nessuna.

Lo diciamo noi per primi perché è vero e perché è il genere di cosa che, taciuta, costerebbe la fiducia su tutto il resto. Ogni fixture contiene **solo** `model`, `content` e `usage`: nessun header, nessun campo di autenticazione, niente da cui una credenziale possa trapelare.

### Perché `replay` non è un `if finto: return "..."`

In `replay` il codice percorre la strada vera fino all'ultimo passo. **Solo il trasporto è assente.**

```
carica_prompt("semplificatore")     ← legge davvero agents/runtime/prompts/semplificatore.md
  └─ sostituzione delle variabili   ← {{corpo}}, {{fatti}}, {{feedback}}
     └─ chiave = sha256(modello + prompt + input reso)[:16]
        └─ lettura di app/fixtures/llm/<chiave>.json
           └─ parsing del JSON di risposta
              └─ validazione Pydantic dell'output strutturato   (contracts.py)
                 └─ conteggio dei token dal campo `usage`
                    └─ FactGuard verifica un output che il codice non ha generato
```

Girano quindi, per davvero: caricamento del prompt, sostituzione delle variabili, hashing, parsing JSON, validazione Pydantic, contabilità dei token e **verifica FactGuard su un testo che il motore deterministico non ha prodotto**. Se domani si aggiungesse il trasporto HTTP, nient'altro cambierebbe: è questo che rende la seam una scelta architetturale invece che una decorazione.

Dettaglio del routing e del model tiering: [`agents/runtime/routing.md`](agents/runtime/routing.md).
Costo quantificato delle due modalità: [`docs/TOKEN-EFFICIENCY.md`](docs/TOKEN-EFFICIENCY.md).

---

## Mappa del repository

```
posta-chiara/
├── app/             la soluzione
│   ├── backend/     FastAPI · orchestratore · i 6 agenti · 5 motori a regole · seam LLM · DB in memoria
│   ├── frontend/    HTML/CSS/JS vanilla, zero build, zero CDN
│   ├── fixtures/    output di esempio della seam LLM, scritti in fase di sviluppo
│   └── tests/       la suite pytest
├── agents/          ★ la struttura agentica — 9 agenti di build + 6 di runtime
├── presentation/    la presentazione HTML, brand Accenture
├── docs/            persona, percorso, limiti, processo, validazione, token
└── requirements.txt · .env.example · .gitignore · README.md
```

| Cartella | Cosa contiene, in concreto |
|---|---|
| [`app/backend/`](app/backend/) | `main.py` (API, `StaticFiles` montato per ultimo) · `orchestrator.py` (ordine, limiti, budget, stato) · `contracts.py` (i modelli Pydantic su ogni confine) · `clock.py` («oggi» costante) · `db.py` (SQLite in memoria, seminato da `data/mailbox.json`) · `agents/` (triage, sicurezza, semplificatore, verificatore, compositore) · `engines/` (`normalize`, `fact_extract`, `phishing_rules`, `plain_rules`, `gulpease`) · `llm/` (la seam) · `state/` (checkpoint esternalizzato) |
| [`app/frontend/`](app/frontend/) | Una pagina, tre viste. Base 20px, target 48px, contrasto AAA, `aria-live`, tastiera completa. Nessun passo di build: si apre e funziona |
| [`app/tests/`](app/tests/) | La suite. Include il test statico «zero rete» e i test end-to-end del percorso di Maria |
| [`agents/`](agents/) | I due sistemi agentici, tenuti separati: `build-time/` (chi ha costruito — agenti, [comandi](agents/build-time/commands/), [skill condivise](agents/build-time/skills/), [stato di build](agents/build-time/state/progress.json)) e `runtime/` (chi gira nel prodotto — specifiche, [prompt](agents/runtime/prompts/), [schema](agents/runtime/contracts/), [routing](agents/runtime/routing.md)). I **prompt di `runtime/prompts/` sono caricati dal codice**, non descritti da esso |
| [`presentation/`](presentation/) | Il deck HTML in 11 slide, brandizzato Accenture |
| [`docs/`](docs/) | I quattro deliverable richiesti dal bando + validazione + efficienza |

---

## La pipeline di runtime — 6 agenti e un orchestratore

```
                       Email in arrivo
                             │
                             ▼
                 ┌───────────────────────┐
                 │    ORCHESTRATORE      │  stato esternalizzato (SQL, ispezionabile)
                 │  max_iter · timeout   │  ripartenza da checkpoint
                 │  budget token         │  routing deterministico-first
                 └───────────┬───────────┘
                             │
      ┌──────────────────────┼──────────────────────┐
      ▼                      ▼                      ▼
[1] TRIAGE            [2] SICUREZZA          [3] ESTRAZIONE FATTI
 categoria             semaforo + AZIONE      date · importi · orari
 e priorità            regole spiegabili      ancorati a keyword
 regole (seam Haiku)   mai LLM                mai LLM
      │                      │                      │
      └──────────────────────┴──────────┬───────────┘
                                        ▼
                            [4] SEMPLIFICATORE
                             Chi / Cosa / Entro quando
                             regole (seam Sonnet)
                                        │
                                        ▼
                            [5] VERIFICATORE ← FactGuard, NON è un LLM
                             confronta i fatti originale vs semplificato
                                        │
                       ┌────────────────┼────────────────┐
                    PASSA            FALLISCE      FALLISCE ancora
                       │        retry con feedback   (dopo 2 iterazioni)
                       │        ──────┘                   │
                       ▼                                  ▼
                mostra semplificato            FALLBACK: originale
                       │                       coi fatti evidenziati
                       ▼
                            [6] COMPOSITORE
                             3 bozze per intento,
                             slot riempiti coi fatti VERIFICATI
                                        │
                                        ▼
                            ╔═══════════════════════╗
                            ║  ESCALATION UMANA     ║  HITL intenzionale
                            ║  Maria rilegge        ║  nessun invio automatico,
                            ║  e preme invia        ║  mai, in nessun caso
                            ╚═══════════════════════╝
```

Specifica completa di ciascun agente — scopo, input, output, passi, vincoli, fallback e **quando non usare l'LLM** — in [`agents/README.md`](agents/README.md) §2 e nei sei file `agents/runtime/0*.md`.

**Il principio del prodotto, in una riga:** *il motore propone, il verificatore controlla, la persona decide.*

---

## ★ Criterio di valutazione → file

La mappa che un giurato deve trovare senza cercarla. Ogni riga punta a file che esistono nel repository.

| # | Criterio | Peso | Dove si vede, concretamente |
|---|---|---:|---|
| 01 | **Profondità agentica** | **24%** | [`app/backend/orchestrator.py`](app/backend/orchestrator.py) — pipeline esplicita, non chiamate sparse · 6 agenti, uno per passo, **un contratto Pydantic ciascuno**: [`app/backend/agents/`](app/backend/agents/) più l'estrazione fatti in [`app/backend/engines/fact_extract.py`](app/backend/engines/fact_extract.py) · **stato esternalizzato** in [`app/backend/state/store.py`](app/backend/state/store.py) + tabella `stato_pipeline` in [`db.py`](app/backend/db.py), ispezionabile in demo da `GET /api/debug/stato` · **output strutturati** in [`app/backend/contracts.py`](app/backend/contracts.py) e [`agents/runtime/contracts/`](agents/runtime/contracts/) · workflow multi-step in [`agents/runtime/orchestrator.md`](agents/runtime/orchestrator.md) |
| 02 | **Qualità delle istruzioni** | **19%** | [`agents/`](agents/) — ogni file ha la stessa struttura *Scopo · Input · Output · Passi · Vincoli · Fallback · Confine* · **niente sovrapposizioni**: [`agents/README.md`](agents/README.md) mappa, [`agents/workflow.md`](agents/workflow.md) ordina, [`agents/build-time/CLAUDE.md`](agents/build-time/CLAUDE.md) vincola, e ciascuno rimanda agli altri invece di ripeterli · ★ i prompt in [`agents/runtime/prompts/`](agents/runtime/prompts/) **sono caricati dal codice** (`client.carica_prompt`): documentazione e comportamento sono lo stesso artefatto |
| 03 | **Robustezza** | **15%** | Fallback dichiarato per ogni agente nel proprio file `runtime/0*.md` e applicato in `orchestrator._Corsa.esegui` · `MAX_SIMPLIFY_RETRIES = 2`, `TIMEOUT_AGENTE_MS = 2000`, `BUDGET_TOKEN_EMAIL = 4000` · **HITL su due livelli**: nel prodotto nessun invio parte senza il click di Maria (`POST /api/email/{id}/invia`), nella build nessuna fase avanza senza un gate umano registrato in [`agents/build-time/state/progress.json`](agents/build-time/state/progress.json) · FactGuard: [`app/backend/agents/verificatore.py`](app/backend/agents/verificatore.py) |
| 04 | **Efficienza dei token** | **12%** | [`agents/runtime/routing.md`](agents/runtime/routing.md) — per ogni agente è scritto **quando NON chiamare un LLM** · **0 token per email** nel default, misurati · cache sullo stato esternalizzato: ri-aprire la stessa email costa 0 · numeri affiancati in [`docs/TOKEN-EFFICIENCY.md`](docs/TOKEN-EFFICIENCY.md) |
| 05 | **Qualità tecnica** | **12%** | Error handling centralizzato in `orchestrator._Corsa.esegui` (un'eccezione degrada, non uccide) e handler globale in [`main.py`](app/backend/main.py) · timeout per agente · retry con feedback sul ciclo semplifica/verifica · **secrets ed env**: nessuna chiave esiste, [`.env.example`](.env.example) documenta le due sole variabili, entrambe facoltative · **model tiering** dichiarato in `routing.md` e implementato in [`llm/client.py`](app/backend/llm/client.py) (`MODELLO_TRIAGE` Haiku, `MODELLO_LINGUA` Sonnet) |
| 06 | **Adeguatezza degli strumenti** | **11%** | [`agents/README.md`](agents/README.md) §3 — 9 agenti di build, ciascuno con una motivazione dichiarata e un **confine di file disgiunto** · **3 agenti di runtime su 6 non hanno una seam LLM, e il perché è scritto** in `routing.md` §2: lo strumento sbagliato nel posto sbagliato costa quanto quello mancante · 3 comandi riutilizzabili in [`agents/build-time/commands/`](agents/build-time/commands/) e 3 skill condivise in [`agents/build-time/skills/`](agents/build-time/skills/), non uno di più · 5 motori a regole, uno per compito, nessuna libreria aggiunta dove basta la standard library |
| 07 | **Documentazione** | **7%** | Questo README · [`agents/`](agents/) · [`docs/`](docs/): [PERSONA](docs/PERSONA.md) · [PERCORSO-ASSISTITO](docs/PERCORSO-ASSISTITO.md) · [AUTONOMIA-E-LIMITI](docs/AUTONOMIA-E-LIMITI.md) · [PROCESSO-AI](docs/PROCESSO-AI.md) · [VALIDAZIONE](docs/VALIDAZIONE.md) · [TOKEN-EFFICIENCY](docs/TOKEN-EFFICIENCY.md) |

---

## Test

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

**Risultato su un clone pulito, con le sole dipendenze di `requirements.txt`: 98 passati, 1 saltato.**

Il saltato è la suite end-to-end del browser ([`app/tests/test_e2e_frontend.py`](app/tests/test_e2e_frontend.py)): usa **Playwright**, che è una dipendenza **facoltativa** e non è in `requirements.txt`. Senza Playwright il modulo si salta invece di fallire, così la suite principale non dipende da un pacchetto opzionale.

Con Playwright installato quella suite gira davvero — avvia un `uvicorn` su `127.0.0.1` e percorre l'interfaccia in un Chromium — e il totale diventa **127 passati, 0 saltati**. Dettaglio di cosa copre ciascun file: [`docs/VALIDAZIONE.md`](docs/VALIDAZIONE.md).

**Nessun test tocca la rete** — ed è banale rispettarlo, perché nel progetto non esiste codice capace di toccarla. Il primo test di `test_llm_modes.py` lo dimostra invece di assumerlo.

Prova di indipendenza dalla rete: si stacca il Wi-Fi e si rilancia `pytest` e `uvicorn` in `off` **e** in `replay`. Il comportamento è identico.

---

## Limiti

Sono dichiarati, non minimizzati: **[`docs/AUTONOMIA-E-LIMITI.md`](docs/AUTONOMIA-E-LIMITI.md)**.

I tre che pesano di più, in sintesi:

- **FactGuard verifica la *presenza* dei fatti, non il loro *ruolo*.** Non distingue «importo dovuto» da «importo già versato». È esattamente lì che serve la revisione umana, ed è il motivo per cui l'originale resta sempre a un tocco.
- **La classificazione delle truffe non è infallibile.** La soglia è prudenziale per costruzione: nel dubbio il sistema dice *«chieda a una persona di fiducia»*, e non dice **mai** *«è sicura»*.
- **Le fixture di `replay` sono output di esempio scritti in fase di sviluppo, non sono registrazioni di chiamate API.** Dimostrano che la seam è completa; non dimostrano come si comporterebbe un modello reale su questo compito.

---

## Come è stato costruito

Nove agenti di build con confini di file disgiunti, tre gate umani obbligatori, e tre falsi positivi reali trovati eseguendo la pipeline sul corpus e corretti a mano: **[`docs/PROCESSO-AI.md`](docs/PROCESSO-AI.md)**.

> *Abbiamo scritto prima gli agenti, poi gli agenti hanno scritto l'app.*

---

*Prototipo realizzato per l'Hagenthon Accenture — Application Engineering. Il corpus di posta è dichiaratamente fittizio: mittenti inventati, protocolli inventati, nessun dato reale, nessun consiglio medico, fiscale o legale.*
