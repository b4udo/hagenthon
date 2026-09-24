# /nuova-email

> Aggiungere un'email al corpus non è aggiungere un record: è toccare un dato da cui dipendono
> fixture, stato su disco, test e screenshot — e questo comando esiste perché nessuno dei quattro
> venga dimenticato.

## Quando usarlo

- Serve un caso che il corpus attuale non copre (un formato di data, un segnale di phishing, un
  tipo di allegato).
- La demo è cambiata e serve una schermata diversa.
- Un test di `test-engineer` richiede un dato che oggi non esiste in `mailbox.json`.

**Quando NON usarlo:** dopo il **feature freeze** a T+2:30. Da lì, aggiungere un'email significa
rigenerare fixture e screenshot con venti minuti a disposizione. Se manca un caso a quel punto,
diventa un limite noto, non una modifica.

Il comando lo esegue **`dev-corpus`**, che possiede `app/backend/data/mailbox.json`. Le
rigenerazioni a valle sono deleghe del `team-leader` ai proprietari dei rispettivi confini.

## Cosa fa

1. **Legge `Email` e `Allegato` in `app/backend/contracts.py`** e usa quei nomi di campo. Nessun
   campo extra.
2. **Assegna un `id` parlante** nella serie esistente (`e07-…`) e verifica che non collida.
3. **Scrive il record** in `app/backend/data/mailbox.json`, con le date ancorate a
   `clock.OGGI_DEFAULT` — **martedì 6 ottobre 2026** — e mai al giorno corrente reale. Se il testo
   nomina un giorno della settimana, lo si verifica sul calendario di quell'ancora.
4. **Controlla lo scope di FactGuard:** se il testo contiene un civico, un CAP, un protocollo o un
   numero di telefono, va bene — devono restare **non estratti**. Se contiene una data, un importo
   o un orario, devono essere **ancorati a una parola chiave entro 40 caratteri**, altrimenti non
   verranno estratti e la nuova email non dimostrerà nulla.
5. **Conta i caratteri del corpo** e confronta con le soglie di
   [`../../runtime/routing.md`](../../runtime/routing.md) §3. Questo determina se la nuova email
   attraverserà una seam LLM in `replay` — e quindi se servono fixture.
6. **Valida** il file: `json.load` più validazione di ogni record contro `Email`.
7. **Rigenera ciò che ne dipende**, in quest'ordine:
   - **Fixture** (`dev-core`) — solo se il passo 5 dice che l'email attraversa una seam. La chiave
     è l'hash di `(modello + prompt + input normalizzato)`: cambiando l'input serve un file nuovo,
     quello vecchio non si trova più.
   - **Stato su disco** — si cancella `app/backend/state/data/` per intero. Un checkpoint vecchio
     serve un risultato calcolato su un corpus diverso, ed è il modo più rapido per passare
     mezz'ora a inseguire un bug che non esiste.
   - **Test di corpus** (`test-engineer`) — se la nuova email esiste per dimostrare un
     comportamento, quel comportamento va asserito.
   - **Screenshot** (`dev-frontend` → `presentation/img/`) — se la lista compare in una slide,
     l'immagine è cambiata.
8. **Riesegue** `pytest -q` e il percorso completo su `localhost:8123`.

## Output atteso

- `app/backend/data/mailbox.json` con un record in più, valido contro `Email`.
- `app/backend/state/data/` vuota.
- Eventuali fixture nuove in `app/fixtures/llm/`, con **solo** `model`, `content`, `usage`.
- `pytest -q` verde.
- L'email compare nella lista a `localhost:8123` con badge e semaforo coerenti, e la sua pipeline
  gira fino in fondo.
- Screenshot aggiornati, se la nuova email è visibile in presentazione.

## Fallimenti tipici

| Sintomo | Causa | Rimedio |
|---|---|---|
| Accenti diventati `Ã¨`, `â‚¬` | Il file è stato scritto via `Set-Content` di PowerShell, che di default scrive in ANSI | Riscrivere con lo strumento Write o con Python `encoding='utf-8'`. **Mai generare il corpus via shell** |
| La pipeline restituisce un risultato vecchio | `state/data/<id>.json` esiste ancora | Cancellare la cartella. È il passo 7 e si dimentica sempre |
| In `replay` la seam degrada a regole con un log rumoroso | La fixture non esiste per il nuovo input: la chiave hash è cambiata | Scrivere la fixture nuova, o accettare il degrado e dichiararlo |
| La nuova data non viene estratta | Manca l'ancora entro 40 caratteri, oppure il formato non è fra quelli supportati | Riformulare la frase con `entro`, `scadenza`, `appuntamento`, `ore`. **Non** modificare `normalize.py`: non è il confine di `dev-corpus` |
| Un civico viene estratto come fatto | Regressione in `fact_extract.py` | Segnalare a `dev-core` tramite il `team-leader`. Non ammorbidire il corpus per nasconderla |
| Le email che attraversano una seam diventano tre | Il corpo della nuova email supera le soglie di `routing.md` §3 | Accorciare il corpo, oppure aggiornare il numero dichiarato in `docs/TOKEN-EFFICIENCY.md`. Una documentazione che non corrisponde al comportamento è peggio di nessuna |
| Un test rosso viene «sistemato» allentando l'asserzione | Confine violato: `dev-corpus` non tocca `app/tests/` | Segnalare al `team-leader`, che delega a `test-engineer` |
