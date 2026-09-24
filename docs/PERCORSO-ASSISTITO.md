# Percorso assistito — dall'email al «inviata»

> Deliverable 2. Cosa succede, passo per passo, quando Maria apre la sua casella; e in fondo lo **script cronometrato della dimostrazione**.

Chi è Maria e perché il percorso è fatto così: [`PERSONA.md`](PERSONA.md).
Chi fa cosa dentro la pipeline: [`../agents/README.md`](../agents/README.md) §2.

---

## 1. Il percorso, dall'inizio alla fine

### Passo 0 · La lista

Maria apre `http://localhost:8123`. Una colonna, sei messaggi, niente cartelle e niente menu.

Ogni voce mostra mittente, oggetto, data — e **un pallino con una parola accanto** (`Puo' rispondere` / `Da controllare` / `Attenzione`). Il pallino **non è precalcolato nel corpus**: arriva dalla pipeline, che gira in secondo piano su ogni email appena la lista è disegnata (`valutaInSecondoPiano` in `app/frontend/app.js`). La seconda volta costa zero, perché lo stato è già a checkpoint.

In alto, sempre visibile: **«Risposte inviate da sola: N»**. È il contatore dell'autonomia, e cresce solo quando Maria preme davvero invia.

### Passo 1 · Apre l'email del medico

Tocca `em-01`. Un `POST /api/email/em-01/elabora` e l'orchestratore esegue la pipeline. Nella vista di lettura, **dall'alto verso il basso e in quest'ordine**:

| # | Blocco | Chi lo produce | Cosa vede Maria |
|---|---|---|---|
| 1 | **Semaforo** | agente 02 (`sicurezza`) | 🟢 *«Può rispondere tranquillamente.»* + pulsante **«Prepara una risposta»** |
| 2 | **In breve** | agente 04 (`semplificatore`) | *Chi le scrive:* «Studio medico dott.ssa Giulia Bianchi, per la sua salute» · *Cosa le chiedono:* «Le chiedono di confermare.» · *Entro quando:* «Entro il 10 ottobre 2026» |
| 3 | **Il messaggio** | agenti 04 + 05 | Il testo riscritto, con l'indice di leggibilità accanto. Sotto, il pulsante **«Mostra il testo originale»**: l'originale è sempre a un tocco |
| 4 | **Documenti allegati** | dal corpus | Nome e dimensione, in chiaro, in una scheda propria — invisibili nella UI di partenza |
| 5 | **Cosa vuole fare?** | agente 06 (`compositore`) | Tre pulsanti di intento |
| 6 | **Come ha ragionato il sistema** | orchestratore | Una riga per agente: modalità, esito, millisecondi, token, nota |

L'ordine non è estetico: **il verdetto di sicurezza precede sempre il contenuto.** Se l'email è una truffa, Maria lo sa prima di aver letto una parola del testo.

### Passo 2 · Sceglie cosa fare

Preme **«Confermo che vengo»**. Il riquadro bianco non compare mai: al suo posto appare una `<textarea>` **già compilata**.

```
Gentile Studio medico dott.ssa Giulia Bianchi,
le confermo che sarò presente all'appuntamento del 14 ottobre 2026 alle ore 09:30.

Cordiali saluti,
Maria Rossi
```

La data e l'ora nella bozza **non sono state riscritte da nessuno**: sono i fatti estratti dall'originale dall'agente 03 e sopravvissuti all'agente 05. Uno slot senza fatto corrispondente **si omette**: la frase si accorcia, non si inventa (`compositore._riferimento`).

Il testo è modificabile. Non è obbligatorio modificarlo.

### Passo 3 · Rilegge e invia

Sopra il riquadro c'è scritto *«La legga con calma. Se va bene, prema Invia.»*.

Preme **«Invia la risposta»** → `POST /api/email/em-01/invia` → il contatore in alto passa a **1**, e in una regione `aria-live` compare *«✓ Risposta inviata.»*.

> ★ **Non esiste alcun percorso nel codice in cui il sistema invii da solo.** L'endpoint di invio è separato dall'endpoint di elaborazione, non è raggiungibile dalla pipeline, e si attiva solo da un click. È il punto **HITL** esplicito dell'architettura, ed è coperto dal test `test_nessun_invio_automatico`.

### Passo 4 · L'email che non va aperta

Torna alla lista e tocca `em-03`, la finta Poste Italiane.

🔴 **«Non risponda a questa email. Sembra una truffa.»** e quattro segnali, ciascuno una frase in italiano:

- *Il nome dice «Poste Italiane» ma l'indirizzo non è quello ufficiale («poste-sicurezza-clienti.info»).*
- *C'è un collegamento che mostra «poste.it» ma porta a «poste-sicurezza-clienti.info».*
- *Chiede dati riservati (password o codici) che nessun ente chiede per email.*
- *Mette fretta per farle fare qualcosa senza pensarci.*

