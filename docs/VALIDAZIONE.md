# Validazione — l'evidenza

> Evidenza di validazione richiesta dalla consegna, punto 03. Tre prove indipendenti: **test automatici**, **checklist di accessibilità**, **confronto prima / dopo misurato**.

---

## 1. Test automatici

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

| Ambiente | Comando | Risultato |
|---|---|---|
| **Clone pulito**, sole dipendenze di `requirements.txt` | `python -m pytest -q` | **69 passati · 1 saltato** |
| Macchina di sviluppo, con Playwright installato | `python -m pytest -q` | **94 passati · 0 saltati** |
| Sola suite principale, Playwright escluso a mano | `python -m pytest -q --ignore=app/tests/test_e2e_frontend.py` | **69 passati** |

Il saltato del primo caso è la suite end-to-end del browser (`app/tests/test_e2e_frontend.py`): dipende da **Playwright**, che è una dipendenza facoltativa e **non è in `requirements.txt`**. Senza Playwright il modulo si salta invece di fallire, perché la suite principale non deve dipendere da un pacchetto opzionale. Con Playwright installato, quella suite avvia un `uvicorn` su `127.0.0.1` e percorre l'interfaccia in un Chromium vero: **13 test in più, tutti verdi**.

**Nessun test tocca la rete.** Non è una regola da rispettare: nel progetto non esiste codice capace di toccarla, e il primo test di `test_llm_modes.py` lo dimostra invece di assumerlo. La prova pratica è staccare il Wi-Fi e rilanciare: il risultato è identico, in `off` e in `replay`.

### Cosa copre ciascun file

I test sono scritti **dai contratti**, non dall'implementazione: `test-engineer` è partito insieme a `dev-core`, non dopo. Verificano quindi il comportamento **voluto**, non fotografano quello ottenuto.

