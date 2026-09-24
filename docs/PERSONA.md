# Persona e barriera — Maria Rossi

> Deliverable 1. Il bando boccia i *«profili utente generici»*: qui **ogni dettaglio impone una scelta tecnica verificabile nel codice**. Se un dettaglio non impone niente, è stato tolto.

---

## Chi è

**Maria Rossi, 74 anni, Torino.** Vedova, vive sola. Ex sarta, licenza media.

Il nipote **Luca** le ha aperto `maria.rossi47@gmail.com` due anni fa, per una ragione pratica: l'ASL manda lì le prenotazioni e il Comune i certificati. Non è stata una scelta sua, ed è la condizione di partenza — non usa la posta elettronica perché le piace, la usa perché le istituzioni hanno smesso di scriverle su carta.

Legge la posta su un **tablet da 10 pollici appoggiato al tavolo della cucina**. Usa WhatsApp tutti i giorni, quasi solo con i messaggi vocali.

---

## La tabella dei vincoli

Ogni riga è un dettaglio della persona → il vincolo tecnico che ne discende → dove quel vincolo vive nel codice.

| Dettaglio | Vincolo tecnico imposto | Dove si vede |
|---|---|---|
| **Tremore alla mano destra, artrosi** | Target cliccabili **≥ 44px** (qui 48, per lasciare margine). Nessun drag, nessun doppio click, nessun hover-only, distanza fra target adiacenti ≥ 8px | `app/frontend/style.css` → `--tocco: 48px`; test `test_i_bersagli_sono_abbastanza_grandi_per_una_mano_che_trema` |
| **Cataratta iniziale** | Contrasto **≥ 7:1** (AAA, non AA), base **20px**, mai testo grigio su grigio, nessuna informazione affidata al solo colore | `style.css` → `html { font-size: 20px }`, palette con i rapporti annotati riga per riga; il semaforo porta sempre una **parola** oltre al pallino |
| **Usa i vocali di WhatsApp, non scrive** | **Sa parlare, non digitare** → la risposta si **sceglie**, non si scrive. Tre pulsanti di intento, la bozza è già compilata | `app/backend/agents/compositore.py`; specifica in `agents/runtime/06-compositore.md` |
| **Tablet 10" appoggiato al tavolo** | Layout a **colonna singola**, larghezza di lettura fissa, niente menu a scomparsa, niente contenuto dietro un'icona | `style.css` → `max-width: 760px` su un'unica colonna; nessun `<nav>` a scomparsa nel markup |
| **Non ha mai usato «cartelle» né «archivia»** | **Zero gerarchie annidate**, e nessun gergo. Le tre cartelle che esistono — *Posta in arrivo*, *Posta inviata*, *Posta eliminata* — sono i tre posti che chiunque si aspetta da una cassetta della posta, sono **sempre tutte e tre visibili** come pulsanti scritti a parole, e non si annidano. Nessun tag, nessun albero, nessuna «archiviazione» | `app/frontend/index.html` → `<nav class="cartelle">` con tre `<button>`, mai un menu a scomparsa; `GET /api/mailbox?cartella=…` è una lista piatta per cartella, non un albero |

Due conseguenze meno ovvie, che discendono dalle stesse righe:

