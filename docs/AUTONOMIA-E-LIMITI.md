# Autonomia e limiti

> Deliverable 3. Cosa Maria guadagna davvero, e cosa il sistema **non** fa. I limiti qui sotto sono dichiarati per primi da noi: taciuti, costerebbero la fiducia su tutto il resto.

---

## 1. Cosa guadagna

| Guadagno | Prima | Dove è implementato |
|---|---|---|
| **Capire una comunicazione di un ente** senza chiamare il nipote | *«Ai sensi e per gli effetti degli artt. 33 e 40 del D.P.R. …»* | Agente 04 + `engines/plain_rules.py`. Il valore vero sta nel riassunto **Chi / Cosa / Entro quando** |
| **Rispondere a un appuntamento** | Riquadro bianco → chiude tutto → aspetta domenica | Agente 06: tre intenti, bozza già compilata coi fatti verificati |
| **Distinguere una truffa da una comunicazione vera** | `em-03` e `em-04` dicono entrambe *soldi* e *urgente* | Agente 02 + `engines/phishing_rules.py`, **regole spiegabili in italiano**, mai una probabilità |
| **Sapere che c'è un allegato, e quale** | Invisibile nell'interfaccia di partenza | Scheda «Documenti allegati» con nome e dimensione |
| **Un numero al posto di un'impressione** | — | Contatore «Risposte inviate da sola», alimentato solo da invii reali (`GET /api/autonomia`) |

**Semplificato senza tradire.** Date, importi e orari sono verificati **verbatim sui valori normalizzati** da FactGuard; l'originale è sempre a un tocco; **nessuna semplificazione non verificata raggiunge l'interfaccia**. Se il controllo fallisce, Maria vede il testo esattamente come l'ente l'ha scritto — che è un esito peggiore, ma mai un esito falso.

---

## 2. I limiti che restano

### ★ FactGuard verifica la *presenza* dei fatti, non il loro *ruolo*

È il limite più importante, ed è intrinseco a un verificatore sintattico.

`verificatore.py` confronta insiemi di valori normalizzati. Vede che `1247.83` c'è nell'originale e c'è nel semplificato, e passa. **Non distingue «importo dovuto» da «importo già versato».** Una riscrittura che invertisse il senso della frase conservando il numero supererebbe il controllo.

Non è un compromesso dovuto al tempo: riconoscere il ruolo semantico di un numero richiederebbe comprensione del testo, cioè esattamente lo strumento che non può fare il controllo (vedi [`../agents/runtime/routing.md`](../agents/runtime/routing.md) §1, punto 3).

**Mitigazione:** è il punto in cui serve la revisione umana, ed è il motivo per cui il pulsante «Mostra il testo originale» è sempre presente, su ogni email, senza eccezioni.

### La classificazione delle truffe non è infallibile

Le regole di `phishing_rules.py` coprono i pattern ricorrenti — dominio che imita un ente noto, link mascherato, richiesta esplicita di credenziali, lessico d'urgenza. Una truffa scritta bene, da un dominio mai visto, senza fretta e senza link, riceverebbe il **giallo**.

Per questo la soglia è **deliberatamente prudenziale**:

- Uno sconosciuto innocuo è **giallo, mai verde**. Il verde è riservato a chi è in rubrica o a un dominio istituzionale verificato senza segnali negativi.
- Il fallback del controllo, se l'agente va in errore, è **giallo**: un controllo che non è riuscito non è un controllo superato.
- Il sistema dice *«può rispondere»*, che è un'affermazione sull'azione. **Non dice mai «è sicura»**, che sarebbe una garanzia sul mittente.
- Sul giallo l'azione è *«Chieda a Guada prima di rispondere»*: l'escalation a una persona di fiducia è un esito **legittimo**, non un errore del sistema.

Il costo di un falso verde (Maria si fida di una truffa) non è paragonabile al costo di un falso giallo (Maria chiede al nipote). La soglia è tarata su quell'asimmetria.

### Non fa un elenco di cose

| Fuori scope | Perché |
|---|---|
| **PEC** | Ha valore legale e regole di ricevuta proprie. Sbagliarne la gestione produce un danno giuridico, non un fastidio |
| **SPID / CIE** | Richiederebbe di maneggiare credenziali d'identità. Un prodotto che insegna a una persona anziana a inserire lo SPID dentro un'applicazione di terzi lavora **contro** il proprio messaggio sulla sicurezza |
| **Compilazione di moduli** | Fuori scope: il prodotto porta al testo di risposta, non a un procedimento amministrativo |
| **Pagamenti** | Nessuna operazione dispositiva, in nessuna forma |
| **Contenuti clinici, fiscali, legali** | ★ **Il sistema dice cosa c'è scritto, non cosa fare.** *«Deve fare le analisi a digiuno»* viene riportato se c'è scritto; non viene spiegato, completato o interpretato. Vale sia per il motore a regole sia per il prompt della seam (`agents/runtime/prompts/semplificatore.md`, regola 3) |

