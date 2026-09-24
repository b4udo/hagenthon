# Processo — come l'AI è stata usata per costruire questo progetto

> Nota sul processo richiesta dalla consegna: come abbiamo usato l'AI, quali output sono stati rivisti o corretti da una persona, quali decisioni tecniche sono state prese.

Il racconto in una riga: **abbiamo scritto prima gli agenti, poi gli agenti hanno scritto l'app.**

---

## 1. Il team di build — 9 agenti, confini disgiunti

Lo sviluppatore è **uno**. I sotto-agenti sostituiscono la seconda persona, e la regola che rende fattibili quattro ore è una sola:

> **Due agenti non toccano mai lo stesso file.**

Non è una linea guida: è la condizione del parallelismo. Ogni agente ha un **confine di file dichiarato**, i confini sono disgiunti, e il `team-leader` rifiuta qualsiasi delega che ne violi uno.

La tabella completa dei nove agenti con confine e specifica è in [`../agents/README.md`](../agents/README.md) §3; ordine, handoff e parallelismi in [`../agents/workflow.md`](../agents/workflow.md). Qui interessa **perché** la divisione è quella:

| Agente | La ragione per cui esiste separato |
|---|---|
| **team-leader** | Un solo posto possiede l'ordine, i gate e il freeze. Non scrive codice di produzione: nemmeno una riga, nemmeno «per sbloccare» |
| **dev-core** | Il percorso critico — contratti, normalizzazione, estrazione fatti, **FactGuard**, la seam LLM. È l'unico pezzo che può far saltare il progetto, e viene per primo |
| **dev-pipeline** | **Consuma** i contratti di dev-core, non li modifica. Un consumatore che può cambiare il contratto smette di essere un consumatore |
| **dev-frontend** | Accessibilità e interazione hanno vincoli propri (≥44px, contrasto 7:1, `aria-live`) che un agente backend ignora, non per incapacità ma perché non sono nel suo contesto |
| **dev-corpus** | Le sei email in burocratese realistico sono ciò su cui vive la demo. Scrivere corpus e scrivere codice sono due mestieri e due contesti diversi |
| **dev-deck** | Parte a T+1:00 in parallelo, così il deck non nasce negli ultimi venti minuti. Non tocca codice, quindi non collide mai |
| **test-engineer** | Scrive i test **dai contratti**, non dall'implementazione. Parte insieme a dev-core, non dopo: così i test verificano il comportamento **voluto**, non fotografano quello ottenuto |
| **qa-critic** | ★ **Sola lettura su `app/`.** Un tester che può riscrivere ciò che testa finisce per «aggiustare» i test invece del codice. Riferisce al leader, che delega la correzione a chi possiede il file |
| **bando-compliance** | Verifica ogni deliverable contro i quattro file del bando. È l'agente che evita di perdere punti per un tecnicismo — tre cartelle, deck HTML, repository pubblico |

Il criterio *Adeguatezza degli strumenti* penalizza sia il sovraffollamento sia la penuria: ogni riga della tabella qui sopra è la motivazione dichiarata dell'esistenza di quell'agente, e togliendone uno qualcosa resta scoperto.

**Conoscenza condivisa e regole non negoziabili** stanno in un unico posto, [`../agents/build-time/CLAUDE.md`](../agents/build-time/CLAUDE.md), che ogni agente legge prima della prima riga: dipendenze congelate, zero codice di rete, due sole modalità di seam, UTF-8 obbligatorio, «oggi» iniettabile, confini di proprietà, limiti di iterazione.

---

## 2. HITL a due livelli — i tre gate umani

Il criterio *Robustezza* chiede «escalation umana intenzionale». Nel progetto compare due volte, e la simmetria è deliberata:

> **Nel prodotto:** nessuna email parte senza che Maria abbia riletto e premuto invia.
> **Nella build:** nessuna fase avanza senza che la persona abbia approvato il gate.

| Gate | Quando | Domanda binaria | Conseguenza già decisa se «no» |
|---|---|---|---|
| **1** | T+1:15 | FactGuard rifiuta l'importo troncato e accetta la data riformattata? | Si riduce lo scope ai **soli importi**, si taglia la verifica su date e orari |
| **2** | T+2:20 | Maria può leggere un'email e inviare una risposta, dal browser, **senza toccare la tastiera**? | Si tagliano tutte le P1 e si usano i dieci minuti restanti per stabilizzare quel percorso |
| **3** | T+2:30 | Feature freeze: si consegna così? | Non ha un «no»: da lì solo correzioni di bug e documentazione |