| File | Cosa dimostra | I casi che contano |
|---|---|---|
| `test_normalize.py` | Che due scritture della stessa cosa siano **lo stesso valore** | `14/10/2026` ≡ `14-10-2026` ≡ `14 ottobre 2026`; `€ 1.234,50` ≡ `1.234,50 euro`; ★ **punto delle migliaia vs virgola decimale**; `9:30` → `09:30`; una data impossibile non è una data |
| `test_fact_extract.py` | Lo **scope rigido** di ciò che FactGuard protegge | Ancoraggio alla parola chiave; ★ **`Via Roma 15` non è un importo**; ★ **il CAP non è un importo**; ★ **la data di una citazione normativa (`D.P.R. 28 dicembre 2000`) non è un fatto**; zero fatti è un esito legittimo; deduplica per valore normalizzato |
| `test_verificatore.py` | **FactGuard** — il pezzo tecnico centrale, e il file con più test del progetto | Fatto preservato → passa; ★ **stessa data in formato diverso → accettata**; ★ **`1.247,83` → `1.247` → rifiutato**; orario alterato → rifiutato; data sparita → `mancante`, non `alterato`; importo inventato → segnalato; senza fatti la verifica passa; `feedback_per_retry` solo quando fallisce; l'espediente `avvelena` corrompe davvero |
| `test_phishing_rules.py` | Che il semaforo sia **spiegabile e prudente** | Dominio che imita un ente → rosso; link mascherato → rosso; ★ **l'email che dichiara «l'Istituto non richiede mai le credenziali» NON viene segnalata**; richiesta esplicita di credenziali → rossa; in rubrica → verde; ★ **sconosciuto innocuo → giallo, mai verde**; ★ **il numero suggerito viene dalla tabella statica, mai dall'email** |
| `test_orchestrator.py` | Ordine, **limiti** e stato | Pipeline completa sul corpus; semaforo rosso → nessuna bozza; ★ **limite di tentativi rispettato**; ★ **un agente in errore non uccide la pipeline**; stato persistito e riletto dal checkpoint; `avvelena` fa rifiutare la semplificazione; ogni risultato porta le tracce |
| `test_compositore.py` | Che la risposta si **scelga**, e che non parta da sola | I tre intenti sono sempre proposti; ★ **senza fatti non inventa data né orario**; ★ **nessun invio automatico** |
| `test_llm_modes.py` | La garanzia **«zero rete»**, resa eseguibile | ★ **test statico sull'AST di ogni sorgente di `app/`: nessun import di `anthropic`/`requests`/`urllib.request`/`http.client`/`httpx`, nessuna chiamata su quelle radici**; `off` → seam non attraversata, 0 token; `replay` con fixture mancante → degrada alle regole senza fermare la pipeline; il prompt viene letto **davvero** da `agents/runtime/prompts/` |
| `test_contracts_sync.py` | Che `agents/` non racconti un sistema che non esiste più | Ogni modello Pydantic ha il suo JSON Schema pubblicato, e gli schema sono **allineati** ai modelli. Se un contratto cambia e lo schema no, la suite diventa rossa |
| `test_gulpease.py` | La metrica su cui poggia il §3 di questo documento | La formula `89 + (300·frasi − 10·lettere)/parole` su un testo noto; testo vuoto → `0.0`, nessuna divisione per zero |
| `test_api.py` | Il contratto HTTP che il frontend consuma | `/api/salute` dichiara `chiave_api_richiesta: false`; la mailbox contiene sei email; `elabora` restituisce le tracce; email inesistente → `404`; **l'invio incrementa il contatore di autonomia** |
| `test_plain_rules.py` | Che il semplificatore **non legga al contrario** | ★ **«si prega di non rispondere» non diventa «Le chiedono di rispondere»**; una richiesta vera resta tale anche se altrove c'è un verbo negato; `«Cedolino pensione»` → `foglio della pensione`, non `foglio della pensione pensione` |
| `test_cartelle.py` | Le tre cartelle e lo stato **«già risposto»** | `gia_risposto` è **derivato** dalla tabella `invio`, non memorizzato: togliendo l'invio sparisce da solo; rispondere a un'email non segna le altre; ★ **eliminare sposta, non cancella** — l'email esiste ancora e si ripristina; la posta inviata eredita destinatario e oggetto dal messaggio originale; `Re:` non si accumula; cartella sconosciuta → `400` |
| `test_e2e_frontend.py` *(facoltativo)* | Che il percorso di Maria funzioni **in un browser vero** | La casella mostra sei email; ogni email riceve un semaforo; **percorso completo dal medico alla risposta inviata**; nessun invio senza un click; la truffa è rossa e non propone di rispondere; il nipote è verde; **il rifiuto dell'email avvelenata compare a schermo**; `lang="it"`; **target ≥ 44px**; **base ≥ 20px**; si apre un'email **con la sola tastiera**; il fuoco si sposta sulla vista di lettura; i cambi di stato passano da una regione `aria-live`; ★ **Maria non vede i pannelli tecnici**, la giuria sì con `?tecnico=1`; i comandi della voce esistono e sono ≥ 44px; ★ **la dettatura avvisa prima che la voce esca dal dispositivo, e si può rifiutare**; la barra di arresto compare solo mentre legge; le tre cartelle sono sempre visibili; **dopo l'invio l'email è marcata «già risposto», anche nel nome accessibile**; eliminare sposta nel cestino e si torna indietro |

> La suite non è stata gonfiata. È concentrata dove il rischio è reale — **FactGuard e orchestratore** — perché test superflui diventano test da riparare.

---

## 2. Checklist di accessibilità

Costruire uno strumento di accessibilità inaccessibile è la domanda letale della giuria. La checklist è [`../agents/build-time/commands/verifica-a11y.md`](../agents/build-time/commands/verifica-a11y.md): **27 voci a esito binario**, ciascuna con scritto **come** si misura, perché «sembra accessibile» non è una misura.

Esito sulle due schermate del prodotto (lista ed email aperta):

