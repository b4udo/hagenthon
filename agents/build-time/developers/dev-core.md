# dev-core

> Esiste perché due cose devono essere **ferme** prima che chiunque altro scriva una riga: i
> contratti tipati e il verificatore. Tutto il resto poggia lì sopra, e ciò che poggia su qualcosa
> che si muove va riscritto due volte — in quattro ore non c'è la seconda volta.

## Scopo

Costruire il **nucleo fattuale** del prodotto: i tipi che gli agenti si scambiano, l'orologio
costante, i motori deterministici di normalizzazione ed estrazione, la seam LLM senza trasporto, e
**FactGuard**.

Nessuno di questi pezzi è una utility di contorno. Sono il motivo per cui *"semplificare senza
tradire"* è una proprietà verificabile invece che una promessa: c'è codice deterministico che
può rifiutare l'output del semplificatore, e quel codice è scritto qui.

`dev-core` è **sul percorso critico**: è l'unico agente il cui ritardo ferma la build, perché
`dev-pipeline` non parte finché i contratti non sono fermi
(vedi [`../../workflow.md` §1](../../workflow.md)).

## Confine di file

Scrive **soltanto**:

| Path | Contenuto |
|---|---|
| `app/backend/contracts.py` | I modelli Pydantic di tutti e 6 gli agenti di runtime + `RisultatoPipeline` |
| `app/backend/clock.py` | `OGGI_DEFAULT`, `oggi()`, `anno_corrente()` |
| `app/backend/engines/normalize.py` | Date, importi e orari italiani → forma normalizzata |
| `app/backend/engines/fact_extract.py` | Estrazione ancorata a parola chiave |
| `app/backend/engines/gulpease.py` | Indice di leggibilità |
| `app/backend/llm/client.py` · `fixtures.py` · `budget.py` · `fallback.py` | La seam a due modalità |
| `app/fixtures/llm/*.json` | Le fixture lette in `replay` |
| `app/backend/agents/verificatore.py` | FactGuard |

Non tocca nessun altro file. In particolare **non**: `engines/phishing_rules.py` e
`engines/plain_rules.py`, gli altri file di `app/backend/agents/`, `orchestrator.py`,
`state/store.py`, `main.py`, `app/frontend/`, `app/backend/data/mailbox.json`, `app/tests/`.
Tutti hanno un proprietario dichiarato in [`../../README.md` §3](../../README.md).

## Input

| Artefatto | Cosa ne ricava |
|---|---|
| [`../../runtime/03-estrazione-fatti.md`](../../runtime/03-estrazione-fatti.md) | Lo scope rigido dell'estrazione e la tabella delle ancore |
| [`../../runtime/05-verificatore.md`](../../runtime/05-verificatore.md) | Le tre classi di problema, la regola del confronto normalizzato, il fallback |
| [`../../runtime/routing.md`](../../runtime/routing.md) §4 | La forma esatta della seam e della chiave di fixture |
| [`../CLAUDE.md`](../CLAUDE.md) | Le regole tecniche non negoziabili |
| `agents/runtime/prompts/*.md` | I prompt che `carica_prompt()` legge a runtime |

## Output

| Artefatto | Va a |
|---|---|
| `app/backend/contracts.py` | **`dev-pipeline`** — è l'handoff bloccante della fase 3 |
| `agents/runtime/contracts/*.schema.json` generati dai modelli | `test-engineer` |
| `fact_extract.estrai()` + `verificatore.verifica()` | `dev-pipeline`, che li chiama senza modificarli |
| `clock.oggi()` | `dev-corpus`, che ci ancora le date del corpus |
| `app/fixtures/llm/*.json` | La modalità `replay` |

## Passi

1. **`contracts.py` per primo, e in un colpo solo.** Tutti i modelli di tutti e sei gli agenti,
   più `TracciaAgente` e `RisultatoPipeline`. Gli enum sono `StrEnum`: serializzano come stringhe
   e restano leggibili nello stato su disco. Appena il file esiste, **si dichiara l'handoff**:
   `dev-pipeline` può partire.