Il protocollo è rigido apposta: il leader **non formula la domanda sul momento** — è già scritta — non suggerisce la risposta, non deduce un «sì» dal silenzio, e applica la conseguenza già decisa invece di improvvisarne una migliore sotto pressione.

Esito e orario reale di ogni gate sono registrati in [`../agents/build-time/state/progress.json`](../agents/build-time/state/progress.json), con **lo stesso pattern di stato esternalizzato usato a runtime**. Verificabile, non dichiarato.

---

## 3. Cosa una persona ha rivisto e corretto

Questa è la parte che conta: gli agenti hanno scritto quasi tutto il codice, ma **sei correzioni sostanziali sono nate da una revisione umana su output reali**, non da un test che diventava rosso. Tutte hanno lasciato una traccia nel codice, sotto forma di commento che spiega l'errore — perché un vincolo senza la sua ragione viene rimosso al primo refactoring.

### ★ Quattro falsi positivi trovati eseguendo la pipeline sul corpus

Non sono ipotesi: sono comportamenti osservati facendo girare la pipeline sulle sei email vere.
**Nessuno dei quattro si vedeva leggendo il codice**, e due appartengono alla stessa famiglia —
la cecità alla negazione — il che è la ragione per cui vale la pena contarli invece di
correggerli in silenzio: una classe di errore che si ripresenta è un difetto di metodo, non
una svista.

#### (a) L'email autentica dell'INPS classificata come phishing

`em-04` è una comunicazione **vera** dell'INPS. Conteneva la frase:

> *«Si rammenta che l'Istituto **non richiede mai**, tramite posta elettronica, la comunicazione di **credenziali** di accesso, codici dispositivi o coordinate bancarie.»*

La regola «richiesta di credenziali» cercava le parole chiave e **ignorava la negazione**: trovava `credenziali`, alzava il flag grave, e il verdetto usciva **rosso** su una comunicazione legittima. Con `em-03` (la finta Poste) anch'essa rossa, il contrasto che regge tutta la demo spariva — e, molto peggio, il prodotto insegnava a Maria a diffidare del suo ente previdenziale.

**Correzione.** Due meccanismi in `engines/phishing_rules.py`, entrambi a finestra di contesto:

- `NEGAZIONI` — se nei 160 caratteri **precedenti** la parola chiave c'è una negazione (`non richiede`, `non le chiederemo`, `mai`, `diffidi`…), il segnale non scatta. Un ente vero che scrive *«non le chiederemo mai la password»* sta dando un **segnale di legittimità**, non di truffa.
- `RICHIESTE_ESPLICITE` — il segnale di truffa non è **nominare** una credenziale, è **chiederla**. L'INPS scrive *«previa autenticazione con le credenziali digitali»* spiegando come si accede al portale; la finta Poste scrive *«le verranno richiesti: password, codice PosteID, numero della carta»*. Solo il secondo è una richiesta rivolta al lettore.

Il test `test_email_che_dichiara_di_non_chiedere_credenziali_non_e_segnalata` blocca la regressione.

#### (b) La data di una citazione normativa estratta come fatto da proteggere

`em-02` (Comune di Torino) cita:

> *«ai sensi e per gli effetti degli artt. 33 e 40 del **D.P.R. 28 dicembre 2000, n. 445**»*

`28 dicembre 2000` è una data perfettamente valida, ancorata alla parola `del`. Veniva estratta come fatto operativo e finiva nella lista che FactGuard protegge. Effetto paradossale: **il semplificatore era obbligato a conservare il riferimento di legge**, cioè esattamente la formula che deve eliminare. Ogni tentativo di semplificazione veniva rifiutato e sull'email più burocratica del corpus compariva il fallback.

**Correzione.** `MARCATORI_NORMATIVI` in `engines/fact_extract.py`: se nei 35 caratteri precedenti compare `d.p.r`, `d.lgs`, `legge`, `decreto`, `art.`, `artt.`, `comma`…, la data **non è un fatto**.

Con una precisazione che è costata un secondo giro: l'esclusione doveva valere **su entrambi i lati del confronto**. Applicata solo in `estrai_fatti` e non in `estrai_valori_grezzi`, la stessa data sarebbe stata esclusa dall'originale e vista nel semplificato, e denunciata come *inventata*. I due lati di FactGuard devono applicare le stesse regole. Il commento è nel codice, il test è `test_la_data_di_una_citazione_normativa_non_e_un_fatto`.

