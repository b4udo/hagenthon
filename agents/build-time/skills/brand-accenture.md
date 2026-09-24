# Skill · Brand Accenture

> Conoscenza condivisa. La carica `dev-deck` per `presentation/index.html`.
>
> ★ **Vale solo per la presentazione, mai per il prodotto.** L'interfaccia di
> Posta Chiara è chiara su fondo bianco con contrasto ≥ 7:1, perché è pensata
> per gli occhi di Maria. Applicarle il fondo scuro del brand sarebbe una
> scelta estetica pagata dall'utente: vedi
> [`accessibilita-anziani.md`](accessibilita-anziani.md).

---

## Da dove vengono questi valori

Non da una ricostruzione a memoria: sono estratti dai quattro file HTML del
bando in `Downloads/hagenthon/`. Sono il riferimento di brand più autorevole
disponibile, perché li ha prodotti chi valuta.

## Token

```css
--purple:       #A100FF;   /* accento primario */
--purple-light: #BE82FF;
--purple-dark:  #460073;
--ink:          #0A0014;
--rose:         #FF50A0;

background: #050008;
color:      #ffffff;
font-family: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
line-height: 1.6;
```

## Componenti da replicare

**Pill `.eyebrow`** — l'etichetta sopra il titolo:
```css
display: inline-block;
border: 1px solid rgba(255,255,255,0.15);
background: rgba(255,255,255,0.05);
border-radius: 999px;
padding: 6px 16px;
font-size: 11px;
text-transform: uppercase;
letter-spacing: 0.25em;
color: rgba(255,255,255,0.7);
```

**Titolo con gradiente** — su una `<span class="grad">` dentro l'`<h1>`:
```css
background: linear-gradient(90deg, var(--purple-light), var(--purple));
background-clip: text;
-webkit-background-clip: text;
color: transparent;
```

**Card**:
```css
border: 1px solid rgba(255,255,255,0.1);
border-radius: 14px;   /* 18px per le card grandi */
background: rgba(255,255,255,0.02);
padding: 22px 24px;
```

**Lista `.bullets`** — marcatore `›` viola al posto del pallino:
```css
.bullets li { position: relative; padding-left: 20px; color: rgba(255,255,255,0.72); }
.bullets li::before { content: "›"; position: absolute; left: 0; color: var(--purple); font-weight: 700; }
```

**Badge numerico** — per i pesi e le numerazioni:
```css
border: 1px solid rgba(161,0,255,0.3);
background: rgba(161,0,255,0.1);
border-radius: 999px;
padding: 2px 10px;
font-family: monospace;
color: var(--purple-light);
```

**Footer** — maiuscolo, spaziato, molto tenue:
```css
text-transform: uppercase;
letter-spacing: 0.2em;
font-size: 11px;
color: rgba(255,255,255,0.25);
```

## Vincoli di consegna

- La presentazione è **HTML**, non `.pptx`. È scritto nelle regole di consegna.
- **File unico, nessuna CDN, nessun font esterno**: deve aprirsi anche da
  `file://` e su una macchina senza rete. La demo non dipende dalla
  connessione della sala.
- **Cinque minuti.** Undici slide sono ~27 secondi l'una: titolo e pochi
  punti, il resto nelle note del presentatore.
- Accessibile anche lei: `<button>` veri per la navigazione, fuoco visibile,
  `lang="it"`. Una presentazione sull'accessibilità che non è accessibile è
  un autogol che la giuria nota.
