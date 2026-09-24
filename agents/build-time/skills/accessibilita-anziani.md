# Skill · Accessibilità per persone anziane

> Conoscenza condivisa, non un agente. La caricano `dev-frontend` quando
> costruisce l'interfaccia e `qa-critic` quando la verifica. La checklist
> **eseguibile** sta in [`../commands/verifica-a11y.md`](../commands/verifica-a11y.md):
> qui c'è il *perché*, lì il *come si controlla*.

---

## Il principio

> **Ogni numero qui sotto discende da un vincolo di Maria, non da una linea
> guida generica.**

Citare le WCAG non basta e non convince: la domanda a cui rispondere è *"cosa
succede a questa persona, con queste mani e questi occhi, davanti a questa
schermata"*. Se una regola non si può ricondurre a un dettaglio della persona,
non appartiene a questo progetto.

## La tabella che governa il frontend

| Vincolo della persona | Conseguenza tecnica | Valore adottato |
|---|---|---|
| Tremore alla mano destra, artrosi | Bersagli grandi, nessun gesto fine | **≥ 44px** (qui 48), nessun drag, nessun doppio click, nessun hover-only |
| Cataratta iniziale | Contrasto e corpo del testo | **≥ 7:1** (AAA, non AA), base **20px**, interlinea 1.6 |
| Usa i vocali di WhatsApp, non scrive | L'input testuale è una barriera | La risposta si **sceglie**, non si scrive |
| Tablet 10" appoggiato al tavolo | Niente layout larghi né menu a scomparsa | **Colonna singola**, larghezza massima ~760px |
| Non ha mai usato cartelle o archivi | Zero gerarchie da imparare | Una lista piatta, nessun annidamento |
| Non sa cosa sia un errore di sistema | I messaggi tecnici spaventano | Mai un codice di errore, mai un traceback |

## Regole non negoziabili

1. **HTML semantico.** `<main>`, `<nav>`, `<button>` veri. Mai `<div onclick>`:
   non riceve il fuoco, non risponde a Invio, non viene annunciato.
2. **Fuoco sempre visibile.** `:focus-visible` con un contorno spesso. Chi
   naviga da tastiera non deve indovinare dove si trova.
3. **Il fuoco segue la vista.** Quando la schermata cambia, il fuoco si sposta
   sul nuovo contenuto. Altrimenti la tastiera resta indietro di una schermata.
4. **`aria-live="polite"`** su ogni cambio di stato: semaforo, esito della
   verifica, conferma di invio. Un cambiamento che non viene annunciato, per
   chi non lo vede, non è avvenuto.
5. **`lang="it"`** sull'elemento radice, o la sintesi vocale legge l'italiano
   con la fonetica inglese.
6. **Nessun limite di tempo**, nessun contenuto che si muove da solo.
7. **Rispetta `prefers-reduced-motion`.**

## Sul linguaggio dell'interfaccia

- Si dà **del lei**, con il tono che userebbe un ente: cortese e diretto.
  Mai paternalistico — non è una bambina, è una persona che non conosce uno
  strumento.
- Le etichette dei pulsanti sono **in prima persona**: *"Confermo che vengo"*,
  non *"Conferma"*. Deve riconoscere la propria intenzione, non eseguire un
  comando.
- Mai gergo informatico: né *client*, né *account*, né *sincronizzazione*.

## L'errore da non fare

> Costruire uno strumento di accessibilità **inaccessibile**.

È la domanda che una giuria fa per prima, ed è letale perché smonta l'intera
premessa. Il progetto ha un costo fisso di venti minuti dedicati a questa
verifica, e sono spesi prima del freeze, non dopo.

Una seconda trappola, più sottile: **il restyling che non produce autonomia.**
Caratteri grandi e colori tenui non fanno guadagnare nulla se la persona
resta bloccata allo stesso punto di prima. Ogni scelta di interfaccia va
giudicata su una domanda sola: *questa cosa le permette di fare da sola
qualcosa che prima non riusciva a fare?*