#### (c) «Inventato» calcolato contro la lista dei fatti invece che contro il testo originale

Sempre su `em-04`, FactGuard segnalava come **inventata** la data `1 ottobre 2026`. Era nell'originale:

> *«Il pagamento è posto in riscossione **con valuta 1 ottobre 2026** presso l'istituto di credito…»*

Il bug era concettuale, non sintattico. Il verificatore confrontava i valori trovati nel semplificato con la **lista dei fatti ancorati**. Ma i fatti si estraggono solo se ancorati a una parola chiave, e `con valuta` non è un'ancora: la data esisteva nell'originale senza essere un fatto protetto. Il semplificatore la ricopiava, e il verificatore la denunciava come comparsa dal nulla.

> **«Inventato» significa: non c'è nell'originale. Non significa: non è fra i fatti protetti.**

**Correzione.** `verificatore.verifica()` riceve un parametro in più, `testo_originale`, e i candidati «inventati» vengono confrontati con **tutto ciò che il testo originale contiene davvero**, non con la lista ristretta. La distinzione è scritta per esteso nel commento del codice, perché è il tipo di dettaglio che verrebbe «semplificato via» da chi legge la funzione fra sei mesi.

#### (d) «Le chiedono di rispondere» su un'email che dice di non rispondere

Ancora `em-04`, e ancora la negazione — stavolta nel semplificatore. La chiusura di rito di
quasi ogni comunicazione automatica di un ente è:

> *«La presente comunicazione è generata automaticamente: si prega di **non rispondere** a
> questo indirizzo.»*

`plain_rules.azione_richiesta` cercava la sottostringa `rispondere` e restituiva
**«Le chiedono di rispondere.»** — nella scheda *Cosa le chiedono*, cioè la prima riga che Maria
legge, su una comunicazione puramente informativa che le chiede l'esatto contrario.

È **la stessa classe di errore di (a)**, in un altro motore: una regola che cerca una parola
chiave e non guarda se è negata. Che si sia ripresentata dopo essere stata corretta una volta è
il motivo per cui ora è documentata come *famiglia* e non come caso isolato.

**Correzione.** `RE_NEGAZIONE_AZIONE` in `engines/plain_rules.py`: si scorrono **tutte** le
occorrenze del verbo e si scarta quella preceduta da una negazione nei 24 caratteri precedenti.
Scorrere tutte le occorrenze, e non solo la prima, è ciò che impedisce alla correzione di
introdurre il falso positivo opposto: se un'email dicesse *«si presenti allo sportello»* **e**
*«non risponda a questo indirizzo»*, la richiesta vera deve comunque emergere. I tre casi sono
in `app/tests/test_plain_rules.py`.

### Due riscritture nate da output palesemente sbagliati

#### (d) Il primo semplificatore produceva italiano rotto

La prima versione sostituiva **parola per parola** da un dizionario burocratese → italiano comune. Su un'email vera del Comune produceva:

> *«all'domanda»* · *«dallei richiesto»* · *«Le chiediamo di pertanto lei a voler ritirare»*

Peggio dell'originale, perché l'originale almeno era grammaticalmente corretto. La causa è **strutturale, non un bug da aggiustare**: sostituire un sostantivo ne cambia il genere e manda in pezzi articoli e preposizioni intorno. Un motore a regole non sa concordare.

**Riscrittura.** `engines/plain_rules.py` lavora su due livelli, entrambi sicuri:

1. **Frasi intere** di pura formula (*«non necessita di sottoscrizione autografa»*): si cancellano. Non resta niente da concordare.
2. **Locuzioni autonome**: si sostituiscono **per intero, articolo compreso** (`all'istanza` → `alla domanda`, `si invita la S.V. a voler provvedere al ritiro del` → `le chiediamo di ritirare il`), così la concordanza è scritta dentro la sostituzione stessa.

Ciò che non rientra nei due casi **resta com'è**. È un limite dichiarato, con una conseguenza misurata: il corpo riscritto guadagna poco in leggibilità, e il guadagno vero sta nel riassunto Chi / Cosa / Entro quando ([`VALIDAZIONE.md`](VALIDAZIONE.md) §3).

#### (e) Uno spezza-frasi che tagliava un indirizzo in due

Le frasi lunghe sono la leva più forte sull'indice Gulpease, che premia i periodi corti molto più delle parole corte. Una versione intermedia spezzava i periodi lunghi **sulla virgola più vicina alla metà**, senza guardare cosa ci fosse intorno. Su `em-02` produceva:

