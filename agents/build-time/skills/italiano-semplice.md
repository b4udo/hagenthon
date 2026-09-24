# Skill · Italiano semplice

> Conoscenza condivisa. La caricano `dev-core` (regole di `plain_rules.py`),
> `dev-corpus` (per scrivere burocratese *credibile*, che è l'esercizio
> opposto) e `dev-frontend` (per i testi dell'interfaccia).

---

## Che cosa significa «semplice», misurato

**Indice Gulpease**, la formula di leggibilità tarata sull'italiano:

```
Gulpease = 89 + (300 × frasi − 10 × lettere) / parole
```

| Indice | Lettura |
|---|---|
| ≥ 80 | molto facile — licenza elementare |
| 60–79 | facile — licenza media |
| 40–59 | difficile |
| < 40 | molto difficile |

Implementazione: `app/backend/engines/gulpease.py`.

★ **La leva più forte è la lunghezza delle frasi, non quella delle parole.**
Il coefficiente delle frasi è 300, quello delle lettere 10. Un periodo
burocratico di sessanta parole resta illeggibile anche dopo aver sostituito
ogni termine difficile: va spezzato. È il motivo per cui il semplificatore
lavora sui periodi prima che sul lessico.

## Il lessico del burocratese italiano

| Burocratese | Italiano comune |
|---|---|
| istanza | domanda |
| convocazione | appuntamento |
| erogazione | pagamento |
| attestazione | certificato |
| la S.V. (Signoria Vostra) | lei |
| entro e non oltre | entro |
| recarsi presso | andare a |
| previa esibizione di | mostrando |
| in corso di validità | valido |
| decorso il termine | dopo questa data |
| provvedere al ritiro | ritirare |
| è fatto obbligo di | deve |
| in difetto | altrimenti |
| cedolino | foglio della pensione |

## ★ La lezione che ha riscritto il semplificatore

La prima versione sostituiva **parola per parola**. Su un'email vera del
Comune produceva:

```
  «all'domanda»      ← "all'istanza", con istanza → domanda
  «dallei richiesto» ← "dalla S.V. richiesto", con la S.V. → lei
```

Italiano rotto: **peggio dell'originale**, che almeno era corretto.

La causa è strutturale, non un difetto da correggere: sostituire un
sostantivo ne cambia il genere, e articoli e preposizioni intorno vanno in
pezzi. **Un motore a regole non sa concordare.**

Da qui le due regole operative:

1. **Sostituisci locuzioni intere, articolo compreso.** La concordanza sta
   dentro la sostituzione: `all'istanza → alla domanda`, non `istanza → domanda`.
2. **Elimina le frasi di pura formula** invece di tradurle. *"La presente
   comunicazione è trasmessa in via telematica e non necessita di
   sottoscrizione autografa"* non va semplificata: va tolta.

Ciò che non rientra in questi due casi **resta invariato**. Un testo non
toccato è un esito accettabile; un testo storpiato non lo è.

## Regole di scrittura

- **Una informazione per frase.** Massimo ~25 parole.
- **Attivo, non passivo**, quando il soggetto è noto.
- **Non toccare mai** date, importi, orari, nomi propri. Sono ciò che FactGuard
  protegge, e l'unico modo sicuro di superare un verificatore è non dargli
  motivo di intervenire.
- **Non aggiungere nulla.** Nessuna interpretazione, nessun consiglio, nessuna
  rassicurazione. Il sistema dice **cosa c'è scritto, non cosa fare**.
- **Mai contenuti clinici, fiscali o legali.**

## Per `dev-corpus`: scrivere burocratese credibile

L'esercizio inverso, e la demo ci vive sopra. Un burocratese finto e blando
rende inutile tutto il resto. Gli ingredienti veri:

- Il periodo unico e lunghissimo, con tre subordinate.
- Il riferimento normativo nel mezzo: *"ai sensi degli artt. 33 e 40 del
  D.P.R. 28 dicembre 2000, n. 445"*.
- Il numero di protocollo in apertura.
- L'impersonale: *si comunica*, *si invita*, *si rammenta*.
- La conseguenza minacciosa in coda: *"decorso inutilmente il termine, la
  pratica sarà archiviata d'ufficio"*.
- La firma senza persona: *"Il Responsabile del Procedimento"*.

Tutto inventato: protocolli, indirizzi, nomi. Nessun dato reale.
