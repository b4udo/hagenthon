# /verifica-a11y

> Costruire uno strumento di accessibilità inaccessibile è la domanda letale della giuria: questa
> è la checklist che la rende una domanda già chiusa — eseguibile su una schermata alla volta, con
> scritto **come** si misura ogni voce, perché «sembra accessibile» non è una misura.

## Quando usarlo

- Su **ogni schermata** appena `dev-frontend` la dichiara finita.
- Nella fase di verifica T+2:30–2:50, eseguito da `qa-critic` su tutte le schermate.
- Prima di fare lo screenshot che finirà in presentazione: un difetto di accessibilità immortalato
  in una slide resta lì.

**Il perché di ogni vincolo non sta qui:** ogni riga nasce da un dettaglio della persona, ed è
documentata in [`../developers/dev-frontend.md`](../developers/dev-frontend.md) §vincoli. Quel file
dice **perché**, questo dice **come si verifica**. Non si duplicano.

## Cosa fa

Si esegue **una schermata alla volta**. Ogni voce ha un esito binario: passa o non passa. «Quasi»
non è un esito.

### 1 · Struttura e semantica

1. **`lang="it"`** sull'elemento `<html>`. *Come:* ispeziona l'elemento radice.
2. **Un solo `<h1>`**, e i titoli non saltano livelli. *Come:* elenca gli heading in ordine nel
   DOM e controlla la sequenza.
3. **Landmark presenti**: `<main>`, e `<nav>` se c'è navigazione. *Come:* ispeziona il DOM.
4. **Ogni elemento cliccabile è un `<button>` o un `<a>` vero.** *Come:* cerca `onclick` su `div`
   e `span` — deve dare zero risultati. Un `<div onclick>` non riceve il focus, non risponde alla
   barra spaziatrice e non viene annunciato come pulsante.
5. **Ogni pulsante ha un nome accessibile** non vuoto: testo visibile, oppure `aria-label` se
   l'etichetta è un'icona. *Come:* ispeziona il nome calcolato nel pannello di accessibilità.

### 2 · Dimensioni e contrasto

6. **Ogni target interattivo misura almeno 44×44 px**, bordi inclusi. *Come:* seleziona
   l'elemento, leggi il riquadro nel pannello di ispezione. Si misura il **target**, non l'icona
   dentro al target.
7. **Distanza fra target adiacenti ≥ 8px.** *Come:* stesso strumento. Due pulsanti da 44px
   attaccati sono un bersaglio unico per una mano che trema.
8. **Dimensione base del testo = 20px**, e nessun testo di contenuto sotto i 16px. *Come:* leggi
   il `font-size` calcolato, non quello dichiarato nel foglio di stile.
9. **Contrasto ≥ 7:1** per ogni coppia testo/sfondo, inclusi testi su colore, badge e pulsanti.
   *Come:* selettore di contrasto del pannello di accessibilità, coppia per coppia. La soglia è
   7:1, non 4.5:1: è la cataratta iniziale di Maria, non un livello di conformità scelto per
   ambizione.
10. **Nessun testo grigio su grigio**, e nessuna informazione affidata al **solo** colore. *Come:*
    il semaforo deve avere anche una parola (`Sicura` / `Attenzione` / `Non rispondere`), non solo
    un pallino.

### 3 · Tastiera e focus

11. **Il percorso completo si fa con Tab e Invio.** *Come:* posa il mouse e percorri la schermata
    dall'inizio alla fine. Se serve il mouse anche una sola volta, la voce non passa.
12. **Il focus è visibile su ogni elemento raggiungibile**, con un contorno che si vede sul fondo
    scuro. *Come:* percorri con Tab e guarda. Un `outline: none` senza sostituto è un difetto
    bloccante.
13. **L'ordine di tabulazione segue l'ordine visivo.** *Come:* percorri con Tab e confronta con
    l'ordine in cui si legge la pagina.
14. **Nessuna trappola del focus**: da ogni punto si esce con Tab o Esc. *Come:* entra in ogni
    pannello che si apre e prova a uscirne.
15. **Nessun `tabindex` positivo.** *Come:* cerca `tabindex="` nel sorgente; sono ammessi solo
    `0` e `-1`.

