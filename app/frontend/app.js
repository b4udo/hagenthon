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
  dettaturaAccettata: false,  // l'avviso sulla dettatura si mostra una volta sola
  cartella: "in_arrivo",
  allegato: null,             // il File scelto, che resta nel browser
  urlAnteprima: null,         // object URL da revocare quando si cambia
  flussoVideo: null,          // MediaStream aperto: va sempre fermato
};

const TITOLI_CARTELLA = {
  in_arrivo: "Posta in arrivo",
  inviata: "Posta inviata",
  eliminata: "Posta eliminata",
};

const AIUTI_CARTELLA = {
  in_arrivo: "Tocchi un messaggio per leggerlo spiegato in parole semplici.",
  inviata: "Le risposte che ha inviato lei.",
  eliminata: "I messaggi che ha tolto dalla posta in arrivo. Può sempre rimetterli indietro.",
};

const VUOTE = {
  in_arrivo: "Non c'è nessun messaggio.",
  inviata: "Non ha ancora inviato nessuna risposta.",
  eliminata: "Non ha eliminato nessun messaggio.",
};

/* Modo tecnico: `?tecnico=1`.
 *
 * Il pannello "Come ha ragionato il sistema" e il pulsante "E se l'AI sbaglia?"
 * servono alla giuria, non a Maria. Mostrarli a lei sarebbe esattamente
 * l'errore che il bando chiama «strumento pensato per sviluppatori»: una
 * persona che apre la posta non deve trovarsi davanti una tabella di agenti,
 * millisecondi e token.
 *
 * Restano nel prodotto e restano veri — si aprono con un parametro nell'URL,
 * che e' come li mostriamo in demo.
 */
function modoTecnico() {
  return new URLSearchParams(window.location.search).get("tecnico") === "1";
}

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
  const dati = await chiedi(`/api/mailbox?cartella=${encodeURIComponent(stato.cartella)}`);
  aggiornaContatore(dati.inviate);
  aggiornaCartelle(dati.conteggi);

  $("titolo-elenco").textContent = TITOLI_CARTELLA[stato.cartella] || "Le sue email";
  $("aiuto-elenco").textContent = AIUTI_CARTELLA[stato.cartella] || "";

  const elenco = $("elenco-email");
  elenco.innerHTML = "";

  if (!dati.email.length) {
    const vuota = document.createElement("li");
    vuota.className = "vuota";
    vuota.textContent = VUOTE[stato.cartella] || "Non c'è niente qui.";
    elenco.appendChild(vuota);
    return;
  }

  for (const elemento of dati.email) {
    elenco.appendChild(
      dati.tipo === "inviata" ? voceInviata(elemento) : voceRicevuta(elemento)
    );
  }
}

function voceRicevuta(email) {
  const voce = document.createElement("li");
  const bottone = document.createElement("button");
  bottone.type = "button";

  // Un'email gia' risposta mostra **solo** «Già risposto».
  //
  // «Può rispondere» e «Già risposto» insieme sono due stati che si
  // contraddicono a colpo d'occhio: il primo invita a fare una cosa che il
  // secondo dice essere gia' fatta. Su una riga sola, con due pastiglie verdi
  // quasi identiche, e' rumore. Il semaforo ha gia' fatto il suo lavoro
  // quando serviva, cioe' prima della risposta.
  // Precedenza: ha risposto > l'ha girata a Luca > il semaforo.
  // Un marcatore solo per riga. Sono stati successivi della stessa pratica,
  // e mostrarne due insieme costringe a capire quale conta.
  let marcatore;
  if (email.gia_risposto) {
    marcatore = '<span class="risposto" data-risposto>✓ Già risposto</span>';
  } else if (email.inoltrata) {
    marcatore = '<span class="in-verifica" data-verifica>⏳ Luca sta verificando</span>';
  } else {
    marcatore = '<span class="pallino pallino-attesa" data-pallino>· da controllare</span>';
  }

  bottone.innerHTML = `
    <span class="voce-alto">
      ${marcatore}
      <span class="voce-mittente"></span>
      <span class="voce-data"></span>
    </span>
    <span class="voce-oggetto"></span>`;

  bottone.querySelector(".voce-mittente").textContent = email.mittente_nome;
  bottone.querySelector(".voce-oggetto").textContent = email.oggetto;
  bottone.querySelector(".voce-data").textContent = dataItaliana(email.data_ricezione);

  let stato_detto = "";
  if (email.gia_risposto) stato_detto = " Già risposto.";
  else if (email.inoltrata) stato_detto = " Luca sta verificando.";

  bottone.className =
    "voce" +
    (email.gia_risposto ? " voce-risposta" : email.inoltrata ? " voce-verifica" : "");

  bottone.setAttribute(
    "aria-label",
    `${email.mittente_nome}. ${email.oggetto}.${stato_detto} Apri per leggere.`
  );

  bottone.addEventListener("click", () => apri(email.id));
  voce.appendChild(bottone);

  // Il verdetto arriva dalla pipeline, non e' precalcolato nel corpus.
  // Su un'email gia' risposta serve ancora, ma solo per la classe
  // «secondo piano»: il pallino non c'e' piu' da aggiornare.
  valutaInSecondoPiano(email.id, bottone);
  return voce;
}

