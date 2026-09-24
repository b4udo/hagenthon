# `agents/` — la struttura agentica di Posta Chiara

Questa cartella contiene **due sistemi agentici distinti**, e la distinzione è deliberata:

| | Cosa contiene | Quando gira |
|---|---|---|
| **`build-time/`** | I 9 agenti che **hanno costruito** questa soluzione durante l'hackathon | Durante lo sviluppo, in Claude Code |
| **`runtime/`** | I 6 agenti che **girano nel prodotto** ogni volta che Maria apre un'email | In produzione, dentro `app/backend/` |

Tenerli separati evita l'errore più comune: documentare il processo di sviluppo e chiamarlo
"architettura agentica", o viceversa. Qui ci sono entrambi, e ciascuno ha il proprio `workflow`.

---

## 1. Il punto architetturale principale

> **I prompt in `runtime/prompts/*.md` non descrivono il codice: sono caricati dal codice.**

`app/backend/llm/client.py` espone `carica_prompt(nome)` che legge **questa cartella** a runtime.
Non esiste una copia del prompt dentro il codice Python. Conseguenza: **è impossibile che la
documentazione diverga dal comportamento**, perché sono lo stesso file.

Lo stesso vale per i contratti: gli schema in `runtime/contracts/*.schema.json` sono generati dai
modelli Pydantic in `app/backend/contracts.py` e ri-verificati dal test
`app/tests/test_contracts_sync.py`. Se un modello cambia e lo schema no, la suite diventa rossa.

---

## 2. Il sistema di runtime — 6 agenti

```
                    Email in arrivo
                          │
                          ▼
              ┌───────────────────────┐
              │    ORCHESTRATORE      │  stato esternalizzato su disco (JSON)
              │  max_iter, timeout,   │  ripartenza da checkpoint
              │  budget token         │  routing deterministico-first
              └───────────┬───────────┘
                          │
   ┌──────────────────────┼──────────────────────┐
   ▼                      ▼                      ▼
[1] TRIAGE          [2] SICUREZZA         [3] ESTRAZIONE FATTI
 ente/persona/       semaforo + AZIONE      date, importi, orari
 commerciale/        regole spiegabili      ancorati a keyword
 sospetta            deterministico         deterministico
 regole (seam Haiku)                        mai LLM
   │                      │                      │
   └──────────────────────┴──────────┬───────────┘
                                     ▼
                         [4] SEMPLIFICATORE
                          parole semplici +
                          Chi / Cosa / Entro quando
                          regole (seam Sonnet)
                                     │
                                     ▼
                         [5] VERIFICATORE  ← FactGuard, NON è un LLM
                          confronta i fatti originale vs semplificato
                                     │
                    ┌────────────────┼────────────────┐
                 PASSA            FALLISCE         FALLISCE ancora
                    │          retry con feedback   (dopo 2 iterazioni)
                    │          ──────┘                   │
                    ▼                                    ▼
             mostra semplificato               FALLBACK: originale
                    │                          con punti evidenziati
                    ▼
                         [6] COMPOSITORE
                          bozza di risposta per intento,
                          slot riempiti coi fatti VERIFICATI
                                     │
                                     ▼
                         ╔═══════════════════════╗
                         ║  ESCALATION UMANA     ║  HITL intenzionale
                         ║  Maria rilegge e      ║  nessun invio automatico
                         ║  preme invia          ║  mai, in nessun caso
                         ╚═══════════════════════╝
```

| # | Agente | Specifica | Implementazione | LLM? |
|---|---|---|---|---|
| — | Orchestratore | [`runtime/orchestrator.md`](runtime/orchestrator.md) | `app/backend/orchestrator.py` | mai |
| 1 | Triage | [`runtime/01-triage.md`](runtime/01-triage.md) | `app/backend/agents/triage.py` | seam (Haiku) |
| 2 | Sicurezza | [`runtime/02-sicurezza.md`](runtime/02-sicurezza.md) | `app/backend/agents/sicurezza.py` | **mai — per scelta** |
| 3 | Estrazione fatti | [`runtime/03-estrazione-fatti.md`](runtime/03-estrazione-fatti.md) | `app/backend/agents/estrazione_fatti.py` | **mai — per scelta** |
| 4 | Semplificatore | [`runtime/04-semplificatore.md`](runtime/04-semplificatore.md) | `app/backend/agents/semplificatore.py` | seam (Sonnet) |
| 5 | Verificatore | [`runtime/05-verificatore.md`](runtime/05-verificatore.md) | `app/backend/agents/verificatore.py` | **mai — per progetto** |
| 6 | Compositore | [`runtime/06-compositore.md`](runtime/06-compositore.md) | `app/backend/agents/compositore.py` | seam (Sonnet) |