### 4 · Interazione motoria

16. **Nessun comportamento dipende dall'hover.** *Come:* percorri la schermata da tastiera e
    verifica che nulla di necessario compaia solo al passaggio del puntatore.
17. **Nessun doppio click.** *Come:* ogni azione si completa con un clic singolo.
18. **Nessun trascinamento.** *Come:* nessun riordino, nessun cursore, nessun elemento da spostare.
19. **Nessuna azione a tempo**: niente che scompaia da solo, niente scadenze di sessione, niente
    conferme che si chiudono da sole. *Come:* apri la schermata e aspetta un minuto senza toccare
    nulla.
20. **I target non si spostano** mentre la mano si avvicina: nessuna animazione di layout su hover
    o focus.

### 5 · Cambi di stato

21. **Esiste una regione `aria-live="polite"`** e i cambi di stato ci passano dentro: esito del
    semaforo, esito della verifica, conferma di invio. *Come:* ispeziona la regione, poi scatena
    il cambio e verifica che il testo cambi lì dentro.
22. **`aria-live` non è `assertive`** se non c'è un'emergenza. *Come:* lettura dell'attributo.
23. **Il rifiuto di FactGuard è annunciato**, non solo colorato. *Come:* premi «E se l'AI
    sbaglia?» e verifica che il messaggio finisca nella regione live.
24. **Nessun cambiamento di contesto automatico**: nessun focus che si sposta da solo, nessuna
    navigazione senza un'azione dell'utente.

### 6 · Layout

25. **Colonna singola a 1024px di larghezza.** *Come:* ridimensiona la finestra e guarda. Il
    tablet di Maria è appoggiato al tavolo, non in mano.
26. **Nessun menu a scomparsa**, nessun contenuto nascosto dietro un'icona.
27. **La pagina resta usabile con lo zoom del browser al 200%**, senza scorrimento orizzontale.
    *Come:* `Ctrl` `+` fino al 200% e ripercorri il flusso.

## Output atteso

- **27 voci con esito binario** per ciascuna schermata verificata.
- Per ogni voce che non passa: la schermata, l'elemento, il valore misurato e quello richiesto
  (*«pulsante Invia: 38×38 px, richiesti 44×44»*). Un numero, non un'impressione.
- L'elenco confluisce nel report di [`../qa/qa-critic.md`](../qa/qa-critic.md) con proprietario
  `dev-frontend`.
- **Le voci 4, 11, 12 e 21 sono bloccanti**: una schermata che non le passa non è consegnabile e
  non va fotografata per il deck.

## Fallimenti tipici

| Sintomo | Causa | Rimedio |
|---|---|---|
| Il focus sparisce su alcuni elementi | `outline: none` nel reset del CSS senza uno stile sostitutivo | Ripristinare un contorno visibile sul fondo scuro |
| Il target misura 44px ma è scomodo | Si è misurata l'icona, non il pulsante, oppure manca la distanza della voce 7 | Rimisurare il riquadro dell'elemento interattivo e distanziare |
| Il contrasto passa a 4.5:1 ma non a 7:1 | Si è usata la soglia di conformità standard invece di quella del progetto | Cambiare la palette. La soglia non si negozia |
| Lo screen reader non annuncia il semaforo | Il testo è stato scritto **fuori** dalla regione `aria-live`, o la regione è stata ricreata nel DOM | La regione deve esistere prima del cambiamento e restare la stessa: si aggiorna il testo, non si sostituisce il nodo |
| Tab salta un pulsante | È un `<div>` con `onclick` | Sostituirlo con un `<button>` vero. È la voce 4, ed è bloccante |
| L'ordine di tabulazione è strano | `tabindex` positivi sparsi per «aggiustare» l'ordine | Toglierli e riordinare il DOM |
| La verifica passa in locale ma non in proiezione | Il contrasto è stato misurato su un monitor tarato diversamente | Rifare la prova sulla macchina e sul proiettore della demo |
| Una voce viene dichiarata «ok» senza misura | Fretta | Un esito senza numero non è un esito: si rimisura |