> *«…sito in **Via dell'Esempio 12. 10122 Torino**, entro…»*

Un indirizzo tagliato a metà, con il CAP promosso a nuova frase. Un testo «più leggibile» che ha perso un'informazione è un testo peggiore, e su un documento che dice a una persona anziana **dove andare** è un danno concreto.

**Correzione.** `_taglia_in_sicurezza` ha tre guardie: mai dopo una cifra, mai prima di una cifra, e solo se la parola successiva appartiene a `INIZI_DI_CLAUSOLA` — cioè può davvero aprire una frase. Se nessun punto di taglio è sicuro, **la frase resta lunga**: è un esito accettabile, spezzare un'informazione non lo è.

### Le altre revisioni, in breve

| Rilievo | Correzione |
|---|---|
| Il triage classificava lo studio medico come `persona_conosciuta` perché è in rubrica | La rubrica pesa sulla **sicurezza**, non sulla categoria: lo studio scrive comunque in burocratese e va semplificato. Commentato in `agents/triage.py` |
| Un agente ha proposto `dateparser` per le date italiane | Rifiuto secco, come previsto da `CLAUDE.md` §1. Le date italiane si fanno a mano in `normalize.py`: `dateparser` è una dipendenza pesante che introdurrebbe comportamenti non deterministici proprio dove serve il contrario |
| Il verificatore avrebbe potuto essere «un modello che controlla il modello» | Rifiutato per progetto, non per tempo. Un verificatore che allucina è **peggio** di nessun verificatore, perché dà una garanzia falsa. Motivazione in `agents/runtime/routing.md` §1 e `05-verificatore.md` |

---

## 4. Le decisioni tecniche, e perché

| Decisione | Alternativa scartata | Ragione |
|---|---|---|
| **Nessuna dipendenza `anthropic`, zero codice di rete in `app/`** | Chiamate live con chiave in `.env` | Il repository è pubblico. Non «la chiave non è committata»: **la chiave non esiste**, e `test_llm_modes.py` lo verifica leggendo staticamente ogni sorgente |
| **Seam a due modalità, `off` / `replay`** | Una terza modalità `live` disattivata | Una modalità disattivata è codice morto che qualcuno riattiva. Due modalità sono due comportamenti, entrambi provati |
| **I prompt in `agents/runtime/prompts/` caricati dal codice** | Prompt in stringhe Python, documentati a parte | Una sola fonte di verità. È **impossibile** che la documentazione diverga dal comportamento, perché sono lo stesso file |
| **Verificatore deterministico** | LLM-as-judge | Il controllo non può appartenere alla stessa classe di strumento della cosa controllata |
| **SQLite `:memory:`** | File su disco, oppure dizionari Python | Nessuna dipendenza aggiunta, azzerato a ogni avvio, **interrogabile in SQL** — lo stato esternalizzato si mostra in demo invece di raccontarlo |
| **«Oggi» costante iniettabile** (`clock.py`) | `date.today()` | Senza un orologio fermo le scadenze del corpus scadono da sole e i test diventano non deterministici in pochi giorni |
| **Frontend senza build** | React, Vite, un bundler | `node` non è installato, e installarlo a metà hackathon non è un'opzione. Nessuna CDN: la demo gira a Wi-Fi staccato |
| **Porta 8123** | 8000 | Entrambe libere, ma la 8000 attira strumenti aziendali |

---

## 5. Cosa ha fatto l'AI, in proporzione

| Prodotto da | Cosa |
|---|---|
| **Agenti AI** | Struttura di `agents/`, contratti Pydantic e JSON Schema, i sei agenti di runtime, i cinque motori a regole, la seam LLM, l'API, il frontend, la suite di test, il corpus, il deck |
| **La persona** | Le tre decisioni ai gate; le cinque correzioni della §3, tutte nate dal **guardare l'output reale**, non dal leggere il codice; il rifiuto delle dipendenze proposte; la scelta di scope di FactGuard |
| **Nessuno dei due, da solo** | Il punto in cui i due si incontrano: gli agenti hanno scritto il verificatore, ma è stato eseguirlo sul corpus vero a far emergere che «inventato» era calcolato contro la lista sbagliata |

> La revisione umana non ha corretto errori di sintassi — di quelli non ce n'erano. Ha corretto **tre casi in cui il codice faceva esattamente ciò che gli era stato chiesto, e ciò che gli era stato chiesto era sbagliato.**