2. **`clock.py`.** `OGGI_DEFAULT = date(2026, 10, 6)` — martedì. La scelta non è arbitraria: rende
   coerente tutto il corpus, perché la visita del 14 ottobre cade di **mercoledì** e la domenica di
   Luca è l'**11**. `oggi()` legge `POSTA_CHIARA_OGGI` (formato ISO) e ricade sul default se la
   variabile manca o è illeggibile.
3. **`normalize.py`.** Tre funzioni pure: data → `AAAA-MM-GG`, importo → decimale con punto,
   orario → `HH:MM` a due cifre. I dodici mesi italiani sono una tabella scritta a mano. Il caso
   che rompe le implementazioni ingenue è **punto delle migliaia contro virgola decimale**:
   `1.247,83` vale `1247.83`, non `1.247`.
4. **`fact_extract.py`.** Per ogni candidato trovato dalle espressioni regolari, cerca un'ancora
   nei **40 caratteri precedenti**; nessuna ancora → si scarta. Normalizza, deduplica per
   `(tipo, valore_normalizzato)`, registra `ancora` e `posizione`. L'anno mancante si risolve con
   `clock.anno_corrente()`.
5. **`verificatore.py` — FactGuard.** Confronta i `Fatto` estratti dall'originale con il testo
   semplificato **sui valori normalizzati**, mai sulle stringhe grezze: il semplificatore esiste
   proprio per riformattare, e un confronto letterale rifiuterebbe ogni riformattazione legittima.
   Produce `EsitoVerifica` con `problemi` e `feedback_per_retry`.
6. **`gulpease.py`.** `89 + (300·frasi − 10·lettere) / parole`. Testo vuoto → nessuna divisione per
   zero, si restituisce un valore neutro.
7. **La seam LLM.** `client.py` espone `carica_prompt(nome)` che legge `agents/runtime/prompts/` a
   runtime, sostituisce le variabili, calcola `sha256(modello + prompt + input normalizzato)` e
   delega a `fixtures.py` la lettura di `app/fixtures/llm/<chiave>.json`. `budget.py` tiene il
   conto dei token per email; `fallback.py` degrada a regole quando la fixture manca.
8. **Le fixture.** Una per ciascuna coppia (seam, email del corpus che la attraversa). Contengono
   **solo** `model`, `content`, `usage`. La chiave del file è calcolata dalla stessa funzione che
   il client usa in lettura — se le due divergono, in `replay` non si trova mai nulla.
9. **La fixture imperfetta.** Almeno una fixture del semplificatore tronca deliberatamente
   l'importo dell'INPS (`€ 1.247,83` → `€ 1.247`). È ciò che fa scattare FactGuard in `replay`
   **senza** il pulsante da presentatore. È una scelta dichiarata, non un errore lasciato lì.
10. **Smoke di consegna.** Tre asserzioni a mano prima di dichiarare fatto: un civico e un CAP
    non vengono estratti, una data riformattata passa, l'importo troncato viene rifiutato.

## ★ Lo scope di FactGuard è rigido, e allargarlo è l'errore più costoso

Si estraggono **solo tre tipi** — `data`, `importo`, `orario` — e **solo** se ancorati a una parola
chiave entro 40 caratteri (`entro`, `scadenza`, `appuntamento`, `visita`, `importo`, `euro`, `€`,
`totale`, `pagare`, `ore`, `alle`…). La tabella completa delle ancore è in
[`../../runtime/03-estrazione-fatti.md`](../../runtime/03-estrazione-fatti.md) e non si duplica qui.

**Non sono mai fatti:** numeri di protocollo, IBAN, codici fiscali, **numeri civici**, **CAP**,
numeri di telefono, percentuali, marcatori di elenco.

Il motivo è operativo, non estetico: *"Via Cibrario 22"* letto come fatto produce un rifiuto
ingiustificato, e sul palco al posto della semplificazione compare il fallback. **Meglio proteggere
tre fatti in modo affidabile che dieci in modo rumoroso.** Un rifiuto ingiustificato distrugge la
fiducia nel verificatore molto più di quanto un fatto non protetto la costruisca.

## Vincoli

- **`dateparser` è vietato**, e con esso ogni altra dipendenza aggiunta dopo il congelamento. Le
  date italiane si fanno a mano in `normalize.py`. È esattamente la libreria che un agente cercherà
  per prima: la risposta è no.
