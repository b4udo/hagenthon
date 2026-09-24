# dev-deck

> Esiste perché un progetto valutato in cinque minuti non viene valutato per quello che è, ma per
> quello che si riesce a mostrare — e perché un deck scritto alla fine racconta ciò che si ricorda,
> mentre uno che cresce insieme al prodotto racconta ciò che esiste davvero.

## Scopo

Costruire `presentation/index.html`: **11 slide, 5 minuti**, brand Accenture, con screenshot
**veri** del prodotto man mano che compaiono.

`dev-deck` parte a **T+1:00** e gira in parallelo con tutto il resto fino al freeze: non tocca
codice, quindi non può collidere con nessuno (vedi [`../../workflow.md` §1](../../workflow.md)).
Partire presto non è ottimismo: è l'unico modo perché alle 2:50 ci sia da **rifinire** invece che
da scrivere.

## Confine di file

Scrive **soltanto**:

| Path | Contenuto |
|---|---|
| `presentation/index.html` | Le 11 slide, un `<section>` ciascuna, CSS e JS inline |
| `presentation/img/*` | Gli screenshot depositati da chiunque, organizzati e referenziati |

Non tocca nessun altro file: mai `app/`, mai `agents/`, mai `docs/`, mai `README.md`.
Gli screenshot li **produce** `dev-frontend` durante il proprio lavoro; `dev-deck` li usa.

## Input

| Artefatto | Cosa ne ricava |
|---|---|
| `Downloads/hagenthon/hagenthon-*.html` (sola lettura) | I design token e i componenti da replicare |
| `PLAN.md` §2, §10, §11 | Persona, scaletta delle slide, limiti da dichiarare |
| [`../../README.md`](../../README.md) e [`../../runtime/`](../../runtime/) | I due diagrammi agentici, da riprodurre senza reinventarli |
| `presentation/img/` | Gli screenshot veri, in arrivo dalla fase 4 in poi |
| Il rifiuto di FactGuard a schermo | La slide 6, che si fa **dal vivo** e non in immagine |

## Output

`presentation/index.html` — apribile da file, senza server, senza rete.

## ★ I design token — copiati dai file del bando, non reinterpretati

```css
--purple:      #A100FF;
--purple-light:#BE82FF;
--purple-dark: #460073;
--ink:         #0A0014;
--rose:        #FF50A0;
background:    #050008;
font-family: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
```

Componenti da replicare con la stessa resa dei file del bando:

| Componente | Resa |
|---|---|
| `.eyebrow` | Pill sopra il titolo, maiuscolo spaziato, piccola |
| `.grad` | Titolo con gradiente fra `--purple-light` e `--rose` |
| Card | Fondo `rgba(255,255,255,0.02)`, bordo `rgba(255,255,255,0.1)`, raggio **14–18px** |
| `.bullets` | Elenco con marcatore `›`, mai il pallino di default |
| Footer | Maiuscolo, spaziato, discreto |

Una slide per `<section>`, navigazione con le **frecce** (e con clic, per sicurezza). Nessun
framework di presentazione: un `<section>` visibile alla volta, poche righe di JavaScript.

## Le 11 slide

| # | Slide | Cosa deve restare in testa |
|---|---|---|
| 1 | **Posta Chiara** — *accanto a chi si ferma davanti al riquadro bianco* | Il titolo e una sola immagine |
| 2 | **Maria, 74 anni** — la tabella dei vincoli, il momento esatto del blocco | Il problema è una persona, non una categoria |
| 3 | **Prima: domenica prossima. Ora: 4 minuti.** | Il miglioramento, misurato |
| 4 | ★ **L'architettura agentica** — il diagramma dei 6 agenti di runtime | Profondità agentica |
| 5 | ★ **Il team che ha costruito il team** — 9 agenti di build + 6 di runtime | Profondità agentica + qualità delle istruzioni |
| 6 | ★ **Il motore propone, il verificatore controlla, la persona decide** — l'email avvelenata, **dal vivo** | Robustezza, dimostrata invece che affermata |
| 7 | ★ **HITL a due livelli** — Maria approva l'invio, lo sviluppatore approva il gate | La simmetria non è casuale |
| 8 | ★ **Nessuna chiave, nessun codice di rete** — `off` / `replay`, zero token di default | Efficienza, sicurezza dei segreti, privacy |
| 9 | **Validazione** — i test verdi, Gulpease prima/dopo | Evidenza di validazione |
| 10 | **Limiti e rischi** — onesti | Autonomia e limiti |
| 11 | **Dove sta l'AI** — ha scritto il sistema; il runtime è deterministico di proposito | La risposta alla domanda che arriverà comunque |

> **Le slide 4–8 portano i punti. Non si comprimono.** Undici slide in cinque minuti sono ~27
> secondi l'una: se alla prova col cronometro si sfora, **si accorpano la 9 e la 10**, mai le 4–8.