| Gruppo | Esito | Evidenza nel codice |
|---|---|---|
| **Struttura e semantica** (1–5) | ✅ | `lang="it"` sull'`<html>`; un solo `<h1>`; `<main>` presente; **zero `<div onclick>`** — ogni elemento cliccabile è un `<button>` vero, anche quelli generati in JavaScript; le voci della lista hanno un `aria-label` esplicito (*«mittente. oggetto. Apri per leggere.»*) |
| **Dimensioni e contrasto** (6–10) | ✅ con una nota | `--tocco: 48px` applicato a tutti i target interattivi (44 è il minimo, 48 lascia margine al tremore); `html { font-size: 20px }`; ogni token di colore porta **il rapporto di contrasto annotato nel foglio di stile** (`--inchiostro` 15.2:1, `--inchiostro-tenue` 9.1:1 — il grigio più chiaro ammesso); ★ **nessuna informazione affidata al solo colore**: il semaforo porta sempre una parola (*Può rispondere / Da controllare / Attenzione*) |
| **Tastiera e focus** (11–15) | ✅ | Link «Vai al contenuto» in cima; `:focus-visible { outline: 4px solid }`; il fuoco si sposta sul pulsante «Torna a tutte le email» quando cambia vista, con il commento che ne spiega il motivo; ★ **zero `tabindex` nel sorgente** — nessun ordine forzato a mano |
| **Interazione motoria** (16–20) | ✅ | Zero `dblclick`, zero `draggable`, zero `dragstart`; l'unica regola `:hover` del foglio di stile cambia il colore di un bordo e **nessun comportamento ne dipende**; nessuna azione a tempo, nessun elemento che scompare da solo |
| **Cambi di stato** (21–24) | ✅ | Tre regioni `aria-live="polite"` — contatore di autonomia, semaforo, conferma di invio — e **zero `assertive`**, che è corretto perché non c'è nessuna emergenza; il rifiuto di FactGuard è in un blocco `role="alert"`, quindi **annunciato, non solo colorato** |
| **Layout** (25–27) | ✅ | Colonna singola `max-width: 760px`; nessun menu a scomparsa, nessun contenuto dietro un'icona; `@media (prefers-reduced-motion: reduce)` disattiva animazioni e transizioni |

**La nota, per onestà.** Due valori restano da rimisurare **sul proiettore della demo**, non sul monitor di sviluppo:

- `--verde: #0d6b2f` è a 6.9:1 su bianco e a 8.4:1 sul proprio fondo tenue, che è dove viene effettivamente usato. È il valore più stretto della palette.
- La voce di lista in secondo piano (la newsletter) è resa con `opacity: 0.75`; il contrasto risultante resta sopra la soglia, ma è l'unico punto in cui è calcolato invece che dichiarato.

La checklist stessa prescrive di rifare la prova sulla macchina e sul proiettore della demo, perché «la verifica passa in locale ma non in proiezione» è uno dei suoi fallimenti tipici.

---

## 3. Prima / dopo, misurato — indice Gulpease

Il confronto prima/dopo è una delle prove di validazione ammesse, e qui è **un numero, non un'impressione**.

L'indice Gulpease è la metrica di leggibilità tarata sull'italiano: `89 + (300·frasi − 10·lettere) / parole`. Sopra **80** un testo è leggibile con la licenza elementare, sopra **60** con la licenza media. Maria ha la licenza media. L'implementazione è `app/backend/engines/gulpease.py`, l'indice è **visibile in interfaccia** accanto al testo, ed è esposto da `POST /api/email/{id}/elabora` nel campo `leggibilita`.

Misuriamo **tre testi, non due**, perché raccontano cose diverse: l'originale, il corpo riscritto, e il riassunto **Chi / Cosa / Entro quando** che è ciò che Maria legge per primo.

| Email | Originale | Corpo riscritto | **Riassunto** |
|---|---:|---:|---:|
| `em-01` dott.ssa Bianchi | 57.5 *difficile* | 60.7 *facile* | **90.1 *molto facile*** |
| `em-02` Comune di Torino | 64.7 *facile* | 61.5 *facile* | 68.0 *facile* |
| `em-04` INPS | 48.7 *difficile* | 49.7 *difficile* | 49.8 *difficile* |
| **media** | **57.0** | **57.3** | **69.3** |

Le altre tre email del corpus non vengono semplificate, e non è un buco: è il routing che funziona. `em-03` è rossa (su phishing non si semplifica), `em-05` è del nipote (76.0 di partenza: è già italiano semplice, semplificarla è spesa netta), `em-06` è pubblicità (va messa in secondo piano, non tradotta). Le regole di non-chiamata sono in [`../agents/runtime/routing.md`](../agents/runtime/routing.md) §3.

### Cosa dicono davvero questi numeri