Il pulsante dice **«Chiami Poste Italiane al numero ufficiale — 803 160»**.

> ★ Quel numero **non viene dall'email**. Viene da `RECAPITI_UFFICIALI`, una tabella statica in `phishing_rules.py`. Su una mail di phishing, il numero scritto nel corpo è il numero del truffatore. È il vincolo più importante di quel file, ed è coperto dal test `test_il_numero_suggerito_viene_dalla_tabella_statica`.

Su rosso l'orchestratore **non chiama nemmeno il compositore**: non viene proposta nessuna bozza, perché a una truffa l'azione giusta è telefonare all'ente, non rispondere.

### Passo 5 · Le altre quattro

| Email | Cosa dimostra | Esito verificato |
|---|---|---|
| `em-02` Comune di Torino | Burocratese pesante (*«ai sensi e per gli effetti degli artt. 33 e 40 del D.P.R. 28 dicembre 2000, n. 445»*) + allegato PDF | 🟢 verde · 6 fatti protetti · semplificazione accettata |
| `em-04` INPS | Comunicazione **vera** che parla di soldi e assomiglia a una truffa: è il contrasto con `em-03` | 🟢 verde · importo `€ 1.247,83` protetto · è l'email dell'esperimento qui sotto |
| `em-05` Luca | Il nipote, in rubrica | 🟢 verde · **non semplificata**: «una persona conosciuta non scrive in burocratese». L'originale è già italiano semplice (Gulpease 76.0) |
| `em-06` Newsletter | Pubblicità | 🟡 giallo · categoria `commerciale`, messa in secondo piano · **nessuna bozza**: a una pubblicità non si risponde |

> `em-03` e `em-04` sono la coppia che porta il valore: **dicono entrambe *soldi* e *urgente*, ma una è falsa e una è vera.** È lì che si vede la differenza fra un assistente e un filtro antispam.

### Passo 6 · «E se l'AI sbaglia?»

In fondo alla vista di lettura c'è una scheda **«Strumenti per la dimostrazione»** con un solo pulsante. Non è nascosto, non è attivo per default, e il suo effetto è dichiarato in `agents/runtime/05-verificatore.md`, in questo file e in presentazione.

Premendolo su `em-04`, l'interfaccia richiama `POST /api/email/em-04/elabora?avvelena=true`. L'orchestratore corrompe l'output del semplificatore **subito prima della verifica** (`€ 1.247,83` → `€ 1.247`) e FactGuard fallisce dal vivo:

```
⚠  Non le mostro la versione semplificata
    L'importo non corrisponde all'originale: € 1.247,83 e' diventato € 1.247.
    → Le mostro il testo così come è arrivato.
```

Il ciclo riprova **due volte** con il feedback del verificatore (`MAX_SIMPLIFY_RETRIES = 2`), fallisce di nuovo — perché la corruzione è applicata a ogni tentativo — e la pipeline esce con `semplificazione_mostrata = False`. Nel pannello «Come ha ragionato» si contano le sei righe: tre tentativi di semplificazione, tre verifiche, tutte rifiutate.

**Maria non vede mai un testo sbagliato.** Vede l'originale, ed è comunque un risultato utile.

> Perché serve un pulsante: col semplificatore deterministico FactGuard **non fallirebbe mai in demo** (le regole ricopiano i fatti alla lettera), e un controllo che non si vede scattare viene letto come decorazione. In `LLM_MODE=replay` lo stesso rifiuto avviene **senza il pulsante**, perché una delle fixture del semplificatore è volutamente imperfetta.

---

## 2. Cosa cambia, in una riga

| | Oggi | Con Posta Chiara |
|---|---|---|
| L'email del medico | Riquadro bianco → chiude tutto | Tre pulsanti → rilegge → invia |
| Quando risponde | **Domenica**, quando viene Luca | **4 minuti** |
| La truffa di Poste | Indistinguibile dall'INPS | 🔴 + il numero verde **ufficiale** |
| Chi decide | Il nipote | Maria |

In interfaccia il guadagno è un numero, non un aggettivo: **«Risposte inviate da sola: 3»**.

---

## 3. Script della dimostrazione — cronometrato

**Durata della parte dal vivo: 2 minuti e 30.** Il resto dei 5 minuti sta nel deck (`presentation/index.html`).
**Due persone:** chi **parla** e chi **clicca**. Non si invertono i ruoli a metà.

### Prima di cominciare — 60 secondi di preparazione, obbligatori