| Dettaglio | Vincolo meno ovvio |
|---|---|
| Licenza media | Obiettivo di leggibilità **Gulpease ≥ 60** sul testo mostrato, misurato e riportato in interfaccia (`app/backend/engines/gulpease.py`). Non è una promessa: è un numero visibile, anche quando è basso — vedi [`VALIDAZIONE.md`](VALIDAZIONE.md) |
| Nessuna familiarità con il gergo informatico | Il verdetto di sicurezza deve essere **spiegabile in una frase italiana** (*«il nome dice Poste Italiane ma l'indirizzo non è quello ufficiale»*), non una probabilità. È il motivo per cui l'agente 02 **non ha** una seam LLM — vedi `agents/runtime/routing.md` §2 |

---

## ★ Il momento preciso in cui si ferma

Non è «trova l'interfaccia difficile». È un istante identificabile, e il prodotto è costruito attorno a quello.

> Ha aperto l'email della **dott.ssa Bianchi**, il suo medico di base. Le chiedono di **confermare la visita del 14 ottobre, alle 9:30**.
> Ha capito cosa vogliono. Sa benissimo cosa vuole rispondere.
>
> Ha premuto **Rispondi**.
>
> Si trova davanti a un **riquadro bianco vuoto**. Non sa cosa scrivere né dove. Non sa come si apre e come si chiude una lettera a un medico. Ha paura di scrivere una cosa sbagliata a un dottore.
>
> **Chiude tutto.** Aspetta domenica, quando viene Luca.

Il riquadro bianco chiede *«cosa vuoi scrivere?»*. È la domanda sbagliata: Maria non sa rispondere **per iscritto**, anche quando sa perfettamente cosa vuole dire. Lo dimostra il fatto che manda vocali tutti i giorni.

**Il ribaltamento del prodotto è tutto qui:** la domanda diventa *«cosa vuole fare?»*, e le risposte sono tre pulsanti — *Confermo che vengo* · *Ho bisogno di più informazioni* · *Non posso, chiedo di spostare*. Lei sceglie, rilegge, invia.

Questa email è `em-01` del corpus di demo (`app/backend/data/mailbox.json`) e non è un caso scelto per comodità: è **il** caso.

---

## Perché non basta un restyling

Il bando boccia esplicitamente i *«restyling grafici che non fanno guadagnare autonomia»* e le *«soluzioni che si fermano alla diagnosi»*. Font grandi non risolvono nulla del momento descritto sopra: Maria vedeva benissimo il riquadro bianco.

Quindi ogni capability del prodotto finisce in **un'azione che Maria può eseguire da sola**, e il sistema non emette mai un verdetto senza un pulsante accanto.

| Barriera | Capability | L'azione che ne segue |
|---|---|---|
| Non distingue una truffa da una comunicazione vera | **Semaforo di sicurezza** | 🔴 *«Non risponda»* + pulsante col **numero verde ufficiale**, preso da una tabella statica nel codice e **mai dall'email** · 🟡 *«Chieda a Luca»* + pulsante «Manda a Luca» · 🟢 *«Può rispondere»* + porta alla risposta guidata |
| *«Ai sensi e per gli effetti degli artt. 33 e 40 del D.P.R. …»* | **Traduttore del burocratese** | **Chi le scrive · Cosa le chiedono · Entro quando** in cima, in tre righe |
| Il riquadro bianco vuoto | **Risposta guidata per intenti** | Sceglie *«Confermo»* → il sistema compone → lei rilegge → **preme invia lei** |
| Gli allegati sono invisibili | **Allegati in chiaro** | *«C'è un foglio allegato»* con nome e dimensione, in una scheda propria |

> Un semaforo senza pulsante è un checker travestito da assistente. **Nessun verdetto senza azione.**

Il percorso completo, passo per passo: [`PERCORSO-ASSISTITO.md`](PERCORSO-ASSISTITO.md).
Quello che resta comunque fuori portata: [`AUTONOMIA-E-LIMITI.md`](AUTONOMIA-E-LIMITI.md).

---

## La rubrica e le altre persone

Nel corpus la rubrica di Maria contiene sei contatti: Luca (il nipote), i figli Anna e Paolo, un'amica, lo studio della dott.ssa Bianchi, la farmacia. Non è colore narrativo, ha due effetti tecnici precisi:

1. **Chi è in rubrica riceve il verde** dal semaforo (`phishing_rules.valuta`), e chi non c'è riceve al massimo il giallo — *uno sconosciuto innocuo è giallo, mai verde*.
2. **La persona di fiducia dell'azione gialla ha un nome**: il pulsante dice *«Manda questa email a Luca»*, non *«inoltra»*. Il nome sta in una costante (`sicurezza.NOME_PERSONA_FIDUCIA`), non è ricavato dall'email.

La rubrica **non** decide la categoria del triage: lo studio medico è in rubrica ma scrive comunque in burocratese, e trattarlo come «persona conosciuta» gli toglierebbe la semplificazione proprio nel caso d'uso principale. La distinzione è commentata in `app/backend/agents/triage.py`.
