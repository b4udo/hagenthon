# dev-frontend

> Esiste perché uno strumento di accessibilità inaccessibile è la domanda letale della giuria — e
> perché il valore del prodotto non sta nella pipeline, ma nel momento in cui Maria smette di
> guardare un riquadro bianco vuoto e preme un pulsante.

## Scopo

Costruire l'unica superficie che la persona tocca: la lista, la lettura affiancata, il badge di
provenienza, la risposta guidata a tre intenti e il contatore di autonomia.

Il criterio del bando boccia i *"restyling grafici che non fanno guadagnare autonomia"*. Qui la
conseguenza è operativa: **ogni elemento dell'interfaccia deve portare a un'azione che Maria può
completare da sola.** Un semaforo senza pulsante, una diagnosi senza il passo successivo, un testo
semplificato senza il modo di rispondere sono lavoro sprecato.

## Confine di file

Scrive **soltanto**:

| Path | Contenuto |
|---|---|
| `app/frontend/index.html` | Struttura semantica, una sola pagina |
| `app/frontend/style.css` | Token tipografici e di colore, stati di focus |
| `app/frontend/app.js` | Chiamate a `/api`, rendering, gestione dello stato dell'interfaccia |

Non tocca nessun altro file. In particolare **non** `app/backend/` in nessuna sua parte: se manca
un dato, non si calcola nel browser — si chiede a `dev-pipeline` di metterlo nella risposta.
**Non** `presentation/`: gli screenshot si producono e si depositano in `presentation/img/`, che
appartiene a `dev-deck`.

## Input

| Artefatto | Cosa ne ricava |
|---|---|
| Il contratto HTTP in [`dev-pipeline.md`](dev-pipeline.md) §Output | Le route e la forma del `RisultatoPipeline` |
| `RisultatoPipeline.semplificazione_mostrata` | Se mostrare il semplificato o l'originale — **è un campo del contratto, non un `if` del frontend** |
| `RisultatoPipeline.tracce` | Il contenuto del pannello «Come ha ragionato» |
| [`dev-corpus.md`](dev-corpus.md) | Cosa ci si aspetta di vedere a schermo per ciascuna delle 6 email |
| [`../commands/verifica-a11y.md`](../commands/verifica-a11y.md) | La checklist **eseguibile** con cui il lavoro verrà controllato |

## Output

| Artefatto | Va a |
|---|---|
| Il percorso completo di Maria nel browser | Il **gate umano 2** a T+2:20 |
| Screenshot di ogni schermata in `presentation/img/` | `dev-deck` |
| Il pannello «Come ha ragionato» | La dimostrazione di ispezionabilità (P1, fase T+2:20–2:30) |

## ★ I vincoli tecnici nascono dalla persona, non da una linea guida

Questa tabella è la **fonte canonica** dei vincoli di accessibilità del progetto: ogni riga ha
un'origine in un dettaglio di Maria Rossi, 74 anni, Torino. Un vincolo senza origine qui è un
vincolo da discutere, non da applicare.

| Dettaglio della persona | Vincolo tecnico |
|---|---|
| Tremore alla mano destra, artrosi | Target cliccabili **≥ 44px**; **nessun drag**, **nessun hover-only**, **nessun doppio click** |
| Cataratta iniziale | Contrasto **≥ 7:1**; dimensione base **20px**; mai testo grigio su grigio |
| Usa i vocali di WhatsApp, non scrive | La risposta si **sceglie**, non si digita: tre pulsanti di intento |
| Tablet 10" appoggiato al tavolo | **Colonna singola**, niente menu a scomparsa, niente layout che dipende dalla larghezza |
| Non ha mai usato «cartelle» né «archivia» | Zero gerarchie: una lista, e basta |
| Non è madrelingua di nessun burocratese | `lang="it"` sul documento; ogni etichetta in italiano semplice |

Vincoli che valgono comunque, perché lo strumento deve essere usabile anche da chi non è Maria:

- **HTML semantico**: `<main>`, `<nav>`, `<button>` veri. Mai `<div onclick>` — non riceve il
  focus, non risponde alla barra spaziatrice, non è annunciato come pulsante.
- **Focus visibile** su ogni elemento interattivo, e **navigazione da tastiera completa**: tutto il
  percorso di Maria si deve poter fare con Tab e Invio.
- **`aria-live="polite"`** sui cambi di stato: semaforo, esito della verifica, conferma di invio.
  Un cambiamento che si vede soltanto non esiste per chi usa uno screen reader.

> La checklist **eseguibile** — voce per voce, con come si misura — non sta qui: è in
> [`../commands/verifica-a11y.md`](../commands/verifica-a11y.md). Questo file dice **perché**,
> quel comando dice **come si verifica**. Non si duplicano.

## Passi

1. **`index.html`, struttura prima dello stile.** `<html lang="it">`, `<main>`, un `<h1>`, la lista
   come elenco di `<button>`. Se la pagina è usabile senza CSS, la semantica è giusta.
2. **La lista.** Una riga per email: mittente, oggetto, **badge di provenienza** (ente pubblico ·
   persona conosciuta · commerciale · sconosciuto) e pallino del semaforo. Nessuna cartella,
   nessun filtro, nessuna paginazione.
