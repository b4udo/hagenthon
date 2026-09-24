/* Posta Chiara — la voce.
 *
 * Due capacita' distinte, con due proprieta' di privacy diverse. La
 * distinzione non e' un dettaglio: e' dichiarata in interfaccia, perche'
 * riguarda dati sanitari e previdenziali di una persona anziana.
 *
 *   LEGGERE AD ALTA VOCE  (speechSynthesis)
 *     Sintesi vocale del browser. Gira **sul dispositivo**, con le voci
 *     installate nel sistema operativo. Nessun testo esce dalla macchina.
 *
 *   DETTARE            (SpeechRecognition)
 *     ★ In Chrome e Edge il riconoscimento vocale **non e' locale**: l'audio
 *     viene inviato a un servizio del fornitore del browser. Non e' una scelta
 *     nostra e non possiamo cambiarla dall'interno della pagina.
 *     Conseguenza: la dettatura e' l'unica funzione di Posta Chiara che fa
 *     uscire qualcosa dal dispositivo. Per questo e' **esplicita, facoltativa,
 *     e avvisata prima del primo uso** — mai attiva da sola.
 *
 * Perche' la voce e' qui e non fra i "se avanza tempo": Maria usa i vocali di
 * WhatsApp e non scrive. Sa parlare, non digitare. Una casella di testo vuota
 * e' esattamente il punto in cui oggi si ferma.
 *
 * Nessuna libreria, nessuna CDN: sono due API del browser.
 */

"use strict";

const Voce = (() => {

  const sintesi = window.speechSynthesis || null;
  const MotoreAscolto = window.SpeechRecognition || window.webkitSpeechRecognition || null;

  // Piu' lento del parlato normale. Con la voce predefinita a velocita' 1 le
  // date lunghe ("quattordici ottobre duemilaventisei") diventano un blocco
  // unico difficile da seguire.
  const VELOCITA = 0.92;

  let voceItaliana = null;
  let alParlare = null;   // callback di stato: (sta_parlando) => void
  let ascolto = null;     // istanza di riconoscimento in corso

  // ─────────────── leggere ad alta voce ───────────────

  function scegliVoce() {
    if (!sintesi) return;
    const voci = sintesi.getVoices();
    if (!voci.length) return;

    // Preferenza: una voce italiana vera; in mancanza, qualunque cosa parli
    // italiano; in mancanza ancora, si rinuncia invece di leggere l'italiano
    // con la fonetica inglese, che e' peggio del silenzio.
    voceItaliana =
      voci.find((v) => v.lang === "it-IT" && v.localService) ||
      voci.find((v) => v.lang === "it-IT") ||
      voci.find((v) => String(v.lang).toLowerCase().startsWith("it")) ||
      null;
  }

  if (sintesi) {
    scegliVoce();
    // getVoices() e' asincrono al primo caricamento su quasi tutti i browser.
    sintesi.addEventListener("voiceschanged", scegliVoce);
  }

  function puoLeggere() {
    return Boolean(sintesi);
  }

  function leggi(testo, quandoFinisce) {
    if (!sintesi || !testo) return;
    // `cancel()` diretto e non `fermaLettura()`: quest'ultima notifica
    // "non sto piu' parlando", e la notifica arriverebbe *dopo* che il
    // chiamante ha gia' segnato il proprio pulsante come attivo, spegnendolo.
    sintesi.cancel();

    // Le sigle lette lettera per lettera suonano come parole senza senso.
    const pronunciabile = String(testo)
      .replace(/\bINPS\b/g, "I N P S")
      .replace(/\bASL\b/g, "A S L")
      .replace(/\bSPID\b/g, "spid")
      .replace(/\bPEC\b/g, "pec")
      .replace(/€\s?/g, " euro ")
      .replace(/\bdott\.ssa\b/gi, "dottoressa")
      .replace(/\bdott\.\b/gi, "dottor")
      .replace(/\bSig\.ra\b/gi, "signora")
      .replace(/\s+/g, " ")
      .trim();

    const frase = new SpeechSynthesisUtterance(pronunciabile);
    frase.lang = "it-IT";
    frase.rate = VELOCITA;
    if (voceItaliana) frase.voice = voceItaliana;

    frase.onstart = () => { if (alParlare) alParlare(true); };
    frase.onend = () => {
      if (alParlare) alParlare(false);
      if (quandoFinisce) quandoFinisce();
    };
    frase.onerror = () => { if (alParlare) alParlare(false); };

    sintesi.speak(frase);
  }

  function fermaLettura() {
    if (!sintesi) return;
    sintesi.cancel();
    if (alParlare) alParlare(false);
  }

  function staParlando() {
    return Boolean(sintesi && sintesi.speaking);
  }

  function osservaLettura(callback) {
    alParlare = callback;
  }

  // ─────────────── dettare ───────────────

  function puoAscoltare() {
    return Boolean(MotoreAscolto);
  }

  /** Avvia la dettatura.
   *
   * `alTesto(testo, definitivo)` viene chiamata mentre la persona parla:
   * `definitivo` distingue l'ipotesi provvisoria dal testo consolidato, cosi'
   * l'interfaccia puo' mostrare in tempo reale che la sta sentendo. Vedere
   * comparire le proprie parole e' il segnale che il microfono funziona: senza,
   * si resta a parlare nel vuoto senza sapere se sta succedendo qualcosa.
   */
  function ascolta({ alTesto, alFine, alErrore }) {
    if (!MotoreAscolto) return false;
    fermaAscolto();
    // La sintesi in corso coprirebbe il microfono e verrebbe trascritta.
    fermaLettura();

    const motore = new MotoreAscolto();
    motore.lang = "it-IT";
    motore.continuous = true;      // non si chiude alla prima pausa di respiro
    motore.interimResults = true;

    let consolidato = "";

    motore.onresult = (evento) => {
      let provvisorio = "";
      for (let i = evento.resultIndex; i < evento.results.length; i++) {
        const pezzo = evento.results[i][0].transcript;
        if (evento.results[i].isFinal) consolidato += pezzo;
        else provvisorio += pezzo;
      }
      if (alTesto) alTesto((consolidato + provvisorio).trim(), Boolean(consolidato));
    };

    motore.onerror = (evento) => {
      const spiegazioni = {
        "not-allowed": "Il microfono non è stato autorizzato. Lo consenta nella barra del browser e riprovi.",
        "service-not-allowed": "Il microfono non è stato autorizzato.",
        "no-speech": "Non ho sentito nulla. Prema di nuovo e parli pure con calma.",
        "audio-capture": "Non trovo un microfono collegato.",
        "network": "Il riconoscimento vocale del browser non è raggiungibile.",
      };
      if (alErrore) alErrore(spiegazioni[evento.error] || "Non sono riuscito ad ascoltare.");
    };

    motore.onend = () => {
      ascolto = null;
      if (alFine) alFine(consolidato.trim());
    };

    ascolto = motore;
    motore.start();
    return true;
  }

  function fermaAscolto() {
    if (ascolto) {
      ascolto.stop();
      ascolto = null;
    }
  }

  function staAscoltando() {
    return Boolean(ascolto);
  }

  return {
    puoLeggere, leggi, fermaLettura, staParlando, osservaLettura,
    puoAscoltare, ascolta, fermaAscolto, staAscoltando,
  };
})();