function voceInviata(invio) {
  const voce = document.createElement("li");
  const bottone = document.createElement("button");
  bottone.type = "button";
  bottone.className = "voce voce-inviata";

  bottone.innerHTML = `
    <span class="voce-alto">
      <span class="risposto">✓ Inviata</span>
      <span class="voce-mittente"></span>
      <span class="voce-data"></span>
    </span>
    <span class="voce-oggetto"></span>
    <span class="anteprima"></span>`;

  bottone.querySelector(".voce-mittente").textContent = invio.destinatario_nome;
  bottone.querySelector(".voce-oggetto").textContent = invio.oggetto;
  bottone.querySelector(".voce-data").textContent = oraItaliana(invio.inviato_il);
  bottone.querySelector(".anteprima").textContent =
    (invio.allegato ? `📎 ${invio.allegato.nome} · ` : "") + anteprima(invio.testo);
  bottone.setAttribute(
    "aria-label",
    `Risposta inviata a ${invio.destinatario_nome}. ${invio.oggetto}. Apri per rileggerla.`
  );

  // Una risposta inviata si rilegge, non si rielabora: non c'e' una pipeline
  // da far girare su un testo che ha scritto lei.
  bottone.addEventListener("click", () => mostraInviata(invio));
  voce.appendChild(bottone);
  return voce;
}

function anteprima(testo) {
  const piatto = String(testo).replace(/\s+/g, " ").trim();
  return piatto.length > 90 ? piatto.slice(0, 90) + "…" : piatto;
}

function mostraInviata(invio) {
  const allegato = invio.allegato ? `\nAllegato: ${invio.allegato.nome}` : "";
  alert(
    `A: ${invio.destinatario_nome}\n` +
      `Oggetto: ${invio.oggetto}${allegato}\n\n${invio.testo}`
  );
}

function aggiornaCartelle(conteggi) {
  for (const bottone of document.querySelectorAll(".cartella")) {
    const nome = bottone.dataset.cartella;
    if (nome === stato.cartella) bottone.setAttribute("aria-current", "page");
    else bottone.removeAttribute("aria-current");
  }
  if (!conteggi) return;
  for (const segno of document.querySelectorAll("[data-conteggio]")) {
    const n = conteggi[segno.dataset.conteggio];
    segno.textContent = n ? String(n) : "";
  }
}

function apriCartella(nome) {
  stato.cartella = nome;
  Voce.fermaLettura();
  $("vista-lettura").hidden = true;
  $("vista-elenco").hidden = false;
  caricaElenco().catch((e) => {
    $("elenco-email").innerHTML =
      `<li class="caricamento">Non riesco a caricare la posta: ${e.message}</li>`;
  });
}

