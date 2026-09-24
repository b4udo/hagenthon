/* Posta Chiara — interfaccia.
 *
 * JavaScript semplice, nessun framework, nessun passo di build: il progetto si
 * clona e si apre. Le regole di accessibilita' che contano qui dentro:
 * pulsanti veri (mai <div onclick>), il fuoco si sposta quando cambia vista,
 * e ogni cambiamento di stato passa da una regione aria-live.
 */

"use strict";

const $ = (id) => document.getElementById(id);

const stato = {
  emailCorrente: null,
  risultato: null,
  bozzaScelta: null,
};

const ETICHETTE_SEMAFORO = { verde: "Può rispondere", giallo: "Da controllare", rosso: "Attenzione" };
const SIMBOLI = { verde: "●", giallo: "●", rosso: "●" };

// ───────────────────────────── rete locale ─────────────────────────────

async function chiedi(percorso, opzioni) {
  const risposta = await fetch(percorso, opzioni);
  if (!risposta.ok) {
    const corpo = await risposta.json().catch(() => ({}));
    throw new Error(corpo.detail || corpo.errore || `Errore ${risposta.status}`);
  }
  return risposta.json();
}

// ───────────────────────────── elenco ─────────────────────────────

async function caricaElenco() {
  const dati = await chiedi("/api/mailbox");
  aggiornaContatore(dati.inviate);

  const elenco = $("elenco-email");
  elenco.innerHTML = "";

  for (const email of dati.email) {
    const voce = document.createElement("li");
    const bottone = document.createElement("button");
    bottone.type = "button";
    bottone.className = "voce";

    bottone.innerHTML = `
      <span class="voce-alto">
        <span class="pallino pallino-attesa" data-pallino>· da controllare</span>
        <span class="voce-mittente"></span>
        <span class="voce-data"></span>
      </span>
      <span class="voce-oggetto"></span>`;

    bottone.querySelector(".voce-mittente").textContent = email.mittente_nome;
    bottone.querySelector(".voce-oggetto").textContent = email.oggetto;
    bottone.querySelector(".voce-data").textContent = dataItaliana(email.data_ricezione);
    bottone.setAttribute(
      "aria-label",
      `${email.mittente_nome}. ${email.oggetto}. Apri per leggere.`
    );

    bottone.addEventListener("click", () => apri(email.id));
    voce.appendChild(bottone);
    elenco.appendChild(voce);

    // Il verdetto arriva dalla pipeline, non e' precalcolato nel corpus.
    valutaInSecondoPiano(email.id, bottone);
  }
}

async function valutaInSecondoPiano(id, bottone) {
  try {
    const r = await chiedi(`/api/email/${id}/elabora`, { method: "POST" });
    const pallino = bottone.querySelector("[data-pallino]");
    const s = r.sicurezza.semaforo;
    pallino.className = `pallino pallino-${s}`;
    pallino.textContent = `${SIMBOLI[s]} ${ETICHETTE_SEMAFORO[s]}`;
    if (r.triage && r.triage.priorita === "secondo_piano") {
      bottone.classList.add("voce-secondo-piano");
    }
  } catch (errore) {
    console.warn("valutazione non riuscita per", id, errore);
  }
}

function dataItaliana(iso) {
  const mesi = ["gen", "feb", "mar", "apr", "mag", "giu",
                "lug", "ago", "set", "ott", "nov", "dic"];
  const p = String(iso).split("-");
  return p.length === 3 ? `${Number(p[2])} ${mesi[Number(p[1]) - 1]}` : iso;
}

// ───────────────────────────── lettura ─────────────────────────────

async function apri(id, avvelena = false) {
  const percorso = `/api/email/${id}/elabora` + (avvelena ? "?avvelena=true" : "");
  const [email, risultato] = await Promise.all([
    chiedi(`/api/email/${id}`),
    chiedi(percorso, { method: "POST" }),
  ]);

  stato.emailCorrente = email;
  stato.risultato = risultato;
  stato.bozzaScelta = null;

  disegna(email, risultato);

  $("vista-elenco").hidden = true;
  $("vista-lettura").hidden = false;
  // Il fuoco segue la vista, altrimenti chi usa la tastiera resta indietro.
  $("btn-indietro").focus();
  window.scrollTo(0, 0);
}