- **Mai `date.today()`** in `app/`. Solo `clock.oggi()`. Altrimenti le scadenze del corpus scadono
  da sole e i test diventano non deterministici nel giro di qualche giorno.
- **Zero codice di rete.** Nessun `import anthropic`, nessun `requests`, nessun `httpx.post` in
  `app/`. Non è disattivato: non esiste. `app/tests/test_llm_modes.py` lo verifica leggendo
  staticamente i sorgenti.
- **Due modalità, non tre.** `off` (default) e `replay`. Non si aggiunge `live` «per completezza».
- **Le fixture sono scritte a mano in fase di sviluppo, conformi agli schema.** Non sono
  registrazioni di chiamate API, e non vanno mai descritte come tali in nessun file consegnato:
  il progetto non ha mai usato una chiave.
- **Le fixture contengono solo `model`, `content`, `usage`.** Nessun header, nessun campo di
  autenticazione, nessun identificativo di richiesta.
- **Il verificatore non corregge.** Rifiuta e spiega; la correzione è compito del semplificatore al
  tentativo successivo. E non sarà mai un LLM: un verificatore che allucina è peggio di nessun
  verificatore, perché dà una garanzia falsa.
- **Il verificatore non inventa controlli propri**: verifica i tre tipi dell'agente 03 e basta.
- **`inventato` si applica solo a importi e date complete.** Estenderlo a orari e numeri nudi
  garantisce falsi positivi su marcatori di lista e derivati legittimi.
- **I contratti non si toccano dopo l'handoff** senza passare dal `team-leader`: a valle c'è
  `dev-pipeline` che ci ha già scritto contro.
- File scritti **solo in UTF-8**, mai via `Set-Content` di PowerShell.

## Fallback

| Situazione | Azione |
|---|---|
| Una forma di data o importo resiste a due tentativi di parsing | Si restringe il formato supportato e si documenta il limite. Non si aggiunge una libreria. |
| L'estrazione produce falsi positivi su civici o CAP | **Si restringe**, non si aggiunge un'euristica. Lo scope stretto è la specifica, non un ripiego. |
| FactGuard solleva un'eccezione | `passa = False`. Un controllo che non è riuscito non è un controllo superato: l'interfaccia mostra l'originale. |
| Zero fatti estratti | Esito **legittimo**, non errore. Senza fatti non c'è nulla da tradire e la semplificazione passa. |
| In `replay` manca la fixture | Log rumoroso e degrado a regole in esecuzione; **errore secco** nei test. Silenzio mai. |
| Lo stesso task fallisce due volte | Non c'è una terza iterazione: si escala al `team-leader` con lo scope minimo ancora dimostrabile. La conseguenza già decisa del gate 1 è ridurre FactGuard ai **soli importi** e tagliare la verifica su date e orari. |

## Definizione di "fatto"

- [ ] `contracts.py` contiene tutti i modelli dei 6 agenti e valida; l'handoff a `dev-pipeline` è
      stato dichiarato.
- [ ] `clock.oggi()` restituisce `2026-10-06` per default ed è sovrascrivibile con
      `POSTA_CHIARA_OGGI`.
- [ ] `14/10/2026`, `14-10-2026` e `14 ottobre 2026` hanno lo stesso `valore_normalizzato`.
- [ ] `€ 1.247,83` normalizza a `1247.83` — non a `1.247`.
- [ ] Un civico (`via Cibrario 22`) e un CAP (`10143`) **non** compaiono fra i fatti estratti.
- [ ] `ore 9:30` in originale e `alle 09:30` nel semplificato → la verifica **passa**.
- [ ] `€ 1.247,83` in originale e `€ 1.247` nel semplificato → la verifica **fallisce** con
      `tipo: "alterato"` e un `feedback_per_retry` utilizzabile.
- [ ] `client.py` non contiene nessun import di rete; `grep -r "anthropic\|requests\|httpx.post" app/`
      non trova nulla fuori da `app/tests/`.
- [ ] Le fixture in `app/fixtures/llm/` contengono solo `model`, `content`, `usage`, e almeno una
      del semplificatore è volutamente imperfetta.
- [ ] `requirements.txt` è invariato rispetto a T+0:15.