Il routing e la regola *"quando NON chiamare un LLM"* per ciascuno: [`runtime/routing.md`](runtime/routing.md).

---

## 3. Il sistema di build — 9 agenti

Il progetto è stato sviluppato da **una persona sola**. I sotto-agenti sostituiscono il secondo
sviluppatore: si dividono per **confine di file disgiunto**, così possono lavorare in parallelo
senza collidere.

```
                    ┌──────────────────────────┐
                    │      TEAM LEADER         │  possiede piano e timebox
                    │  gate di fase, non       │  stato: state/progress.json
                    │  scrive codice di prod.  │  ferma tutto al freeze
                    └────────────┬─────────────┘
                                 │
        ┌────────────────┬───────┴────────┬────────────────┐
        ▼                ▼                ▼                ▼
   DEVELOPERS          QA            REVIEW           HUMAN GATE
   dev-core         test-engineer   bando-compliance   la persona,
   dev-pipeline     qa-critic        audit contro      ai checkpoint
   dev-frontend      (sola lettura   i 4 file           T+1:15
   dev-corpus         su app/)       del bando          T+2:20
   dev-deck                                             T+2:30
```

| Agente | Confine di file | Specifica |
|---|---|---|
| **team-leader** | nessuno — delega e verifica | [`build-time/team-leader.md`](build-time/team-leader.md) |
| **dev-core** | `engines/`, `llm/`, `fixtures/`, `verificatore.py`, `contracts.py`, `clock.py` | [`build-time/developers/dev-core.md`](build-time/developers/dev-core.md) |
| **dev-pipeline** | `agents/` (tranne verificatore), `orchestrator.py`, `state/`, `main.py` | [`build-time/developers/dev-pipeline.md`](build-time/developers/dev-pipeline.md) |
| **dev-frontend** | `app/frontend/` | [`build-time/developers/dev-frontend.md`](build-time/developers/dev-frontend.md) |
| **dev-corpus** | `app/backend/data/mailbox.json` | [`build-time/developers/dev-corpus.md`](build-time/developers/dev-corpus.md) |
| **dev-deck** | `presentation/` | [`build-time/developers/dev-deck.md`](build-time/developers/dev-deck.md) |
| **test-engineer** | `app/tests/` | [`build-time/qa/test-engineer.md`](build-time/qa/test-engineer.md) |
| **qa-critic** | *sola lettura* | [`build-time/qa/qa-critic.md`](build-time/qa/qa-critic.md) |
| **bando-compliance** | *sola lettura* | [`build-time/review/bando-compliance.md`](build-time/review/bando-compliance.md) |

Ordine, handoff e gate: [`workflow.md`](workflow.md).
Comandi riutilizzabili: [`build-time/commands/`](build-time/commands/).
Conoscenza condivisa (accessibilità, italiano semplice, brand): [`build-time/skills/`](build-time/skills/).

---

## 4. HITL a due livelli

Il criterio *Robustezza* chiede "escalation umana intenzionale". Nel progetto compare due volte,
e la simmetria non è casuale:

> **Nel prodotto:** nessuna email parte senza che Maria abbia riletto e premuto invia.
> **Nella build:** nessuna fase avanza senza che lo sviluppatore abbia approvato il gate.

I tre gate di build sono registrati in [`build-time/state/progress.json`](build-time/state/progress.json),
con lo stesso pattern di stato esternalizzato usato a runtime. Verificabile, non dichiarato.

---

## 5. Mappa criterio di valutazione → file

| Criterio | Peso | Dove guardare |
|---|---:|---|
| Profondità agentica | 24% | `runtime/orchestrator.md` · `app/backend/orchestrator.py` · `app/backend/state/` (stato esternalizzato) · `runtime/contracts/` (output strutturati) |
| Qualità delle istruzioni | 19% | Ogni file di questa cartella ha la stessa struttura: Scopo · Input · Output · Passi · Vincoli · Fallback · Confine. `runtime/prompts/` è **caricato dal codice**: zero divergenza |
| Robustezza | 15% | `runtime/05-verificatore.md` (FactGuard) · `runtime/orchestrator.md` §limiti · `workflow.md` §gate umani |
| Efficienza dei token | 12% | `runtime/routing.md` — per ogni agente è scritto **quando NON chiamare un LLM** · `docs/TOKEN-EFFICIENCY.md` |
| Qualità tecnica | 12% | `app/backend/llm/client.py` (2 modalità, zero rete) · `app/tests/` · `runtime/routing.md` §model tiering |
| Adeguatezza strumenti | 11% | Questo README §3 — ogni agente ha una motivazione dichiarata e un confine disgiunto |
| Documentazione | 7% | `README.md` alla radice · questa cartella · `docs/` |
