# CLAUDE.md — regole di progetto non negoziabili

> Questo file è la **fonte canonica** delle regole tecniche di Posta Chiara. Ogni agente di
> `build-time/` lo legge prima di scrivere la prima riga, e il `team-leader` lo fa rispettare
> rifiutando le deleghe che lo violano.
>
> Le regole qui sotto non sono preferenze di stile: ciascuna corrisponde a un modo concreto in cui
> questa build può fallire in quattro ore. Sono scritte all'imperativo perché sotto pressione una
> regola sfumata non regge.

Ordine, gate e parallelismi stanno altrove: [`../workflow.md`](../workflow.md).
Confini di file di ogni agente: [`../README.md` §3](../README.md).

---

## 1 · Dipendenze — congelate

Le dipendenze sono **fastapi, uvicorn, pydantic, pytest, httpx**, congelate a T+0:15.

- **Nessun `pip install` dopo quel momento.** Una dipendenza con estensione C senza wheel per la
  versione di Python in uso significa build da sorgente su Windows, cioè un buco nero di tempo
  senza fondo e senza preavviso.
- `httpx` esiste **solo** per il `TestClient` di Starlette. Non è un client HTTP del progetto.
- **`dateparser` è vietato.** È esattamente la libreria che un agente cercherà per primo per le
  date italiane. Le date italiane si fanno a mano in `app/backend/engines/normalize.py`: è una
  dipendenza pesante che introdurrebbe comportamenti non deterministici proprio dove serve il
  contrario.
- Un agente che propone un pacchetto riceve un **rifiuto secco**: si risolve con la libreria
  standard, oppure si riduce lo scope.

## 2 · Zero codice di rete in `app/`

- Nessun `import anthropic`, nessun `requests`, nessun `urllib` di rete, nessun `httpx.post`
  fuori da `app/tests/`. Non è disattivato: **non esiste**.
- `app/tests/test_llm_modes.py` lo verifica **leggendo staticamente i sorgenti**. È la garanzia
  tecnica detta alla giuria, resa eseguibile.
- Se un agente lo aggiunge «per completezza», si rimuove. Non si discute.

## 3 · La seam LLM ha due modalità, non tre

| `LLM_MODE` | Comportamento |
|---|---|
| `off` *(default)* | La seam non viene attraversata: solo motori deterministici |
| `replay` | La seam viene attraversata **per intero** e la risposta è letta da `app/fixtures/llm/` |

- **Non si aggiunge una modalità `live`.** Non c'è trasporto, non c'è dipendenza, non c'è chiave.
- Le fixture contengono **solo** `model`, `content`, `usage`. Nessun header, nessun campo di
  autenticazione.
- ★ **Le fixture sono output di esempio scritti a mano in fase di sviluppo, conformi agli schema.
  Non sono registrazioni di chiamate API.** La parola «registrate» non deve comparire riferita
  alle fixture in nessun file consegnato: README, `docs/`, `agents/`, presentazione, note del
  presentatore. Detta da noi, la formulazione onesta è la posizione più forte; scoperta da altri,
  sarebbe una bugia che travolge tutto il resto.
- Fixture mancante in `replay`: **fallback a regole + log rumoroso** in esecuzione, **errore
  secco** nei test. Silenzio mai.

## 4 · Segreti

- **Non esiste una chiave API in questo progetto**: non nel repository, non nella cronologia git,
  non sulla macchina di sviluppo. Non è una precauzione, è un fatto verificabile.
- `.env` in `.gitignore` **dal primissimo commit**, prima che esista qualcosa da proteggere.
  Rimediare dopo è troppo tardi: la cronologia git resta.
- `.env.example` sì, committato.
- Prima del passaggio a repository pubblica: `git log -p | Select-String "sk-ant-"` deve essere
  **vuoto**. Lo verifica [`review/bando-compliance.md`](review/bando-compliance.md).

## 5 · Codifica dei file

- **UTF-8, sempre.** File scritti **solo** con lo strumento Write o con Python
  `encoding='utf-8'`.
- ★ **Mai `Set-Content` di PowerShell 5.1:** scrive in ANSI per default e manda in mojibake tutti
  gli accenti italiani e il simbolo dell'euro. Un corpus generato via shell è un corpus da
  riscrivere.
- L'HTML dichiara `<meta charset="utf-8">`; l'`<html>` dichiara `lang="it"`.

## 6 · Applicazione web

- **Porta 8123**, non 8000: entrambe sono libere, ma la 8000 attira strumenti aziendali.
- **`StaticFiles` si monta per ultimo**, dopo tutte le route `/api`, su `/` con `html=True`.
  Montato per primo le inghiotte, e il sintomo — `404` su `/api` con la pagina che funziona — fa
  perdere venti minuti.
- **`Cache-Control: no-store`** in sviluppo, o si debuga JavaScript già corretto ma cachato.
- **`--reload` spento durante la demo.**
- **Nessuna CDN**, nessun font remoto, nessuna libreria scaricata a runtime: la demo gira con la
  rete staccata, e lo si prova davvero staccandola.
- **Nessuno step di build** per il frontend: `node` non è installato, e installarlo a metà
  hackathon non è un'opzione.

## 7 · Il tempo

- **«Oggi» è una costante iniettabile**: `app/backend/clock.py`, `OGGI_DEFAULT = date(2026,10,6)`,
  sovrascrivibile con la variabile d'ambiente `POSTA_CHIARA_OGGI` in formato ISO.
- **`date.today()` è vietato in `app/`.** Senza un orologio fermo le scadenze del corpus scadono
  da sole e i test diventano non deterministici nel giro di qualche giorno.

## 8 · Confini e proprietà

- **Due agenti non toccano mai lo stesso file.** È la condizione che rende possibile il
  parallelismo, non una linea guida.
- Il proprietario di un file è quello dichiarato in [`../README.md` §3](../README.md). Serve
  qualcosa in un file altrui? Si chiede al `team-leader`, che delega al proprietario. Non si
  modifica «solo una riga».
- **I contratti in `app/backend/contracts.py` si consumano, non si modificano**, dopo l'handoff di
  `dev-core`.
- **I file del bando in `Downloads/hagenthon/` sono di sola lettura assoluta.**

## 9 · Limiti di iterazione

- Un agente che fallisce **due volte** sullo stesso task non riprova una terza: escala al
  `team-leader` con lo scope minimo ancora dimostrabile.
- Il leader che non sa decidere escala alla persona. Non improvvisa.
- **Feature freeze a T+2:30.** Dopo, solo correzioni di bug e documentazione.

## 10 · Il prodotto

- **Nessun invio automatico. Mai, in nessun caso.** Il sistema produce bozze; l'ultimo click è
  sempre umano.
- **Nessun verdetto senza azione.** Un semaforo senza un pulsante che dice cosa fare è un checker
  travestito da assistente.
- **Nessun testo semplificato raggiunge l'interfaccia senza essere passato da FactGuard.**
  Verificatore indisponibile o in errore → si mostra l'originale.
- **Il verificatore non è e non sarà mai un LLM.** Il controllo non può appartenere alla stessa
  classe di strumento di ciò che controlla.
- **Lo scope di FactGuard non si allarga:** solo date, importi e orari, ciascuno ancorato a una
  parola chiave entro 40 caratteri. Mai protocolli, IBAN, codici fiscali, civici, CAP, telefoni.
- **La pipeline non restituisce mai un errore all'interfaccia.** Al minimo, Maria vede l'email
  originale.