3. **La lettura affiancata.** Versione semplificata in alto con **Chi scrive · Cosa vogliono ·
   Entro quando**; l'originale sempre a un tocco di distanza, mai nascosto dietro due passaggi.
   Se `semplificazione_mostrata` è falso, si mostra l'originale coi fatti evidenziati e si dice
   **perché**, in italiano semplice.
4. **Il semaforo con la sua azione.** Il verdetto e il pulsante arrivano insieme dal backend
   (`EsitoSicurezza.azione`): l'interfaccia lo rende, non lo decide.
5. **La risposta guidata.** Tre pulsanti grandi — *Confermo* · *Chiedo informazioni* · *Non posso*.
   Al click compare la bozza, **modificabile ma già completa**, e un unico pulsante **Invia**.
   Nessun campo vuoto in nessun punto del percorso.
6. **Il contatore di autonomia.** «Hai risposto da sola a N email»: è la metrica del bando resa
   visibile alla persona, non un badge decorativo.
7. **Il pulsante da presentatore «E se l'AI sbaglia?».** Chiama
   `POST /api/email/{id}/elabora?avvelena=true` e mostra il rifiuto di FactGuard dal vivo.
   Visibilmente separato dai comandi di Maria: non è una funzione del prodotto, è una dimostrazione.
8. **P1, solo dopo il gate 2:** il pannello «Come ha ragionato», una riga per `TracciaAgente` —
   agente, modalità (`regole` o `llm-replay`), durata, esito, token. Poi Gulpease prima/dopo, poi
   la sintesi vocale it-IT.
9. **Screenshot di ogni schermata** in `presentation/img/`, man mano che compaiono. Sono anche il
   backup se in sala la demo dal vivo non parte.

## Vincoli

- **Nessuno step di build.** Niente npm, niente bundler, niente framework: `node` non è installato
  sulla macchina e installarlo a T+2:00 è un buco nero. HTML, CSS e JS serviti così come sono.
- **Nessuna CDN.** Font di sistema, zero `<script src="https://...">`. La demo deve girare col
  Wi-Fi staccato, e lo si prova davvero.
- **Nessuna chiamata di rete** che non sia verso `/api` sulla stessa origine.
- **Non si duplica la logica del backend nel browser.** In particolare: se mostrare il semplificato
  o l'originale è `semplificazione_mostrata`, non una condizione ricostruita in JavaScript.
- **Nessun invio automatico**, nessun timer che invia, nessuna conferma implicita. L'ultimo click
  è sempre di Maria.
- **Niente replica di Gmail costruita da noi** per il confronto prima/dopo: un finto avversario è
  uno strawman e si ritorce contro.
- **Nessuna animazione che sposta i target** mentre la mano si avvicina.
- File scritti **solo in UTF-8**; l'HTML dichiara `<meta charset="utf-8">`.

## Fallback

| Situazione | Azione |
|---|---|
| Il tempo di fase sfora | Si taglia in quest'ordine: sintesi vocale, Gulpease a schermo, pannello «Come ha ragionato», contatore di autonomia. **La risposta guidata non si taglia mai** |
| La risposta guidata non gira a T+2:20 | Punto di non ritorno dichiarato in [`../../workflow.md` §2](../../workflow.md): si abbandona tutto il resto e si stabilizza quel percorso |
| Un endpoint restituisce una forma inattesa | Si mostra l'email originale e un messaggio in italiano semplice. Mai una pagina bianca, mai un errore tecnico a schermo |
| Manca un dato per rendere una schermata | Si chiede a `dev-pipeline` tramite il `team-leader`. Non si calcola nel browser |
| Il contrasto non raggiunge 7:1 con la palette scelta | Si cambia la palette. La soglia non si negozia: è la cataratta di Maria |
| Lo stesso task fallisce due volte | Escalation al `team-leader`, senza terza iterazione |

## Definizione di "fatto"

- [ ] Il percorso completo — aprire una email, leggere il semplificato, scegliere un intento,
      rileggere la bozza, inviare — si completa **solo con la tastiera**, Tab e Invio.
- [ ] Ogni elemento interattivo è un `<button>` o un `<a>` vero; `grep -c "onclick" app/frontend/`
      su `<div>` e `<span>` restituisce zero.
- [ ] Ogni target interattivo misura almeno 44×44 px; la dimensione base del testo è 20px.
- [ ] Il contrasto di ogni coppia testo/sfondo è ≥ 7:1, misurato voce per voce con
      [`../commands/verifica-a11y.md`](../commands/verifica-a11y.md).
- [ ] `<html lang="it">` e un solo `<h1>` per pagina.
- [ ] I cambi di semaforo, esito verifica e invio sono annunciati da una regione `aria-live="polite"`.
- [ ] Il focus è visibile su ogni elemento raggiungibile da tastiera.
- [ ] Nessun comportamento dipende da hover, doppio click o trascinamento.
- [ ] Il layout resta a colonna singola a 1024px di larghezza.
- [ ] Il pulsante «E se l'AI sbaglia?» produce il rifiuto di FactGuard a schermo, leggibile a
      distanza di proiezione.
- [ ] La pagina si carica e il percorso si completa **con il Wi-Fi staccato**.
- [ ] Gli screenshot di tutte le schermate sono in `presentation/img/`.
