# dev-corpus

> Esiste perché una demo si vince o si perde sui dati: sei email scelte male mostrano un prodotto
> che funziona su niente, e sei email scelte bene fanno scattare in diretta ogni meccanismo che il
> resto del sistema si limiterebbe a dichiarare.

## Scopo

Scrivere il corpus di demo: **sei email**, realistiche e **dichiaratamente fittizie**, costruite
in modo che ciascuna esista per far vedere una capacità diversa del prodotto — e che la coppia
phishing/INPS mostri il caso in cui il valore è massimo.

Il corpus **non è colore narrativo**: è l'insieme di test end-to-end del prodotto, e ogni campo di
ogni email è scelto per un motivo tecnico.

## Confine di file

Scrive **soltanto**:

- `app/backend/data/mailbox.json`

Non tocca nessun altro file. Non tocca codice, quindi può girare **in parallelo con chiunque**
(vedi [`../../workflow.md` §1](../../workflow.md)). Gli allegati sono **dichiarati nel JSON**, non
depositati come file binari.

## Input

| Artefatto | Cosa ne ricava |
|---|---|
| `app/backend/contracts.py` → `Email`, `Allegato` | La forma esatta dei record: nessun campo in più, nessuno in meno |
| `app/backend/clock.py` → `OGGI_DEFAULT = 2026-10-06` (martedì) | L'ancora temporale di ogni data del corpus |
| [`../../runtime/03-estrazione-fatti.md`](../../runtime/03-estrazione-fatti.md) | Quali forme di data, importo e orario il motore riconosce |
| [`../../runtime/routing.md`](../../runtime/routing.md) §3 | Le regole di non-chiamata, che dipendono da lunghezza del corpo, rubrica e categoria |

## Output

`app/backend/data/mailbox.json` — un array di oggetti conformi a `Email`. Consumato da
`dev-pipeline` (esecuzione), `dev-frontend` (rendering), `test-engineer` (test di corpus),
`dev-deck` (screenshot).

## ★ Le sei email

`OGGI` è **martedì 6 ottobre 2026**. Tutte le date del corpus sono coerenti con quell'ancora: la
visita del 14 ottobre cade di **mercoledì**, la domenica di Guada è l'**11**.

| # | `id` | Mittente | Contenuto | Esiste per mostrare |
|---|---|---|---|---|
| 1 | `e01-bianchi` | dott.ssa Bianchi, medico di base | Conferma della visita di **mercoledì 14 ottobre, ore 9:30** | ★ Il caso principale: la **risposta guidata**. È il punto esatto in cui Maria oggi si ferma |
| 2 | `e02-comune` | Comune di Torino | Certificato di residenza, **PDF allegato**, burocratese pesante con articoli e commi | Allegati in chiaro + traduzione del burocratese |
| 3 | `e03-poste-falsa` | «Poste Italiane» da `no-reply@poste-sicurezza-clienti.info` | *"Conto bloccato, verifica entro 24 ore"*, link mascherato | ★ Semaforo **rosso** + azione: il numero verde ufficiale |
| 4 | `e04-inps` | INPS | Cedolino della pensione, importo **€ 1.247,83** | ★ FactGuard e l'**email avvelenata** |
| 5 | `e05-Guada` | Guada, nipote, **in rubrica** | *"Nonna, domenica vengo a pranzo"* | Semaforo **verde** — il contrasto che rende credibile il rosso |
| 6 | `e06-newsletter` | Newsletter di un supermercato | Promozioni della settimana | Triage: `commerciale`, in secondo piano |

### ★ La coppia 3 + 4 è il cuore della demo

Le email 3 e 4 dicono **entrambe** *soldi* e *urgente*. Una è vera, una è falsa. È l'unico punto in
cui si vede il valore del prodotto invece di sentirselo raccontare: non serve spiegare perché un
semaforo serva, basta metterle una accanto all'altra.

Conseguenza sulla scrittura: **devono somigliarsi**. Se la falsa è scritta in un italiano
sgrammaticato e la vera in italiano istituzionale, il confronto è truccato e la giuria se ne
accorge. La falsa deve essere plausibile; a tradirla sono il **dominio**, il **link mascherato** e
il **lessico d'urgenza**, cioè esattamente i tre segnali che `phishing_rules.py` sa spiegare.

### Dettagli che devono esserci perché qualcosa li usi

| Dettaglio da inserire | Chi lo usa |
|---|---|
| Un **numero civico** (es. *via Cibrario 22*) e un **CAP** (es. *10143*) in e01 o e02 | Dimostrano che FactGuard **non** li estrae. È il falso positivo più probabile: va esibito, non evitato |
| Un **numero di protocollo** inventato (es. *Prot. 2026/14785*) in e02 | Stessa ragione: contiene una cifra che somiglia a un anno |
| Date in **forme diverse** fra le email (`14 ottobre`, `14/10/2026`, `entro il 10 ottobre`) | `normalize.py` e i test di equivalenza |
| L'importo **€ 1.247,83** in e04, scritto una sola volta e in quella forma | La fixture imperfetta e la corruzione di demo si aggrappano a quella stringa |
| `in_rubrica: true` **solo** su e05 | Regola di non-chiamata e semaforo verde |
| Un `Allegato` di tipo `pdf` **solo** su e02 | La schermata «C'è un foglio allegato» |
| `data_ricezione` distribuite fra il 3 e il 6 ottobre 2026 | Ordinamento della lista; l'orario notturno di e03 è un segnale in più |

