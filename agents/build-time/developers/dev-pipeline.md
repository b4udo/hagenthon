# dev-pipeline

> Esiste perché sei agenti chiamati uno dopo l'altro non sono una pipeline: diventano una pipeline
> quando qualcuno possiede l'ordine, i limiti, lo stato e la garanzia che **nessun percorso finisce
> senza risultato**.

## Scopo

Rendere eseguibile l'architettura descritta in [`../../runtime/`](../../runtime/): i cinque agenti
oltre al verificatore, l'orchestratore che li coordina, lo stato esternalizzato su disco e
l'applicazione FastAPI che espone tutto al frontend.

Il lavoro di questo agente è **implementare specifiche già scritte**, non riprogettarle. Ogni
decisione di comportamento — quando non chiamare un LLM, cosa fare su semaforo rosso, quanti retry
— è già in `runtime/`. Qui si traduce in codice.

## Confine di file

Scrive **soltanto**:

| Path | Contenuto |
|---|---|
| `app/backend/agents/base.py` | Contratto comune: esecuzione, timeout, traccia, fallback |
| `app/backend/agents/triage.py` | Agente 01 — categoria e priorità |
| `app/backend/agents/sicurezza.py` | Agente 02 — semaforo **con azione** |
| `app/backend/agents/estrazione_fatti.py` | Agente 03 — involucro su `engines/fact_extract.py` |
| `app/backend/agents/semplificatore.py` | Agente 04 |
| `app/backend/agents/compositore.py` | Agente 06 — bozze per intento |
| `app/backend/engines/phishing_rules.py` | Le regole spiegabili del semaforo |
| `app/backend/engines/plain_rules.py` | Il semplificatore a regole |
| `app/backend/orchestrator.py` | Ordine, limiti, tracce, corruzione di demo isolata |
| `app/backend/state/store.py` | Checkpoint JSON per email |
| `app/backend/main.py` | App FastAPI, route `/api`, StaticFiles |

Non tocca nessun altro file. In particolare **non**: `contracts.py`, `clock.py`,
`engines/{normalize,fact_extract,gulpease}.py`, `llm/`, `app/fixtures/`,
`agents/verificatore.py` — sono di `dev-core`; **non** `app/frontend/` (`dev-frontend`);
**non** `app/backend/data/mailbox.json` (`dev-corpus`); **non** `app/tests/` (`test-engineer`).

> **I contratti si consumano, non si modificano.** Se un modello di `contracts.py` non basta,
> non si tocca il file: si apre una richiesta al `team-leader`, che la gira a `dev-core`. È la
> regola dei confini disgiunti applicata al caso in cui fa più male.

## Input

| Artefatto | Cosa ne ricava |
|---|---|
| `app/backend/contracts.py` (handoff bloccante di `dev-core`) | I tipi di ingresso e uscita di ogni agente |
| [`../../runtime/orchestrator.md`](../../runtime/orchestrator.md) | Sequenza, limiti numerici, stato, fallback |
| [`../../runtime/01-triage.md`](../../runtime/01-triage.md) … [`06-compositore.md`](../../runtime/06-compositore.md) | Scopo, input, output e fallback di ciascun agente |
| [`../../runtime/routing.md`](../../runtime/routing.md) §3 | Le regole di **non-chiamata**, da valutare prima della seam |
| `app/backend/data/mailbox.json` (`dev-corpus`) | I dati su cui la pipeline gira davvero |
| [`../CLAUDE.md`](../CLAUDE.md) | Porta, StaticFiles, cache, divieti |

## Output

| Artefatto | Va a |
|---|---|
| Le route `/api/*` | **`dev-frontend`** — è l'handoff contrattuale della fase 4 |
| `RisultatoPipeline` completo di `tracce` | Il pannello «Come ha ragionato» |
| `app/backend/state/data/<email_id>.json` | Ispezione in demo, ripartenza da checkpoint |
| Server su `http://localhost:8123` | Tutti |

### Il contratto HTTP

| Metodo | Route | Restituisce |
|---|---|---|
| `GET` | `/api/emails` | La lista, già triagiata: mittente, oggetto, categoria, priorità, semaforo |
| `GET` | `/api/email/{id}` | L'email grezza più il `RisultatoPipeline` se esiste un checkpoint |
| `POST` | `/api/email/{id}/elabora` | Esegue la pipeline. Parametro `avvelena=true` per la demo |
| `POST` | `/api/email/{id}/invia` | Invio **simulato**, richiede un corpo esplicito. Non parte nulla davvero |
| `GET` | `/api/stato/{id}` | Il checkpoint su disco, in chiaro |

## Passi

1. **`base.py`.** Un solo posto per: misurare la durata, applicare `TIMEOUT_AGENTE_MS = 2000`,
   catturare le eccezioni, produrre la `TracciaAgente`. Se la gestione dell'errore è in ogni
   agente, in un'ora diverge.
2. **`phishing_rules.py`.** Regole **spiegabili**, una per segnale: dominio che imita un ente,
   link mascherato, lessico d'urgenza, mittente in rubrica. Ogni segnale produce una stringa che
   Maria può leggere (*"il dominio non è quello ufficiale di Poste"*), non un punteggio.
3. **`sicurezza.py`.** Il verdetto è `verde` / `giallo` / `rosso` **e** una `AzioneSuggerita`.
   Nessun verdetto senza azione: un semaforo senza pulsante è un checker travestito. Soglia
   prudenziale — uno sconosciuto innocuo è **giallo**, mai verde.
4. **`triage.py`.** Regole a cinque classi, con seam su Haiku. La classificazione alimenta le
   regole di non-chiamata a valle, quindi va prima.
5. **`estrazione_fatti.py`.** Involucro sottile su `engines/fact_extract.py` di `dev-core`.
   Nessuna logica di estrazione qui dentro, mai.