- [ ] `uvicorn app.backend.main:app --port 8123` già in esecuzione, **`--reload` spento**.
- [ ] Browser già su `http://localhost:8123`, **lista caricata e pallini già colorati** (la prima elaborazione non si fa davanti alla giuria: dopo è a checkpoint e risponde subito).
- [ ] Zoom del browser al 100%, finestra a tutto schermo, notifiche di sistema spente.
- [ ] Wi-Fi **staccato**. Non è una precauzione: è parte dell'argomento.
- [ ] Screenshot di backup di ogni schermata aperti in una seconda finestra.

### La sequenza

| Tempo | Chi clicca | Cosa fa | Cosa si vede | Cosa dice chi parla |
|---:|---|---|---|---|
| **0:00** | — | Si parte dalla lista | Sei email, un pallino con una parola ciascuna | *«Questa è la casella di Maria, 74 anni. I pallini non sono nel file: li ha appena calcolati la pipeline.»* |
| **0:10** | clicca | Apre **`em-01`** (dott.ssa Bianchi) | Verde in cima, **Chi / Cosa / Entro quando**, testo riscritto | *«È il caso in cui oggi si ferma. Prima cosa: è sicura. Seconda: cosa le chiedono, in tre righe.»* |
| **0:30** | clicca | Preme **«Confermo che vengo»** | La bozza compare già compilata con 14 ottobre e 9:30 | *«Il riquadro bianco non compare mai. La data e l'ora non le ha scritte un modello: sono i fatti estratti dall'originale e verificati.»* |
| **0:45** | clicca | Preme **«Invia la risposta»** | *✓ Risposta inviata* · il contatore in alto passa a **1** | *«L'ultimo click è sempre suo. Nel codice non esiste un percorso che invii da solo.»* |
| **0:55** | clicca | Torna alla lista, apre **`em-03`** (finta Poste) | 🔴 + quattro segnali + **«Chiami Poste Italiane — 803 160»** | *«Quel numero non viene dall'email: viene da una tabella nel codice. Nel corpo di una mail di phishing, il numero è del truffatore.»* |
| **1:15** | clicca | Torna alla lista, apre **`em-04`** (INPS) | 🟢 + il testo semplificato con l'importo **€ 1.247,83** intatto | *«Questa dice soldi e urgente esattamente come la precedente. Ma è vera. È qui che si vede la differenza.»* |
| **1:30** | clicca | Scorre in fondo e preme **«E se l'AI sbaglia?»** | ⚠ **Verifica fallita**, importo `€ 1.247,83` → `€ 1.247`, viene mostrato l'originale | *«Abbiamo corrotto di proposito la semplificazione. FactGuard è codice deterministico, non un modello: se ne accorge, rifiuta, e Maria vede l'originale. Il motore propone, il verificatore controlla, la persona decide.»* |
| **1:55** | clicca | Apre **«Come ha ragionato il sistema»** | Tre tentativi di semplificazione, tre verifiche, tutte rifiutate, token a zero | *«Ogni riga è un agente. Modalità, esito, millisecondi, token. Il sistema è ispezionabile, non magico — e il totale dei token è zero.»* |
| **2:15** | — | Ferma lì | Il contatore in alto | *«Prima: domenica prossima. Ora: quattro minuti. E il Wi-Fi è staccato da quando abbiamo cominciato.»* |
| **2:30** | — | Torna al deck | — | — |

### Se qualcosa non gira

| Guasto | Rimedio, senza commentarlo ad alta voce |
|---|---|
| Il server non risponde | Si passa agli screenshot di backup e si continua a parlare. La sequenza è la stessa |
| Un'email è lenta al primo click | Non succede se la lista è stata precaricata. Se succede: si parla del contatore di autonomia mentre carica |
| Il pulsante avvelenato non scatta | Verificare di essere su `em-04`: la corruzione agisce sull'importo dell'INPS. Su un'altra email non c'è niente da corrompere |
| Domanda *«ma dov'è l'AI?»* a metà demo | Risposta pronta, 15 secondi: *«L'AI ha scritto tutto il sistema. A runtime il default è deterministico di proposito, e la seam LLM ve la mostriamo attraversata su output di esempio: non abbiamo registrato chiamate API perché non volevamo una chiave in un repository pubblico.»* Poi si riprende da dove si era |

### La variante `replay`, se c'è tempo e se la domanda arriva

```powershell
$env:LLM_MODE = "replay"
uvicorn app.backend.main:app --port 8123
```

Stesso percorso, stessa macchina, **stessa rete staccata**. Nel pannello «Come ha ragionato» la colonna *Modalità* passa da `regole` a `llm-replay` e la colonna *Token* smette di essere zero. È la prova che la seam è completa: cambia il valore di una variabile d'ambiente, non una riga di codice.

Cosa sono le fixture, detto con le parole esatte: **output di esempio scritti durante lo sviluppo, non registrazioni di chiamate API** — vedi [`../README.md`](../README.md) e [`AUTONOMIA-E-LIMITI.md`](AUTONOMIA-E-LIMITI.md).
