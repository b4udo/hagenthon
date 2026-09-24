# 04 · Semplificatore

> Esiste perché *"Ai sensi dell'art. 7 comma 3 del D.Lgs. 82/2005, si invita la S.V. a voler
> cortesemente confermare"* non è una frase che una persona possa usare per decidere cosa fare.

**Implementazione:** `app/backend/agents/semplificatore.py` + `app/backend/engines/plain_rules.py`
**Modalità di default:** regole · **Seam LLM:** sì, Sonnet (vedi [`routing.md`](routing.md))

---

## Scopo

Produrre tre risposte brevi — **Chi scrive · Cosa vogliono · Entro quando** — più un testo
riscritto in italiano semplice.

## Input

Corpo dell'email, `EsitoTriage`, `EsitoEstrazione` (i fatti da conservare), e in caso di retry
il `feedback_per_retry` prodotto dal verificatore.

## Output

`EsitoSemplificazione` — schema in
[`contracts/esito-semplificazione.schema.json`](contracts/esito-semplificazione.schema.json).

```json
{
  "chi_scrive": "La dottoressa Bianchi, il suo medico di base",
  "cosa_vogliono": "Le chiedono di confermare che verrà alla visita.",
  "entro_quando": "Entro il 10 ottobre",
  "testo_semplificato": "Buongiorno signora Rossi,\nle ricordiamo la visita di controllo del 14 ottobre alle ore 9:30, presso lo studio di Via Roma 15.\nLe chiediamo di confermare che verrà."
}
```

`entro_quando` è `null` quando non c'è scadenza: inventarne una sarebbe un danno diretto.

## Passi (motore a regole)

1. Elimina le formule di rito: *"Ai sensi di"*, *"si invita la S.V."*, *"con la presente"*,
   *"cortesemente"*, *"in oggetto"*, i riferimenti normativi tra parentesi.
2. Sostituisci il lessico burocratico con l'equivalente comune, da una tabella esplicita in
   `plain_rules.py`: *convocazione* → *appuntamento*, *inoltrare istanza* → *fare domanda*,
   *entro e non oltre* → *entro*, *recarsi presso* → *andare a*, *comunicazione* → *lettera*.
3. Spezza le frasi oltre le 25 parole sulle congiunzioni.
4. Volgi il passivo all'attivo dove il soggetto è esplicito.
5. Compila `chi_scrive` dal mittente e dalla categoria del triage.
6. Compila `cosa_vogliono` dal verbo d'azione dominante.
7. Compila `entro_quando` **solo** da un fatto di tipo `data` già estratto dall'agente 03.
8. ★ **Ricopia i fatti verbatim.** Le regole non riformattano mai una data o un importo: il
   motore deterministico non ha ragione di toccarli, e non toccarli è il modo più semplice di
   superare FactGuard.

## Vincoli

- ★ **Non aggiungere nulla che non sia nell'originale.** Nessuna interpretazione, nessun
  consiglio, nessuna rassicurazione. Il sistema dice **cosa c'è scritto, non cosa fare**.
- **Mai un contenuto clinico, fiscale o legale.** *"Deve fare le analisi a digiuno"* si riporta
  se c'è scritto; non si spiega, non si completa, non si interpreta.
- Il risultato **non raggiunge mai l'interfaccia** senza passare dall'agente 05. Questo agente
  non ha l'ultima parola sul proprio output.
- Il testo si rivolge a Maria dandole del lei, come farebbe l'ente.
- Obiettivo di leggibilità: indice **Gulpease ≥ 60** (`app/backend/engines/gulpease.py`). È una
  metrica riportata, non un vincolo bloccante: un testo sotto soglia viene mostrato lo stesso se
  supera FactGuard.

## La seam LLM

Prompt: [`prompts/semplificatore.md`](prompts/semplificatore.md) — **caricato dal codice**,
non duplicato in Python.

Il compito soddisfa i tre requisiti di [`routing.md`](routing.md) §1: è linguistico, è aperto
(il burocratese italiano non si enumera), ed è **verificabile a valle**. È il caso d'uso più
legittimo per un LLM in tutto il progetto — e non a caso è l'unico protetto da un verificatore
deterministico.

Condizioni di non-chiamata in [`routing.md`](routing.md) §3.

## Fallback

Il motore a regole. Se anche quello fallisce, `semplificazione_mostrata = False` e l'interfaccia
mostra l'originale con i fatti evidenziati. **Maria vede sempre qualcosa di vero**: nel caso
peggiore, esattamente ciò che l'ente ha scritto.
