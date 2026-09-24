# Orchestratore — runtime

> Esiste perché una pipeline di 6 agenti senza un punto unico che possieda ordine, limiti e stato
> è solo un insieme di chiamate sparse. Qui c'è l'unico posto che decide chi gira, quando si ferma
> e cosa si salva.

**Implementazione:** `app/backend/orchestrator.py`
**Non è un LLM.** È codice deterministico che coordina agenti, alcuni dei quali hanno una seam LLM.

---

## Scopo

Prendere un'email grezza e produrre un `RisultatoPipeline` completo, oppure un risultato
**degradato ma sempre utilizzabile**. L'orchestratore non ha il diritto di restituire un errore
all'interfaccia: Maria deve sempre vedere qualcosa, al minimo l'email originale.

---

## Sequenza

```
  carica stato          ── se esiste un checkpoint per questa email, riparti da lì
        │
        ├─► [1] triage             ── categoria, priorità
        ├─► [2] sicurezza          ── semaforo + azione eseguibile
        ├─► [3] estrazione_fatti   ── date, importi, orari (l'input di FactGuard)
        │
        ├─► ciclo di semplificazione, al massimo MAX_SIMPLIFY_RETRIES + 1 tentativi
        │     [4] semplificatore ──► [5] verificatore (FactGuard)
        │           ▲                       │
        │           └──── feedback ─────────┤ fallisce
        │                                   ▼ passa
        │                             esci dal ciclo
        │
        ├─► se il ciclo esaurisce i tentativi: `semplificazione_mostrata = False`
        │   e l'interfaccia mostra l'originale coi fatti evidenziati
        │
        ├─► [6] compositore        ── bozze per intento, solo su fatti VERIFICATI
        │
        └─► salva stato            ── JSON su disco, ispezionabile
```

Il passo 6 gira **solo** se il semaforo non è rosso. Su rosso non si compone alcuna risposta:
proporre una bozza a una mail di phishing sarebbe il peggior fallimento possibile del prodotto.

---

## Input

`Email` (da `app/backend/data/mailbox.json`), più il flag di demo `avvelena: bool` che corrompe
deliberatamente l'output del semplificatore (vedi [`05-verificatore.md`](05-verificatore.md)).

## Output

`RisultatoPipeline` — contratto in `app/backend/contracts.py`, schema in
[`contracts/risultato-pipeline.schema.json`](contracts/risultato-pipeline.schema.json).

Include sempre `tracce: list[TracciaAgente]`: per ogni agente, la modalità usata (`regole` o
`llm-replay`), la durata, l'esito e i token. È ciò che alimenta il pannello **"Come ha ragionato"**
nell'interfaccia — e la ragione per cui il sistema è ispezionabile invece che magico.

---

## Limiti — tutti espliciti, tutti testati

| Limite | Valore | Cosa succede al superamento |
|---|---|---|
| `MAX_SIMPLIFY_RETRIES` | `2` | Si esce dal ciclo, `semplificazione_mostrata = False`, fallback all'originale |
| `TIMEOUT_AGENTE_MS` | `2000` | L'agente è considerato fallito, si applica il suo fallback dichiarato |
| `BUDGET_TOKEN_EMAIL` | `4000` | Le seam LLM restanti girano **a regole**. La pipeline non si ferma mai per budget |
| Errore non gestito in un agente | — | Catturato dall'orchestratore, tracciato come `esito: "errore"`, si applica il fallback |

> **Nessun percorso della pipeline può terminare senza risultato.** Ogni agente dichiara un
> fallback nel proprio file, e l'orchestratore lo applica. Un agente che solleva un'eccezione
> non uccide la pipeline: la degrada.

---

## Stato esternalizzato

**Dove:** `app/backend/state/data/<email_id>.json`
**Chi lo scrive:** `app/backend/state/store.py`

Contiene il `RisultatoPipeline` serializzato più `aggiornato_il`. Tre conseguenze concrete:

1. **Riprendibilità** — se il processo muore a metà, ripartendo si rilegge il checkpoint invece
   di rifare tutto.
2. **Costo marginale zero** — ri-aprire la stessa email non ri-esegue la pipeline. Vedi
   [`routing.md`](routing.md).
3. **Ispezionabilità** — in demo si apre il file e si mostra cosa ha deciso ogni agente. Lo stato
   non è una variabile in memoria di cui fidarsi sulla parola.

La cartella è in `.gitignore`: è stato di runtime, non un artefatto di consegna.

---

## Vincoli

- **Mai inviare un'email.** L'orchestratore produce bozze. L'invio è un endpoint separato,
  raggiungibile solo da un'azione esplicita di Maria.
- **Mai saltare il verificatore.** Nessun testo semplificato raggiunge l'interfaccia senza
  essere passato da FactGuard. Se il verificatore è indisponibile, si mostra l'originale.
- **Mai chiamare una seam LLM quando `routing.md` dice di non farlo.**
- L'ordine degli agenti è fisso. Non esiste routing dinamico "intelligente": sarebbe
  imprevedibilità travestita da flessibilità, su un dominio dove l'errore costa a una persona
  di 74 anni.

## Fallback

| Situazione | Comportamento |
|---|---|
| Un agente va in timeout o in errore | Si applica il fallback dell'agente, si traccia, si prosegue |
| Il ciclo di semplificazione esaurisce i tentativi | Originale + fatti evidenziati |
| Budget token esaurito | Tutto a regole, zero token, risultato completo |
| Lo stato su disco è corrotto o illeggibile | Si ignora e si ricalcola da zero. Mai un errore all'utente |
| `LLM_MODE=replay` ma la fixture manca | Log rumoroso, si degrada a regole. Nei test è invece un errore secco |