function disegna(email, r) {
  $("titolo-lettura").textContent = email.oggetto;
  $("mittente").textContent = `Da ${email.mittente_nome} — ${email.mittente_email}`;

  disegnaSemaforo(r.sicurezza);
  disegnaRiassunto(r);
  disegnaTesto(email, r);
  disegnaAllegati(email.allegati);
  disegnaRisposta(r);
  disegnaTracce(r);

  $("conferma-invio").hidden = true;
}

function disegnaSemaforo(sicurezza) {
  const box = $("semaforo");
  box.className = `semaforo semaforo-${sicurezza.semaforo}`;
  $("semaforo-messaggio").textContent = sicurezza.messaggio;

  const segnali = $("semaforo-segnali");
  segnali.innerHTML = "";
  for (const s of sicurezza.segnali) {
    const li = document.createElement("li");
    li.textContent = s;
    segnali.appendChild(li);
  }

  const azione = sicurezza.azione;
  const bottone = $("btn-azione");
  bottone.hidden = azione.tipo === "nessuna";
  bottone.textContent = azione.valore
    ? `${azione.etichetta}: ${azione.valore}`
    : azione.etichetta;

  bottone.onclick = () => {
    if (azione.tipo === "telefono") {
      // Il numero viene dalla tabella statica del backend, mai dall'email.
      window.location.href = `tel:${String(azione.valore).replace(/\s/g, "")}`;
    } else if (azione.tipo === "inoltra") {
      alert("Ho preparato l'inoltro a Luca.\n(In questo prototipo l'invio è simulato.)");
    } else {
      const risposta = $("scheda-risposta");
      if (!risposta.hidden) {
        risposta.scrollIntoView({ behavior: "smooth", block: "start" });
        const primo = risposta.querySelector(".intento");
        if (primo) primo.focus();
      }
    }
  };
}

function disegnaRiassunto(r) {
  const scheda = $("scheda-riassunto");
  if (!r.semplificazione || !r.semplificazione_mostrata) {
    scheda.hidden = true;
    return;
  }
  scheda.hidden = false;
  $("chi-scrive").textContent = r.semplificazione.chi_scrive;
  $("cosa-vogliono").textContent = r.semplificazione.cosa_vogliono;
  $("entro-quando").textContent = r.semplificazione.entro_quando || "Nessuna scadenza";
}

function disegnaTesto(email, r) {
  const semplificato = r.semplificazione_mostrata && r.semplificazione;

  $("titolo-testo").textContent = semplificato
    ? "Il messaggio, in parole semplici"
    : "Il messaggio";
  $("testo-messaggio").textContent = semplificato
    ? r.semplificazione.testo_semplificato
    : email.corpo;

  // Verifica fallita: si dice perche', non si nasconde.
  const avviso = $("scheda-verifica");
  const rifiutata = r.verifica && !r.verifica.passa && r.verifica.problemi.length > 0;
  avviso.hidden = !rifiutata;
  if (rifiutata) {
    const lista = $("problemi-verifica");
    lista.innerHTML = "";
    for (const p of r.verifica.problemi) {
      const li = document.createElement("li");
      li.textContent = p.spiegazione;
      lista.appendChild(li);
    }
  }

  const leg = r.leggibilita || {};
  if (leg.riassunto != null) {
    $("leggibilita").textContent =
      `Leggibilità (indice Gulpease): originale ${leg.prima} (${leg.prima_giudizio}), ` +
      `testo riscritto ${leg.dopo} (${leg.dopo_giudizio}), ` +
      `riassunto in breve ${leg.riassunto} (${leg.riassunto_giudizio}).`;
  } else {
    $("leggibilita").textContent =
      `Leggibilità del testo originale: ${leg.prima ?? "—"} (${leg.prima_giudizio ?? "—"}).`;
  }

  const btn = $("btn-originale");
  const orig = $("testo-originale");
  btn.hidden = !semplificato;
  orig.hidden = true;
  orig.textContent = email.corpo;
  btn.setAttribute("aria-expanded", "false");
  btn.onclick = () => {
    const mostra = orig.hidden;
    orig.hidden = !mostra;
    btn.setAttribute("aria-expanded", String(mostra));
    btn.textContent = mostra ? "Nascondi il testo originale" : "Mostra il testo originale";
  };
}