### Il vincolo di lunghezza — non è estetico

[`routing.md`](../../runtime/routing.md) §3 stabilisce che, in `replay`, **2 email su 6**
attraversano davvero una seam LLM; il resto è servito dalle regole a costo zero, ed è un numero
dichiarato in `docs/TOKEN-EFFICIENCY.md`.

Quel numero è una conseguenza diretta di come è scritto il corpus: e03 è rossa, e06 è commerciale,
e05 è in rubrica e sotto i 200 caratteri. Restano **e02 ed e04**, che devono essere le uniche con
un corpo lungo e burocratico. **Il corpo di e01 resta sotto i 200 caratteri** — uno studio medico
scrive corto — altrimenti le email che attraversano la seam diventano tre e la documentazione
smette di corrispondere al comportamento.

## Passi

1. Leggi `Email` e `Allegato` in `contracts.py`. Il JSON usa **quei nomi di campo**, e nessun campo
   extra: un campo che nessun modello legge è un campo che mente.
2. Scrivi le sei email nell'ordine della tabella, con `id` parlanti (`e01-bianchi` …).
3. Ancora ogni data a `OGGI = 2026-10-06`, verificando il giorno della settimana quando il testo lo
   nomina («mercoledì 14 ottobre», «domenica»).
4. Inserisci i dettagli della tabella «dettagli che devono esserci»: civico, CAP, protocollo, forme
   di data diverse, importo.
5. Conta i caratteri del corpo di ogni email e confronta con le soglie di `routing.md` §3.
6. Rileggi con l'occhio di chi cerca dati veri: nessun indirizzo esistente riconducibile a una
   persona, nessun IBAN, nessun codice fiscale, nessun numero di telefono reale.
7. Carica il file con `json.load` e valida ogni record contro `Email`. Un corpus che non valida
   fa fallire la pipeline all'avvio, non in fase di test.

## Vincoli

- **Dichiaratamente fittizio.** Protocolli inventati, domini inventati, nessun dato personale
  reale, nessun indirizzo o recapito riconducibile a una persona esistente.
- **Nessun consiglio medico, fiscale o legale** nel testo delle email né nella loro
  semplificazione. Il prodotto dice **cosa c'è scritto**, non **cosa fare**.
- **Nessun dato reale di enti**: numeri verdi e riferimenti devono essere plausibili ma dichiarati
  come fittizi nel README del corpus. Il numero verde mostrato dall'azione del semaforo rosso è
  l'unico caso in cui plausibilità e realtà vanno trattate con cura.
- **Mai `date.today()` mentalmente**: ogni data si calcola rispetto a `clock.OGGI_DEFAULT`, mai
  rispetto al giorno in cui si scrive.
- **Non si tocca il codice.** Se un formato di data del corpus non viene riconosciuto, si segnala a
  `dev-core` tramite il `team-leader`; non si modifica `normalize.py`, e nemmeno si «aggiusta» il
  corpus per nascondere un buco del motore — quel buco è un test che manca.
- **UTF-8 obbligatorio**, e il file va scritto con lo strumento Write o con Python
  `encoding='utf-8'`. **Mai generare il corpus via shell:** `Set-Content` di PowerShell 5.1 scrive
  in ANSI e gli accenti italiani diventano mojibake su tutte e sei le email.
- **Sei email, non sette.** Ogni email in più è una schermata in più da controllare a T+2:30.

## Fallback

| Situazione | Azione |
|---|---|
| Il tempo stringe | Si scrivono **prima** e01, e03 ed e04: sono le tre che reggono la demo. e02, e05 ed e06 sono contorno |
| Un'email non produce il comportamento atteso dal motore | Si segnala al `team-leader` e si **lascia il corpus com'è**: è il motore a doversi adeguare, non i dati a doversi ammorbidire |
| Un formato di data non viene normalizzato | Si annota come limite noto e si usa una forma supportata, registrando la cosa: un formato taciuto diventa un bug scoperto sul palco |
| Il JSON non valida contro `Email` | Si corregge immediatamente: è l'unico errore di questo agente che ferma tutti gli altri |
| Lo stesso problema si ripresenta due volte | Escalation al `team-leader`, senza terza iterazione |

## Definizione di "fatto"

- [ ] `app/backend/data/mailbox.json` contiene esattamente **6** record, tutti validi contro `Email`.
- [ ] Nessun campo fuori dal contratto; `allegati` popolato solo su `e02-comune`, `in_rubrica: true`
      solo su `e05-Guada`.
- [ ] Ogni data del corpus è coerente con `OGGI = 2026-10-06`: il 14 ottobre è mercoledì, l'11 è
      domenica.
- [ ] `e04-inps` contiene la stringa `€ 1.247,83` **una sola volta** e in quella forma.
- [ ] `e03-poste-falsa` ha mittente `no-reply@poste-sicurezza-clienti.info`, un link mascherato e
      lessico d'urgenza — e un testo plausibile, non caricaturale.
- [ ] Il corpus contiene un numero civico, un CAP e un numero di protocollo, e **nessuno dei tre**
      viene estratto come `Fatto`.
- [ ] Il corpo di `e01-bianchi` è sotto i 200 caratteri; `e02` ed `e04` sono le uniche con corpo
      lungo e burocratico.
- [ ] Il file si apre in UTF-8 senza mojibake: `à`, `è`, `ì`, `ò`, `ù`, `€` corretti.
- [ ] Nessun dato reale riconducibile a una persona; nessun consiglio medico, fiscale o legale.