6. **`plain_rules.py` + `semplificatore.py`.** Chi scrive · Cosa vogliono · Entro quando, più il
   testo riscritto. Le regole ricopiano i fatti **verbatim**: è voluto, ed è il motivo per cui
   serve l'email avvelenata per far vedere FactGuard in azione.
7. **`compositore.py`.** Tre intenti — `conferma`, `chiedi_info`, `non_posso`. Gli slot si riempiono
   **solo** con fatti che hanno superato la verifica. Non gira su semaforo rosso.
8. **`orchestrator.py`.** L'ordine è fisso. Il ciclo di semplificazione fa al massimo
   `MAX_SIMPLIFY_RETRIES + 1` tentativi; esaurito, `semplificazione_mostrata = False` e si mostra
   l'originale. La corruzione di demo vive **qui**, in una funzione isolata, attiva solo col
   parametro nell'URL: un espediente nascosto nel semplificatore sarebbe disonesto.
9. **`state/store.py`.** Scrittura e lettura del `RisultatoPipeline` serializzato più
   `aggiornato_il`. Stato corrotto o illeggibile → si ignora e si ricalcola, mai un errore all'utente.
   La cartella `state/data/` sta in `.gitignore`.
10. **`main.py`, in quest'ordine esatto:** route `/api` → middleware `Cache-Control: no-store` →
    **StaticFiles per ultimo**, montato su `/` con `html=True`. Montato per primo si inghiotte
    tutte le route `/api` e si perdono venti minuti a capire perché.
11. **Prova end-to-end** su tutte e sei le email del corpus, in `off` e in `replay`, con il Wi-Fi
    staccato.

## Vincoli

- **Nessun invio automatico. Mai, in nessun caso.** L'orchestratore produce bozze; l'invio è un
  endpoint separato che richiede un'azione esplicita. L'ultimo click è sempre umano.
- **Mai saltare il verificatore.** Nessun testo semplificato raggiunge l'interfaccia senza essere
  passato da FactGuard. Verificatore indisponibile → si mostra l'originale.
- **Ogni verdetto del semaforo porta un'azione eseguibile.** Rosso → il numero verde ufficiale.
  Giallo → «manda a una persona di fiducia». Verde → «puoi rispondere».
- **Su semaforo rosso non si semplifica e non si compone.** Proporre una bozza di risposta a una
  email di phishing è il peggior fallimento possibile di questo prodotto.
- **L'ordine degli agenti è fisso.** Niente routing dinamico «intelligente»: sarebbe
  imprevedibilità travestita da flessibilità, su un dominio dove l'errore costa a una persona di
  74 anni.
- **L'orchestratore non ha il diritto di restituire un errore all'interfaccia.** Al minimo, Maria
  vede l'email originale.
- **Le regole di non-chiamata di [`routing.md`](../../runtime/routing.md) §3 si valutano prima
  della seam**, non dopo. Una chiamata evitata costa zero token e zero latenza.
- **Porta 8123**, non 8000. `--reload` spento durante la demo.
- **Nessuna dipendenza nuova.** Le librerie sono congelate: fastapi, uvicorn, pydantic, pytest,
  httpx. `httpx` serve solo al `TestClient`.
- **Zero codice di rete in `app/`**, incluse le route: nessun client HTTP uscente.
- File scritti **solo in UTF-8**.

## Fallback

| Situazione | Azione |
|---|---|
| Un agente va in timeout o solleva un'eccezione | Si applica il fallback dichiarato nel suo file di `runtime/`, si traccia `esito: "errore"`, la pipeline **prosegue** |
| Il ciclo di semplificazione esaurisce i due retry | `semplificazione_mostrata = False`, originale con i fatti evidenziati. Non esiste un terzo tentativo |
| Budget token dell'email esaurito (`> 4000`) | Le seam restanti girano a regole. La pipeline non si interrompe mai per budget |
| Il checkpoint su disco è corrotto | Si ignora e si ricalcola da zero |
| Serve un campo che `contracts.py` non ha | **Non si modifica il file.** Richiesta al `team-leader` → `dev-core`. Nel frattempo si lavora con quello che c'è |
| Il tempo di fase sfora | Si taglia il compositore a **due** intenti (`conferma`, `non_posso`) e si stabilizza il percorso di Maria. Il punto di non ritorno è T+2:20 |
| Lo stesso task fallisce due volte | Si escala al `team-leader`, senza terza iterazione |

## Definizione di "fatto"

- [ ] `uvicorn app.backend.main:app --port 8123` parte e `http://localhost:8123` serve la pagina.
- [ ] `GET /api/emails` restituisce le 6 email con categoria, priorità e semaforo.
- [ ] `POST /api/email/{id}/elabora` restituisce un `RisultatoPipeline` valido per tutte e sei.
- [ ] `POST /api/email/{id}/elabora?avvelena=true` sull'email INPS produce
      `semplificazione_mostrata: false` e un problema di tipo `alterato`.
- [ ] Le route `/api` rispondono **anche** dopo il mount di StaticFiles.
- [ ] Ogni `EsitoSicurezza` ha una `azione` con `tipo != "nessuna"` quando il semaforo è rosso o giallo.
- [ ] Su semaforo rosso non ci sono bozze in `RisultatoPipeline.bozze`.
- [ ] Esiste `app/backend/state/data/<id>.json` dopo la prima elaborazione, e la seconda chiamata
      lo riusa senza ri-eseguire.
- [ ] Nessun percorso restituisce 500: le sei email girano anche con la rete staccata, in `off` e
      in `replay`.
- [ ] Nessun file di `dev-core` risulta modificato (`git diff --stat` pulito su `contracts.py`,
      `clock.py`, `llm/`, `verificatore.py`).
