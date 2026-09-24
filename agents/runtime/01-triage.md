# 01 · Triage

> Esiste perché Maria apre una casella in cui una convocazione dell'ASL e una promozione del
> supermercato hanno lo stesso identico aspetto. Prima di qualsiasi altra cosa, bisogna sapere
> che tipo di comunicazione è.

**Implementazione:** `app/backend/agents/triage.py`
**Modalità di default:** regole · **Seam LLM:** sì, Haiku (vedi [`routing.md`](routing.md))

---

## Scopo

Assegnare a ogni email una **categoria** e una **priorità**, e dire in una frase perché.
Il risultato governa tutto ciò che segue: l'ordine della lista, se semplificare, se comporre bozze.

## Input

`Email` — mittente (nome, indirizzo), oggetto, corpo, `in_rubrica`.

## Output

`EsitoTriage` — schema in [`contracts/esito-triage.schema.json`](contracts/esito-triage.schema.json).

```json
{
  "categoria": "sanita",
  "priorita": "azione_richiesta",
  "motivo": "Il medico di base chiede di confermare un appuntamento.",
  "confidenza": 0.9
}
```

| Campo | Valori ammessi |
|---|---|
| `categoria` | `sanita` · `ente_pubblico` · `persona_conosciuta` · `commerciale` · `sconosciuto` |
| `priorita` | `azione_richiesta` · `informativa` · `secondo_piano` |
| `motivo` | Una frase, in italiano semplice, rivolta a Maria |
| `confidenza` | `0.0`–`1.0` |

## Passi

1. Se `in_rubrica` è vero → `persona_conosciuta`, confidenza `0.95`.
2. Confronta il dominio del mittente con l'elenco dei domini istituzionali noti
   (`inps.it`, `comune.torino.it`, `aslcittaditorino.it`, …) → `ente_pubblico` o `sanita`.
3. Cerca i marcatori commerciali nell'oggetto e nel corpo (`offerta`, `sconto`,
   `newsletter`, `disiscriviti`) → `commerciale`, priorità `secondo_piano`.
4. Altrimenti → `sconosciuto`, confidenza `≤ 0.6`.
5. Per la priorità, cerca i marcatori di azione (`confermare`, `entro`, `scadenza`,
   `presentarsi`, `rispondere`) → `azione_richiesta`, altrimenti `informativa`.

## Vincoli

- **Il triage non giudica la sicurezza.** `sconosciuto` non significa "sospetto": quel verdetto
  appartiene all'agente 02, che ha regole proprie. Sovrapporre le due cose produrrebbe due fonti
  di verità in disaccordo davanti alla giuria.
- La categoria `commerciale` **non nasconde** l'email: la mette in secondo piano. Nascondere
  posta a una persona che già non si fida dello strumento è il modo più rapido per perderne la
  fiducia.
- `motivo` è rivolto a Maria, non a uno sviluppatore: mai gergo, mai nomi di regole.

## Fallback

Categoria `sconosciuto`, priorità `informativa`, confidenza `0.0`, motivo *"Non sono riuscito a
capire di cosa si tratta."* L'email resta visibile e leggibile: il fallimento del triage non
sottrae mai un'email dalla lista.