async function valutaInSecondoPiano(id, bottone) {
  try {
    const r = await chiedi(`/api/email/${id}/elabora`, { method: "POST" });
    const pallino = bottone.querySelector("[data-pallino]");
    if (pallino) {
      const s = r.sicurezza.semaforo;
      pallino.className = `pallino pallino-${s}`;
      pallino.textContent = `${SIMBOLI[s]} ${ETICHETTE_SEMAFORO[s]}`;
    }
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

function oraItaliana(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const due = (n) => String(n).padStart(2, "0");
  return `${d.getDate()} ${["gen","feb","mar","apr","mag","giu",
    "lug","ago","set","ott","nov","dic"][d.getMonth()]}, ${due(d.getHours())}:${due(d.getMinutes())}`;
}

// ───────────────────────────── lettura ─────────────────────────────

async function apri(id, avvelena = false) {
  // Aprire un'altra email mentre la voce legge la precedente e' il modo piu'
  // rapido di confondersi su quale messaggio si sta ascoltando.
  Voce.fermaLettura();
  Voce.fermaAscolto();
  chiudiFotocamera();

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
  disegnaStatoCartella(r);
  disegnaRiassunto(r);
  disegnaTesto(email, r);
  disegnaAllegati(email.allegati);
  disegnaRisposta(r);
  disegnaTracce(r);

  $("conferma-invio").hidden = true;
  $("conferma-aiuto").hidden = true;
}

function disegnaStatoCartella(r) {
  // Chi ha gia' risposto deve vederlo subito: riproporre le tre scelte come
  // se non fosse successo niente e' il modo piu' rapido di far inviare due
  // volte la stessa cosa a chi non ricorda di averlo gia' fatto.
  $("stato-risposta").hidden = !r.gia_risposto;
  // Stessa ragione per l'attesa: se l'ha gia' girata a Luca deve ricordarselo
  // invece di girargliela una seconda volta.
  $("stato-verifica").hidden = !r.inoltrata || r.gia_risposto;

  const eliminata = r.cartella === "eliminata";
  $("btn-elimina").hidden = eliminata;
  $("btn-ripristina").hidden = !eliminata;
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
  togliAllegato();
  statoVoce("");
  const avviso = $("bozza").querySelector(".voce-avviso");
  if (avviso) avviso.remove();
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
      allegato: stato.allegato
        ? {
            nome: stato.allegato.name,
            tipo: stato.allegato.type || "sconosciuto",
            dimensione: stato.allegato.size,
          }
        : null,
    }),
  });

  $("bozza").hidden = true;
  $("conferma-invio").textContent = dati.allegato
    ? `✓ Risposta inviata, con «${dati.allegato}» allegato.`
    : "✓ Risposta inviata.";
  $("conferma-invio").hidden = false;
  togliAllegato();
  aggiornaContatore(dati.completate_da_sola);

  // Da adesso questa email e' "gia' risposto", qui e nell'elenco.
  $("stato-risposta").hidden = false;
  if (stato.risultato) stato.risultato.gia_risposto = true;
}

async function chiediAiuto() {
  if (!stato.emailCorrente) return;
  const esito = await chiedi(`/api/email/${stato.emailCorrente.id}/aiuto`, { method: "POST" });
  const conferma = $("conferma-aiuto");
  conferma.textContent = `✓ ${esito.messaggio}`;
  conferma.hidden = false;
  // Da adesso l'email e' in attesa: lo dice qui e lo dira' nell'elenco.
  if (stato.risultato) stato.risultato.inoltrata = true;
  $("stato-verifica").hidden = Boolean(stato.risultato && stato.risultato.gia_risposto);
  // Lo dice anche a voce: chi fa fatica a leggere deve sapere che è partito.
  if (Voce.puoLeggere()) Voce.leggi(esito.messaggio);
}