function disegnaAllegati(allegati) {
  const scheda = $("scheda-allegati");
  if (!allegati || allegati.length === 0) {
    scheda.hidden = true;
    return;
  }
  scheda.hidden = false;

  const lista = $("elenco-allegati");
  lista.innerHTML = "";
  for (const a of allegati) {
    const li = document.createElement("li");
    const nome = document.createElement("span");
    nome.className = "nome";
    nome.textContent = a.tipo === "pdf" ? `C'è un foglio allegato: ${a.nome}` : a.nome;
    li.appendChild(nome);

    for (const etichetta of ["Guarda", "Stampa"]) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "bottone bottone-secondario";
      b.textContent = etichetta;
      b.addEventListener("click", () =>
        alert(`${etichetta}: «${a.nome}».\n(In questo prototipo il documento è simulato.)`)
      );
      li.appendChild(b);
    }
    lista.appendChild(li);
  }
}

function disegnaRisposta(r) {
  const scheda = $("scheda-risposta");
  if (!r.bozze || r.bozze.length === 0) {
    scheda.hidden = true;
    return;
  }
  scheda.hidden = false;

  const contenitore = $("intenti");
  contenitore.innerHTML = "";
  $("bozza").hidden = true;

  for (const bozza of r.bozze) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "intento";
    b.textContent = bozza.etichetta;
    b.setAttribute("aria-pressed", "false");
    b.addEventListener("click", () => scegliIntento(bozza, contenitore, b));
    contenitore.appendChild(b);
  }
}

function scegliIntento(bozza, contenitore, bottone) {
  for (const b of contenitore.querySelectorAll(".intento")) {
    b.setAttribute("aria-pressed", "false");
  }
  bottone.setAttribute("aria-pressed", "true");

  stato.bozzaScelta = bozza;
  $("testo-bozza").value = bozza.testo;
  $("bozza").hidden = false;
  $("conferma-invio").hidden = true;
  $("testo-bozza").focus();
}

async function inviaRisposta() {
  if (!stato.bozzaScelta || !stato.emailCorrente) return;

  // ★ L'ultimo click e' sempre umano: si arriva qui solo da questo pulsante.
  const dati = await chiedi(`/api/email/${stato.emailCorrente.id}/invia`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      intento: stato.bozzaScelta.intento,
      testo: $("testo-bozza").value,
    }),
  });

  $("bozza").hidden = true;
  $("conferma-invio").hidden = false;
  aggiornaContatore(dati.completate_da_sola);
}

function aggiornaContatore(n) {
  $("contatore-autonomia").textContent = n;
}

function disegnaTracce(r) {
  const corpo = $("corpo-tracce");
  corpo.innerHTML = "";
  for (const t of r.tracce) {
    const tr = document.createElement("tr");
    for (const [valore, classe] of [
      [t.agente, ""], [t.modalita, ""], [t.esito, ""],
      [t.durata_ms, ""], [t.token, ""], [t.nota, "nota"],
    ]) {
      const td = document.createElement("td");
      td.textContent = valore;
      if (classe) td.className = classe;
      tr.appendChild(td);
    }
    corpo.appendChild(tr);
  }
  $("riepilogo-token").textContent =
    r.token_usati === 0
      ? "Questa email è costata 0 token: l'ha elaborata il motore deterministico."
      : `Token usati su questa email: ${r.token_usati}.`;
}

// ───────────────────────────── avvio ─────────────────────────────

function tornaAllElenco() {
  $("vista-lettura").hidden = true;
  $("vista-elenco").hidden = false;
  window.scrollTo(0, 0);
  caricaElenco();
}

document.addEventListener("DOMContentLoaded", async () => {
  $("btn-indietro").addEventListener("click", tornaAllElenco);
  $("btn-invia").addEventListener("click", () => {
    inviaRisposta().catch((e) => alert("Non sono riuscito a inviare: " + e.message));
  });
  $("btn-annulla").addEventListener("click", () => {
    $("bozza").hidden = true;
    for (const b of $("intenti").querySelectorAll(".intento")) {
      b.setAttribute("aria-pressed", "false");
    }
  });
  $("btn-avvelena").addEventListener("click", () => {
    if (stato.emailCorrente) apri(stato.emailCorrente.id, true);
  });

  try {
    const salute = await chiedi("/api/salute");
    $("modalita-llm").textContent = salute.llm_mode;
  } catch {
    $("modalita-llm").textContent = "non raggiungibile";
  }

  caricaElenco().catch((e) => {
    $("elenco-email").innerHTML =
      `<li class="caricamento">Non riesco a caricare la posta: ${e.message}</li>`;
  });
});