**Il corpo riscritto guadagna pochissimo: 57.0 → 57.3, tre decimi.** Lo scriviamo perché è vero, e perché la ragione è interessante.

Un motore a regole **non può rifondere i periodi senza rischiare di storpiarli**, e non lo fa apposta: la versione che ci provava produceva *«all'domanda»* e tagliava un indirizzo in due (vedi [`PROCESSO-AI.md`](PROCESSO-AI.md) §3). Ciò che resta sicuro — cancellare frasi di pura formula, sostituire locuzioni intere — tocca il lessico e la lunghezza, cioè proprio le due leve su cui il Gulpease è meno sensibile.

Su `em-02` l'indice **scende**, 64.7 → 61.5, e vale la pena guardare perché:

| | Parole | Lettere | Frasi | Gulpease |
|---|---:|---:|---:|---:|
| Originale | 244 | 1254 | 22 | 64.7 |
| Riscritto | 150 | 742 | 11 | 61.5 |

Il testo è più corto del **39%** e ha perso 512 lettere di formule di rito — *«non necessita di sottoscrizione autografa»*, *«ai sensi e per gli effetti degli artt. 33 e 40 del D.P.R. …»* — eppure l'indice peggiora, perché Gulpease misura la **densità di frasi**, non la lunghezza del testo: eliminando frasi intere il numeratore cala insieme al testo. **È un artefatto della metrica, non un peggioramento della lettura.**

**Il guadagno vero è il riassunto: 57.0 → 69.3 di media, e 57.5 → 90.1 sull'email che conta**, quella del medico, l'unica che Maria deve davvero agire. Novanta è *molto facile*: leggibile con la licenza elementare. Ed è il testo che sta in cima alla schermata, prima di tutto il resto.

> Riportiamo entrambi i numeri perché sceglierne uno solo sarebbe una mezza verità. La motivazione è scritta anche nel codice, nel docstring di `_leggibilita` in `app/backend/main.py`: chi legge la funzione fra sei mesi deve trovarci la ragione, non solo il calcolo.

### L'anomalia di `em-04`, spiegata invece che nascosta

Il riassunto dell'INPS si ferma a **49.8**, molto sotto gli altri due. Non è un difetto di semplificazione: è la metrica che inciampa su un nome proprio.

Il riassunto è di **12 parole e 77 lettere**. Di queste, *«INPS - Istituto Nazionale Previdenza Sociale»* vale 5 parole e **38 lettere — il 49% del totale**. Gulpease penalizza pesantemente le parole lunghe, e qui la metà del testo è la ragione sociale dell'ente che scrive, che non si può abbreviare senza mentire su chi manda l'email.

È un **artefatto della metrica**, non un problema di leggibilità: nessuna persona fatica a leggere *«INPS - Istituto Nazionale Previdenza Sociale, un ufficio pubblico»*. Il numero resta visibile in interfaccia com'è, senza correzioni cosmetiche: una metrica che si aggiusta quando dà il risultato sbagliato smette di essere una metrica.

---

## 4. Riepilogo dell'evidenza

| Prova | Esito | Dove si rifà |
|---|---|---|
| Test automatici | **69 passati, 1 saltato** su un clone pulito · **94 passati** con Playwright installato | `python -m pytest -q` |
| Zero codice di rete in `app/` | ✅ verificato staticamente sull'AST di ogni sorgente | `pytest app/tests/test_llm_modes.py -q` |
| Contratti allineati agli schema pubblicati | ✅ | `pytest app/tests/test_contracts_sync.py -q` |
| Checklist accessibilità, 27 voci | ✅ su entrambe le schermate, due valori da rimisurare in proiezione | `agents/build-time/commands/verifica-a11y.md` |
| Confronto prima / dopo | ✅ misurato su 3 email, **+12.3 punti** di media sul riassunto | campo `leggibilita` di `POST /api/email/{id}/elabora` |
| Funzionamento a rete staccata | ✅ in `off` **e** in `replay` | si stacca il Wi-Fi e si rilancia |
| Il rifiuto di FactGuard dal vivo | ✅ | pulsante «E se l'AI sbaglia?» su `em-04` |
| Nessun invio automatico | ✅ endpoint separato, raggiungibile solo da un click | `test_nessun_invio_automatico` |