async function spostaEmail(destinazione) {
  if (!stato.emailCorrente) return;
  await chiedi(`/api/email/${stato.emailCorrente.id}/${destinazione}`, { method: "POST" });
  tornaAllElenco();
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

// ─────────────────────────── allegati ───────────────────────────
//
// Un documento gia' salvato, oppure una foto scattata sul momento. Il file
// **non lascia il browser**: al server arrivano solo nome, tipo e dimensione.
// Per un prototipo senza trasporto di posta reale, spedire i byte darebbe
// l'impressione di una spedizione che non avviene.

const MAX_BYTE_ALLEGATO = 10 * 1024 * 1024;

function pesoLeggibile(byte) {
  if (byte < 1024) return `${byte} byte`;
  if (byte < 1024 * 1024) return `${Math.round(byte / 1024)} KB`;
  return `${(byte / (1024 * 1024)).toFixed(1)} MB`.replace(".", ",");
}

function erroreAllegato(messaggio) {
  const p = $("allegato-errore");
  p.textContent = messaggio;
  p.hidden = !messaggio;
}

function scegliAllegato(file) {
  if (!file) return;

  if (file.size > MAX_BYTE_ALLEGATO) {
    erroreAllegato(
      `Questo file è troppo grande (${pesoLeggibile(file.size)}). ` +
        "Il limite è 10 MB."
    );
    return;
  }
  erroreAllegato("");

  liberaAnteprima();
  stato.allegato = file;

  $("allegato-nome").textContent = file.name;
  $("allegato-peso").textContent = pesoLeggibile(file.size);

  const anteprima = $("anteprima-foto");
  if (file.type && file.type.startsWith("image/")) {
    // Vedere la foto e' l'unico modo di sapere se e' venuta leggibile.
    stato.urlAnteprima = URL.createObjectURL(file);
    anteprima.src = stato.urlAnteprima;
    anteprima.alt = `Anteprima di ${file.name}`;
    anteprima.hidden = false;
  } else {
    anteprima.hidden = true;
    anteprima.removeAttribute("src");
  }

  $("allegato-scelto").hidden = false;
  $("btn-togli-allegato").focus();
}

function liberaAnteprima() {
  if (stato.urlAnteprima) {
    URL.revokeObjectURL(stato.urlAnteprima);
    stato.urlAnteprima = null;
  }
}

function togliAllegato() {
  liberaAnteprima();
  stato.allegato = null;
  $("allegato-scelto").hidden = true;
  $("anteprima-foto").hidden = true;
  $("anteprima-foto").removeAttribute("src");
  erroreAllegato("");
  for (const id of ["file-documento", "file-foto"]) $(id).value = "";
}

// ─────────────── la fotocamera ───────────────
//
// `<input capture>` apre la fotocamera **solo su telefono**: su un portatile
// l'attributo viene ignorato e si apre il solito selettore di file. Per
// aprire davvero l'obiettivo serve getUserMedia, che richiede un contesto
// sicuro — `localhost` lo e', quindi la demo funziona senza certificati.
//
// Il flusso video non esce dal dispositivo: nessun frame viene inviato da
// nessuna parte, lo scatto diventa un file che resta nel browser.

function fotocameraDisponibile() {
  return Boolean(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
}

async function apriFotocamera() {
  erroreAllegato("");
  try {
    stato.flussoVideo = await navigator.mediaDevices.getUserMedia({
      // `environment` = fotocamera posteriore dove esiste; sul portatile
      // non c'e' scelta e il browser ignora la preferenza senza fallire.
      video: { facingMode: "environment", width: { ideal: 1280 } },
      audio: false,
    });
  } catch (errore) {
    // Negato, occupato o assente: si ripiega sul selettore di file, che su
    // telefono apre comunque l'app fotocamera.
    $("fotocamera").hidden = true;
    $("btn-fotocamera").hidden = true;
    $("ripiego-foto").hidden = false;
    erroreAllegato(
      errore && errore.name === "NotAllowedError"
        ? "Non ho il permesso di usare la fotocamera. Lo conceda nella barra del browser, oppure scelga un documento già salvato."
        : "Non riesco ad aprire la fotocamera. Può scegliere un documento già salvato."
    );
    return;
  }

  const video = $("video-fotocamera");
  video.srcObject = stato.flussoVideo;
  await video.play().catch(() => {});
  $("fotocamera").hidden = false;
  $("btn-scatta").focus();
}

function chiudiFotocamera() {
  // Le tracce vanno fermate a mano: senza questo la spia della fotocamera
  // resta accesa, e su un dispositivo altrui è inaccettabile.
  if (stato.flussoVideo) {
    for (const traccia of stato.flussoVideo.getTracks()) traccia.stop();
    stato.flussoVideo = null;
  }
  const video = $("video-fotocamera");
  video.pause();
  video.srcObject = null;
  $("fotocamera").hidden = true;
}

function scatta() {
  const video = $("video-fotocamera");
  const larghezza = video.videoWidth;
  const altezza = video.videoHeight;
  if (!larghezza || !altezza) {
    erroreAllegato("La fotocamera non è ancora pronta. Riprovi fra un istante.");
    return;
  }

  const tela = document.createElement("canvas");
  tela.width = larghezza;
  tela.height = altezza;
  tela.getContext("2d").drawImage(video, 0, 0, larghezza, altezza);

  tela.toBlob(
    (blob) => {
      if (!blob) {
        erroreAllegato("Non sono riuscito a salvare la foto. Riprovi.");
        return;
      }
      const adesso = new Date();
      const due = (n) => String(n).padStart(2, "0");
      const nome =
        `foto-${adesso.getFullYear()}${due(adesso.getMonth() + 1)}${due(adesso.getDate())}` +
        `-${due(adesso.getHours())}${due(adesso.getMinutes())}${due(adesso.getSeconds())}.jpg`;
      chiudiFotocamera();
      scegliAllegato(new File([blob], nome, { type: "image/jpeg" }));
    },
    "image/jpeg",
    0.9
  );
}

function preparaAllegati() {
  $("file-documento").addEventListener("change", (e) => scegliAllegato(e.target.files[0]));
  $("file-foto").addEventListener("change", (e) => scegliAllegato(e.target.files[0]));
  $("btn-togli-allegato").addEventListener("click", () => {
    togliAllegato();
    $("file-documento").focus();
  });

  if (!fotocameraDisponibile()) {
    // Browser senza getUserMedia: si mostra subito il ripiego, invece di un
    // pulsante che promette una fotocamera e non la apre.
    $("btn-fotocamera").hidden = true;
    $("ripiego-foto").hidden = false;
  } else {
    $("btn-fotocamera").addEventListener("click", () => {
      apriFotocamera().catch(() => erroreAllegato("Non riesco ad aprire la fotocamera."));
    });
  }

  $("btn-scatta").addEventListener("click", scatta);
  $("btn-chiudi-fotocamera").addEventListener("click", () => {
    chiudiFotocamera();
    $("btn-fotocamera").focus();
  });
}

// ───────────────────────────── voce ─────────────────────────────
//
// Maria usa i vocali di WhatsApp e non scrive: sa parlare, non digitare.
// Ascoltare e dettare non sono un di piu', sono il suo modo di usare un
// dispositivo. Vedi voce.js per la differenza di privacy fra le due.

function testoRiassunto() {
  const r = stato.risultato;
  if (!r || !r.semplificazione) return "";
  const s = r.semplificazione;
  return [
    `Chi le scrive: ${s.chi_scrive}.`,
    `Cosa le chiedono: ${s.cosa_vogliono}`,
    s.entro_quando ? `Entro quando: ${s.entro_quando}.` : "Non c'è una scadenza.",
  ].join(" ");
}

function testoMessaggio() {
  return $("testo-messaggio").textContent || "";
}

/** Collega un pulsante a un testo: prima pressione legge, seconda ferma. */
function collegaLettura(idBottone, prendiTesto) {
  const bottone = $(idBottone);
  if (!bottone) return;

  if (!Voce.puoLeggere()) {
    // Meglio assente che presente e inerte: un pulsante che non fa nulla
    // e' peggio di nessun pulsante per chi non puo' verificarne l'effetto.
    bottone.hidden = true;
    return;
  }

  bottone.setAttribute("aria-pressed", "false");
  bottone.addEventListener("click", () => {
    if (bottone.getAttribute("aria-pressed") === "true") {
      Voce.fermaLettura();
      return;
    }
    const testo = prendiTesto();
    if (!testo.trim()) return;
    azzeraPulsantiVoce();
    bottone.setAttribute("aria-pressed", "true");
    Voce.leggi(testo);
  });
}

function pulsantiVoce() {
  return [$("btn-ascolta-riassunto"), $("btn-ascolta-messaggio"), $("btn-ascolta-bozza")]
    .filter(Boolean);
}

function azzeraPulsantiVoce() {
  for (const b of pulsantiVoce()) b.setAttribute("aria-pressed", "false");
}

function mostraBarraVoce(attiva) {
  $("barra-voce").hidden = !attiva;
  document.body.classList.toggle("voce-attiva", attiva);
  if (!attiva) azzeraPulsantiVoce();
}

function statoVoce(messaggio, errore = false) {
  const p = $("voce-stato");
  p.textContent = messaggio || "";
  p.classList.toggle("voce-stato-errore", Boolean(errore));
}

// ─────────── dettatura ───────────

function avviaDettatura() {
  const bottone = $("btn-detta");
  const area = $("testo-bozza");
  const inizialeLunghezza = area.value.length;

  bottone.setAttribute("aria-pressed", "true");
  bottone.innerHTML = '<span aria-hidden="true">■</span> Ho finito di parlare';
  statoVoce("La sto ascoltando. Parli pure con calma.");

  const partito = Voce.ascolta({
    alTesto: (testo) => {
      // Si aggiunge in coda alla bozza scelta, non la si sostituisce: la
      // risposta resta quella verificata, la voce ci aggiunge una frase.
      const separatore = inizialeLunghezza && !area.value.endsWith("\n") ? "\n" : "";
      area.value = area.value.slice(0, inizialeLunghezza) + separatore + testo;
    },
    alFine: (testo) => {
      bottone.setAttribute("aria-pressed", "false");
      bottone.innerHTML = '<span aria-hidden="true">🎤</span> Aggiunga con la voce';
      statoVoce(testo ? "Ho scritto quello che ha detto. Lo rilegga pure." : "");
    },
    alErrore: (messaggio) => statoVoce(messaggio, true),
  });

  if (!partito) statoVoce("Questo browser non sa ascoltare il microfono.", true);
}

/** L'avviso sulla dettatura, una volta sola e prima del primo uso.
 *
 * In Chrome il riconoscimento vocale non e' locale: l'audio va a un servizio
 * del fornitore del browser. E' l'unica cosa in tutto Posta Chiara che esce
 * dal dispositivo, e chi la usa deve saperlo **prima**, non dopo.
 */
function chiediConsensoDettatura() {
  if (stato.dettaturaAccettata) { avviaDettatura(); return; }

  const avviso = document.createElement("div");
  avviso.className = "voce-avviso";
  avviso.setAttribute("role", "alertdialog");
  avviso.innerHTML = `
    <p><strong>Un avviso prima di cominciare.</strong> Per capire quello che dice,
       il browser manda la sua voce a un servizio esterno. È l'unica parte di
       Posta Chiara che esce da questo dispositivo: tutto il resto resta qui.
       Se preferisce, può scrivere o lasciare la risposta così com'è.</p>
    <div class="azioni">
      <button type="button" class="bottone bottone-microfono" data-si>Va bene, ascolti</button>
      <button type="button" class="bottone bottone-secondario" data-no>No, lascio stare</button>
    </div>`;

  $("bozza").insertBefore(avviso, $("voce-stato"));
  avviso.querySelector("[data-si]").focus();

  avviso.querySelector("[data-si]").addEventListener("click", () => {
    stato.dettaturaAccettata = true;
    avviso.remove();
    avviaDettatura();
  });
  avviso.querySelector("[data-no]").addEventListener("click", () => {
    avviso.remove();
    $("btn-detta").focus();
  });
}

function preparaVoce() {
  collegaLettura("btn-ascolta-riassunto", testoRiassunto);
  collegaLettura("btn-ascolta-messaggio", testoMessaggio);
  collegaLettura("btn-ascolta-bozza", () => $("testo-bozza").value);

  Voce.osservaLettura(mostraBarraVoce);
  $("btn-ferma-voce").addEventListener("click", () => Voce.fermaLettura());

  const detta = $("btn-detta");
  if (!Voce.puoAscoltare()) {
    // Firefox e Safari desktop non espongono il riconoscimento vocale.
    detta.disabled = true;
    detta.title = "Questo browser non sa ascoltare il microfono.";
    detta.hidden = true;
    return;
  }
  detta.setAttribute("aria-pressed", "false");
  detta.addEventListener("click", () => {
    if (Voce.staAscoltando()) { Voce.fermaAscolto(); return; }
    chiediConsensoDettatura();
  });
}

// ───────────────────────────── avvio ─────────────────────────────

function tornaAllElenco() {
  // La voce non deve continuare a leggere un'email che non e' piu' aperta,
  // e la fotocamera non deve restare accesa alle spalle di chi l'ha aperta.
  Voce.fermaLettura();
  Voce.fermaAscolto();
  chiudiFotocamera();
  statoVoce("");
  $("vista-lettura").hidden = true;
  $("vista-elenco").hidden = false;
  window.scrollTo(0, 0);
  caricaElenco();
}

document.addEventListener("DOMContentLoaded", async () => {
  if (modoTecnico()) {
    for (const el of document.querySelectorAll(".solo-tecnico")) el.hidden = false;
  }

  preparaVoce();
  preparaAllegati();

  for (const bottone of document.querySelectorAll(".cartella")) {
    bottone.addEventListener("click", () => apriCartella(bottone.dataset.cartella));
  }
  $("btn-aiuto").addEventListener("click", () => {
    chiediAiuto().catch((e) => alert("Non sono riuscito a girare il messaggio: " + e.message));
  });
  $("btn-elimina").addEventListener("click", () => {
    spostaEmail("elimina").catch((e) => alert("Non sono riuscito a spostarla: " + e.message));
  });
  $("btn-ripristina").addEventListener("click", () => {
    spostaEmail("ripristina").catch((e) => alert("Non sono riuscito a rimetterla: " + e.message));
  });

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