### Il semplificatore è a regole: copre il burocratese ricorrente, non il testo libero

`plain_rules.py` lavora su due livelli, entrambi sicuri: cancella **frasi intere** di pura formula e sostituisce **locuzioni autonome per intero**, articolo compreso. Ciò che non rientra in questi due casi **resta com'è**.

Conseguenza onesta: copre bene convocazioni, scadenze, certificati e comunicazioni di ente — cioè quello che arriva davvero nella casella di Maria — e **non** copre testo libero arbitrario. Il guadagno di leggibilità sul corpo riscritto è modesto e misurato: vedi [`VALIDAZIONE.md`](VALIDAZIONE.md) §3.

Allargarlo è esattamente ciò per cui esiste la seam LLM sull'agente 04, ed è l'unico punto del sistema dove un modello linguistico è giustificato — perché è l'unico il cui errore è **rilevabile a valle** da FactGuard.

### ★ Le fixture di `replay` sono scritte in sviluppo, non sono registrazioni di chiamate API

> Sono **output di esempio scritti durante lo sviluppo**, conformi agli schema in `agents/runtime/contracts/`. **Non sono registrazioni di chiamate API.** Il progetto non ha mai usato una chiave.

Cosa dimostrano: che la seam è **completa** — prompt caricato dal file, variabili sostituite, hash calcolato, JSON interpretato, output validato con Pydantic, token contati, e **FactGuard che verifica un testo che il codice non ha prodotto lui**.

Cosa **non** dimostrano: come si comporterebbe un modello reale su questo compito. Sul tasso di successo del semplificatore LLM su burocratese italiano vero, questo progetto non ha dati.

### Lo stato si azzera al riavvio

Il database è **SQLite in memoria** (`app/backend/db.py`). Scelto perché dà in memoria, senza file e senza dipendenze aggiuntive, le stesse proprietà di un database vero, interrogabile in SQL.

Conseguenza: i checkpoint della pipeline e il contatore di autonomia **vivono quanto il processo**. La ripartenza da checkpoint funziona entro la vita del processo, non fra un riavvio e l'altro. È un limite del prototipo, dichiarato anche nel docstring di `state/store.py`, e si risolve con una riga di configurazione (un file al posto di `:memory:`) il giorno in cui serve persistenza vera.

### Casella simulata, nessun IMAP reale

Le sei email vengono da `app/backend/data/mailbox.json` e sono **dichiaratamente fittizie**: mittenti inventati, protocolli inventati, nessun dato personale reale. L'integrazione con Gmail o con un server IMAP non è nello scope, e l'invio è registrato nel database locale — **nessun messaggio lascia la macchina**, in nessuna modalità.

### Privacy — la cosa da dire per primi

È posta **sanitaria e previdenziale** di una persona anziana.

**Oggi nulla esce dal dispositivo.** Non per configurazione, ma perché nel progetto non esiste codice capace di farlo uscire: nessun import di rete in `app/`, verificato staticamente da `test_llm_modes.py`.

Attivando davvero un trasporto LLM, il testo di quelle email verrebbe inviato a un modello remoto. Servirebbero un consenso esplicito e informato, oppure un modello locale. **Non è un dettaglio implementativo: è una decisione di prodotto che oggi non è stata presa**, e il default deterministico è il modo di non prenderla di nascosto.

---

## 3. Rischio residuo, in una riga

| Rischio | Chi lo assorbe |
|---|---|
| Un numero conservato ma con il senso ribaltato | La revisione umana: l'originale è sempre a un tocco |
| Una truffa sofisticata classificata gialla | La persona di fiducia: il giallo **è** l'escalation |
| Una bozza che non dice quello che Maria voleva | Maria: la rilegge e può modificarla prima di inviare |
| Un guasto di qualsiasi agente | La pipeline: degrada, non si ferma. Al minimo Maria vede l'email originale |

> **Il motore propone, il verificatore controlla, la persona decide.** L'ultima parola non è mai del sistema — e questo non è un limite, è il progetto.
