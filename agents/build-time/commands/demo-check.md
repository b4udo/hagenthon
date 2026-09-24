# /demo-check

> Esiste perché le demo non falliscono sul codice: falliscono su un server già in ascolto, un
> checkpoint vecchio, una cartella sbagliata o una rete che in sala non c'è — e perché scoprirlo
> cinque minuti prima di parlare costa molto meno che scoprirlo mentre si parla.

## Quando usarlo

- Dopo il **feature freeze** (T+2:30), come primo passo della fase di verifica.
- **Sulla macchina della demo**, non su quella di sviluppo, se sono diverse.
- **Prima di ogni prova a voce col cronometro** e un'ultima volta poco prima di entrare in sala.
- Dopo qualunque modifica al corpus o alle fixture (vedi
  [`nuova-email.md`](nuova-email.md)).

Lo esegue `qa-critic` nella fase di verifica, e la persona prima della presentazione.

## Cosa fa

Dieci controlli, in quest'ordine. **Il primo che fallisce ferma la sequenza**: i successivi
darebbero esiti inaffidabili.

1. **Ambiente pulito.** Attiva `.venv`, verifica che nessun processo sia già in ascolto sulla
   porta **8123**, cancella `app/backend/state/data/`. Un checkpoint calcolato su un corpus
   precedente è il modo più rapido per inseguire un bug che non esiste.
2. **`pytest -q` verde**, senza variabili d'ambiente impostate a mano. Poi di nuovo con
   `LLM_MODE=replay`. Due esecuzioni, due esiti verdi.
3. **Il server parte** su `http://localhost:8123` con `--reload` **spento**, e la pagina si carica
   al primo colpo.
4. **Le sei email caricano.** La lista mostra mittente, oggetto, badge di provenienza e semaforo
   per tutte e sei. Nessun record mancante, nessun accento in mojibake.
5. **Il percorso di Maria si completa**: apri l'email della dott.ssa Bianchi, leggi il semplificato
   con Chi scrive · Cosa vogliono · Entro quando, scegli *Confermo*, rileggi la bozza, invia.
   Rifallo **solo con la tastiera**.
6. ★ **L'email avvelenata fa scattare FactGuard dal vivo.** Sull'email INPS, premi
   «E se l'AI sbaglia?». Deve comparire a schermo il rifiuto, con l'originale `€ 1.247,83` accanto
   alla versione corrotta `€ 1.247`, e la semplificazione deve essere **scartata** a favore
   dell'originale. È la dimostrazione più importante dei cinque minuti: se questa non gira, non
   gira la presentazione.
7. **Il semaforo rosso porta un'azione.** Apri la falsa Poste: verdetto rosso, motivazione
   leggibile, e il pulsante col numero verde ufficiale. Nessuna bozza di risposta proposta.
8. ★ **Con il Wi-Fi staccato**, davvero staccato: ripeti i passi 3, 4, 5 e 6 in `LLM_MODE=off`,
   poi **di nuovo** in `LLM_MODE=replay`. In `replay` il rifiuto di FactGuard sull'INPS deve
   avvenire **anche senza** il pulsante da presentatore, perché una delle fixture del
   semplificatore è volutamente imperfetta.
9. **La presentazione si apre** con doppio clic su `presentation/index.html`, sempre a rete
   staccata, e le 11 slide scorrono con le frecce. Gli screenshot si vedono.
10. **Il piano B è pronto:** gli screenshot di backup di ogni schermata sono sulla macchina della
    demo, in una cartella che si apre in due clic, e il browser è già sulla pagina giusta con lo
    zoom impostato per la proiezione.

## Output atteso

- **10 controlli con esito**, in ordine, nessuno saltato.
- Il server in ascolto su 8123, con `--reload` spento.
- `pytest -q` verde in entrambe le modalità.
- Il rifiuto di FactGuard visibile a schermo e **leggibile a distanza di proiezione** — non solo
  presente nel DOM.
- Tutto ripetuto e funzionante **con la rete fisicamente staccata**, in `off` e in `replay`.
- Gli screenshot di backup accessibili in due clic.

## Fallimenti tipici

| Sintomo | Causa | Rimedio |
|---|---|---|
| La pagina si carica ma le route `/api` danno 404 | `StaticFiles` è stato montato **prima** delle route: montato su `/` per primo, le inghiotte tutte | Rimontarlo per ultimo. È il primo posto da guardare, sempre |
| Il browser mostra una versione vecchia del JavaScript | Manca `Cache-Control: no-store` in sviluppo | Aggiungere l'intestazione. Senza, si perdono venti minuti a debugare codice già corretto |
| Il server non parte, porta occupata | Un'istanza precedente è ancora viva | Chiudere il processo sulla 8123. Non cambiare porta «per fare prima»: la 8123 è quella provata |
| La pipeline restituisce un risultato che non corrisponde al codice attuale | Checkpoint vecchio in `state/data/` | Cancellare la cartella. È il passo 1 e si salta sempre |
| Accenti in mojibake nella lista | Un file è stato scritto in ANSI da `Set-Content` | Riscriverlo in UTF-8 |
| In `replay` FactGuard non scatta senza il pulsante | La fixture imperfetta non viene trovata: la chiave hash non corrisponde all'input | Ricalcolare la chiave con la stessa funzione del client. Finché non torna, in demo si usa il pulsante |
| Con il Wi-Fi staccato qualcosa non si carica | Un riferimento a una CDN è rientrato in HTML o nel deck | Rimuoverlo e sostituirlo con un font di sistema |
| Tutto gira in sviluppo e niente sulla macchina della demo | Il controllo è stato fatto sulla macchina sbagliata | Rieseguire il comando dove si presenterà. È l'unico posto in cui l'esito conta |
| Il rifiuto si vede sullo schermo del portatile ma non dal fondo della sala | Dimensione e contrasto tarati sul monitor | Ingrandire e riprovare in proiezione |
