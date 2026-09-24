# Workflow — ordine, handoff, checkpoint, gate umani

Questo file descrive il **workflow di build**: come i 9 agenti di `build-time/` si sono divisi
le 4 ore dell'hackathon. Il workflow di **runtime** (i 6 agenti che girano nel prodotto) è in
[`runtime/orchestrator.md`](runtime/orchestrator.md).

---

## 1. La regola che rende fattibili 4 ore

> **Due agenti non toccano mai lo stesso file.**

Non è una linea guida: è la condizione che permette il parallelismo. Ogni agente in
[`README.md` §3](README.md) ha un **confine di file dichiarato**, e i confini sono disgiunti.
Il `team-leader` rifiuta qualsiasi delega che violi un confine.

Corollari operativi:
- `dev-corpus` e `dev-deck` non toccano mai codice → possono girare **sempre** in parallelo.
- `test-engineer` scrive i test **dai contratti**, non dall'implementazione → parte **insieme**
  a `dev-core`, non dopo. Questo è anche il motivo per cui i test verificano il comportamento
  voluto invece di fotografare quello ottenuto.
- `dev-pipeline` non parte finché i contratti di `dev-core` non sono fermi.
- `qa-critic` gira solo a valle e in **sola lettura**.

---

## 2. Sequenza

| Orario | Fase | Agenti attivi | Esito dimostrabile |
|---|---|---|---|
| **0:00–0:10** | Smoke: venv, dipendenze congelate, un endpoint, una pagina statica | *persona* | Gira |
| **0:10–0:35** | `agents/` completa: build-time, runtime, contratti, prompt | team-leader | La struttura agentica esiste **prima** del codice |
| **0:35–1:15** | `contracts` · `clock` · `normalize` · `fact_extract` · **FactGuard** · fixture LLM ‖ test dai contratti ‖ corpus 6 email | **dev-core ‖ test-engineer ‖ dev-corpus** | Il rifiuto di FactGuard, in diretta |
| **1:15** | 🔶 **GATE UMANO 1** — FactGuard regge? | *persona* | — |
| **1:15–1:50** | triage · sicurezza con azioni · `plain_rules` · orchestratore · stato · `main.py` ‖ test | **dev-pipeline ‖ test-engineer** | Chi / Cosa / Entro quando + semaforo |
| **1:50–2:20** | Frontend: lettura, badge, risposta guidata a 3 intenti, contatore autonomia | **dev-frontend** | Il percorso completo di Maria |
| **1:00–2:30** | `presentation/index.html`, con screenshot veri man mano che compaiono | **dev-deck** *(in parallelo)* | Il deck cresce col prodotto |
| **2:20** | 🔶 **GATE UMANO 2** — il percorso end-to-end gira? | *persona* | — |
| **2:20–2:30** | P1: pannello "Come ha ragionato" → prova in `replay` a rete staccata → Gulpease → sintesi vocale | dev-frontend | La seam LLM gira offline |
| **2:30** | ⛔ **FEATURE FREEZE** · 🔶 **GATE UMANO 3** | *persona* | — |
| **2:30–2:50** | `pytest` finale · checklist a11y · percorso demo · audit bando ‖ `docs/` · screenshot di backup | **qa-critic ‖ bando-compliance** | Checklist verde |
| **2:50–4:00** | Rifinitura deck + due prove a voce col cronometro | *persona* + dev-deck | 5 minuti netti |

**Punto di non ritorno — T+2:20.** Se la risposta guidata non gira, si taglia tutto il resto e si
porta a casa quella. È il punto esatto in cui Maria oggi si ferma: senza, non c'è dimostrazione.

---

## 3. I gate umani

Il `team-leader` **si ferma e chiede**. Non prosegue da solo. Ogni gate ha una domanda binaria,
e una risposta "no" ha una conseguenza già decisa — così la decisione sotto pressione non va
improvvisata.

| Gate | Quando | Domanda | Se la risposta è NO |
|---|---|---|---|
| **1** | T+1:15 | FactGuard rifiuta l'importo troncato e accetta la data riformattata? | Si riduce lo scope a **soli importi**, e si taglia la verifica su date e orari |
| **2** | T+2:20 | Maria può leggere un'email e inviare una risposta, dal browser, senza toccare la tastiera? | Si tagliano tutte le P1 e si usano i 10 minuti per stabilizzare quel percorso |
| **3** | T+2:30 | Feature freeze: si consegna così? | Non è una domanda con un "no": da qui solo correzioni di bug e documentazione |

Esito e orario reale di ogni gate sono registrati in
[`build-time/state/progress.json`](build-time/state/progress.json).

---

## 4. Handoff — cosa passa da un agente all'altro

Gli handoff sono **artefatti su disco**, mai conversazione. Un agente che riceve deve poter
lavorare leggendo solo file.

```
  dev-core ──► app/backend/contracts.py ──► dev-pipeline   (modelli Pydantic)
           └─► agents/runtime/contracts/ ─► test-engineer  (JSON Schema)

  dev-corpus ──► app/backend/data/mailbox.json ──► dev-pipeline, dev-frontend

  dev-pipeline ──► GET /api/email/{id} ──► dev-frontend    (contratto HTTP)

  chiunque ──► screenshot in presentation/img/ ──► dev-deck

  qa-critic ──► report in chiaro ──► team-leader ──► l'agente che possiede quel file
```

Nota sull'ultimo: `qa-critic` **non corregge**. Riferisce al leader, che delega la correzione a
chi possiede il confine di file. Un tester che può riscrivere ciò che testa finisce per
"aggiustare" i test invece del codice.

---

## 5. Limiti di iterazione — anche in build

Gli stessi limiti che il prodotto applica a sé stesso valgono per la build:

- Un agente che fallisce **due volte** sullo stesso task non riprova una terza: escala al leader.
- Il leader che non sa decidere escala alla persona. Non improvvisa.
- Nessun agente installa dipendenze dopo T+0:15 (vedi `docs/` e `requirements.txt`).
- Nessun agente cambia i file del bando in `Downloads/hagenthon/`: sono di sola lettura.
