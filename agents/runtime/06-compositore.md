# 06 · Compositore

> Esiste perché **è il punto esatto in cui Maria si ferma.** Ha aperto l'email della dottoressa,
> ha premuto Rispondi, e si è trovata davanti a un riquadro bianco vuoto. Non sa cosa scrivere né
> dove. Chiude tutto e aspetta domenica, quando viene Luca.

**Implementazione:** `app/backend/agents/compositore.py`
**Modalità di default:** regole · **Seam LLM:** sì, Sonnet (vedi [`routing.md`](routing.md))

---

## Il ribaltamento

Il riquadro bianco chiede *"cosa vuoi scrivere?"* — una domanda a cui Maria non sa rispondere
per iscritto, anche quando sa benissimo cosa vuole dire. Lo dimostra il fatto che usa i vocali
di WhatsApp ogni giorno: **sa parlare, non digitare.**

Il compositore cambia la domanda in *"cosa vuoi fare?"*, e offre **tre pulsanti**.
La risposta si **sceglie**, non si scrive.

## Input

`Email`, `EsitoTriage`, e i `Fatto` estratti dall'agente 3 **dal testo originale**.

> ★ **Precisazione che conta.** L'agente 05 non filtra i fatti: verifica che il *testo
> semplificato* li abbia conservati. I fatti restano dunque quelli dell'originale anche quando
> FactGuard rifiuta la semplificazione — ed è giusto così, perché la data da mettere nella
> risposta dev'essere quella vera, non quella sopravvissuta a una riscrittura. «Slot riempiti
> solo con fatti verificati» qui significa **estratti e ancorati dall'agente 3**, mai dedotti
> dal modello.

## Output

`list[BozzaRisposta]` — schema in
[`contracts/bozza-risposta.schema.json`](contracts/bozza-risposta.schema.json).

```json
[
  {
    "intento": "conferma",
    "etichetta": "Confermo che vengo",
    "testo": "Gentile dottoressa Bianchi,\nle confermo che sarò presente alla visita del 14 ottobre alle ore 9:30.\nCordiali saluti,\nMaria Rossi",
    "fatti_usati": [
      { "tipo": "data",   "valore_normalizzato": "2026-10-14" },
      { "tipo": "orario", "valore_normalizzato": "09:30" }
    ]
  }
]
```

## I tre intenti — e perché esattamente tre

| Intento | Etichetta | Copre |
|---|---|---|
| `conferma` | "Confermo che vengo" / "Va bene" | Il caso maggioritario nella posta di un ente |
| `chiedi_info` | "Ho bisogno di più informazioni" | Quando non ha capito o manca un dato |
| `non_posso` | "Non posso, chiedo di spostare" | Il rifiuto, che è la cosa più difficile da scrivere da soli |

Tre è il numero massimo di scelte che si leggono in un colpo d'occhio, ed è il minimo che copre
lo spazio reale delle risposte a una convocazione. Con cinque pulsanti, il riquadro bianco
diventa un menù: si è spostato il problema, non risolto.

L'etichetta è **in prima persona e al presente** — *"Confermo che vengo"*, non *"Conferma"*.
Maria deve riconoscere la propria intenzione, non selezionare un comando.

## Passi

1. Scegli gli intenti applicabili in base al triage. Un'email informativa senza richiesta non
   genera `conferma`.
2. Prendi il modello di testo dell'intento da una tabella in `compositore.py`.
3. ★ **Riempi gli slot solo con fatti verificati.** Uno slot senza fatto corrispondente **si
   omette**: la frase si accorcia, non si inventa.
4. Apri con la formula adatta al destinatario (`Gentile dottoressa`, `Spettabile ufficio`, `Ciao`
   per chi è in rubrica).
5. Firma con il nome dell'utente.
6. Registra in `fatti_usati` quali fatti sono finiti nel testo — è ciò che rende la bozza
   verificabile a colpo d'occhio nell'interfaccia.

## Vincoli

- ★ **Nessun invio automatico. Mai, in nessun caso, per nessun intento.** Il compositore produce
  una bozza; l'ultimo click è sempre di Maria. È il vincolo più importante del prodotto e il
  punto HITL esplicito dell'architettura.
- ★ **Nessuno slot inventato.** Se il fatto non è tra quelli verificati, la frase si riformula
  senza. Una bozza che afferma un orario sbagliato **a nome di Maria** è molto peggio di una
  bozza vaga.
- **Nessuna bozza su semaforo rosso.** L'orchestratore non chiama nemmeno questo agente: su
  un'email di phishing l'azione giusta è telefonare all'ente, non rispondere.
- Niente impegni che Maria non ha preso: nessun *"sarò lì in anticipo"*, nessun *"provvederò
  al pagamento"*.
- Il testo è **breve**. Deve stare sullo schermo senza scorrere, perché va riletto prima di
  inviare, e una bozza che non si rilegge non è stata approvata davvero.

## La seam LLM

Prompt: [`prompts/compositore.md`](prompts/compositore.md) — **caricato dal codice**.

Il vincolo sugli slot vale identico nella seam: il prompt riceve **solo** i fatti verificati e
ha l'istruzione esplicita di non introdurre date, orari o importi che non siano nella lista.
L'output è comunque ricontrollato prima di essere mostrato.

## Fallback

I modelli di testo a regole, che sono il default. Se anche quelli falliscono, l'interfaccia
mostra i tre pulsanti con un testo minimo (*"Confermo. Maria Rossi"*) ed è comunque un percorso
completabile: **meglio una bozza spoglia che un riquadro bianco.** È letteralmente il problema
da cui è nato il prodotto.