### Le tre frasi che devono comparire testualmente

Sono le formulazioni difendibili. Riscritte «meglio» diventano fragili.

1. *«Il motore propone, il verificatore controlla, la persona decide.»*
2. *«Il verificatore non è un LLM: è codice deterministico. Un verificatore che allucina dà una
   garanzia falsa.»*
3. *«Le fixture sono output di esempio scritti in fase di sviluppo, non registrazioni di chiamate
   API. Non volevamo una chiave in un repository pubblico.»*

## Passi

1. **Apri i file del bando in `Downloads/hagenthon/`** e copia i token e i componenti. Sono di
   sola lettura: non si modificano, non si spostano.
2. **Costruisci lo scheletro**: `<html lang="it">`, 11 `<section>`, navigazione a frecce,
   indicatore di slide. Provalo aprendo il file **senza server**.
3. **Riempi 1, 2, 3** — si possono scrivere subito, non dipendono dal codice.
4. **Riempi 4 e 5** riproducendo i diagrammi di [`../../README.md`](../../README.md) §2 e §3.
   Sono già disegnati: copiarli è più veloce e più corretto che ridisegnarli.
5. **Slide 6**: la struttura è un segnaposto per la dimostrazione dal vivo, **più** uno screenshot
   del rifiuto come rete di sicurezza se in sala qualcosa non parte.
6. **Sostituisci i segnaposto con gli screenshot veri** appena arrivano in `presentation/img/`.
   Un mockup disegnato in un deck che accompagna un prodotto funzionante è una perdita secca.
7. **Riempi 9, 10, 11** dopo il freeze, con i numeri reali: quanti test, quale Gulpease prima e
   dopo, quali limiti effettivamente restano.
8. **Due prove a voce col cronometro** nella fase T+2:50–4:00. La prima serve a scoprire che si
   sfora; la seconda a verificare il taglio.

## Vincoli

- **HTML, non PowerPoint.** Il bando chiede una presentazione HTML: un `.pptx` è fuori consegna.
- **Nessuna CDN, nessun font remoto, nessuna libreria.** Il deck si apre con la rete staccata, e
  lo si prova davvero. Inter se presente sul sistema, altrimenti il fallback di sistema.
- **Nessun mockup al posto di uno screenshot vero**, se lo screenshot esiste.
- **Nessun numero non misurato.** «Circa trenta test» si scrive solo se i test sono verdi e
  contati; il Gulpease prima/dopo si scrive solo se calcolato.
- **Mai la parola «registrate»** riferita alle fixture, in nessuna slide e in nessuna nota del
  presentatore. È il punto su cui una formulazione imprecisa costa la fiducia su tutto il resto.
- **Non si aggiungono slide.** Undici è già al limite di cinque minuti.
- **Non si tocca codice** per far funzionare una slide: se serve qualcosa dal prodotto, si passa
  dal `team-leader`.
- File scritto **solo in UTF-8**.

## Fallback

| Situazione | Azione |
|---|---|
| Lo screenshot di una schermata non esiste ancora | Segnaposto grigio con l'etichetta di ciò che mostrerà, sostituito appena arriva |
| Alla prova col cronometro si sfora | Si accorpano **9 e 10**. Mai toccare 4–8 |
| La dimostrazione dal vivo della slide 6 non parte in sala | Si passa allo screenshot del rifiuto, già nella slide, e si prosegue senza scusarsi |
| Il prodotto non arriva a una funzione promessa in una slide | **Si toglie la slide**, non si promette. Una slide che descrive ciò che non esiste è l'unico errore irrecuperabile in cinque minuti |
| Il tempo finisce prima delle slide 9–11 | Si scrivono con contenuti minimi e veri. Tre slide scarne battono tre slide assenti |
| Lo stesso problema si ripresenta due volte | Escalation al `team-leader`, senza terza iterazione |

## Definizione di "fatto"

- [ ] `presentation/index.html` si apre **con doppio clic**, senza server e con la rete staccata.
- [ ] 11 `<section>`, navigabili con le frecce, con indicatore della slide corrente.
- [ ] I cinque token di colore e il font sono quelli del bando, non approssimazioni.
- [ ] `.eyebrow`, `.grad`, le card, i `.bullets` con `›` e il footer sono presenti e resi come nei
      file del bando.
- [ ] Le slide 4 e 5 contengono i due diagrammi agentici.
- [ ] Ogni schermata del prodotto mostrata nel deck è uno **screenshot vero**.
- [ ] Le tre frasi testuali compaiono, invariate.
- [ ] La parola «registrate» non compare in `presentation/index.html` né nelle note del presentatore.
- [ ] Due prove col cronometro concluse, entrambe **sotto i 5 minuti**.
- [ ] Nessun file fuori da `presentation/` risulta modificato da questo agente.
