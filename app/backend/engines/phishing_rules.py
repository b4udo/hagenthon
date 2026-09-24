"""Regole di sicurezza — spiegabili, non probabilistiche.

Qui non c'e' e non ci sara' un modello linguistico. Il verdetto deve essere
spiegabile a una persona di 74 anni ("il nome dice Poste Italiane ma
l'indirizzo non e' quello ufficiale") e deve tradursi in un'azione. Una
probabilita' non e' ne' l'una ne' l'altra cosa.

★ Il vincolo piu' importante del file: il numero di telefono dell'azione
suggerita viene SEMPRE da RECAPITI_UFFICIALI qui sotto, mai dal corpo
dell'email. Su una mail di phishing, il numero nel testo e' quello del
truffatore.
"""

from __future__ import annotations

import re

# Tabella statica. Unica fonte dei recapiti proposti a Maria.
RECAPITI_UFFICIALI: dict[str, dict[str, object]] = {
    "poste italiane": {
        "nome": "Poste Italiane",
        "domini": ("poste.it", "posteitaliane.it"),
        "telefono": "803 160",
    },
    "postepay": {
        "nome": "Poste Italiane",
        "domini": ("poste.it", "posteitaliane.it"),
        "telefono": "803 160",
    },
    "inps": {
        "nome": "INPS",
        "domini": ("inps.it", "inps.gov.it"),
        "telefono": "803 164",
    },
    "agenzia delle entrate": {
        "nome": "Agenzia delle Entrate",
        "domini": ("agenziaentrate.gov.it",),
        "telefono": "800 909 696",
    },
    "comune di torino": {
        "nome": "Comune di Torino",
        "domini": ("comune.torino.it",),
        "telefono": "011 011 011",
    },
    "intesa sanpaolo": {
        "nome": "Intesa Sanpaolo",
        "domini": ("intesasanpaolo.com",),
        "telefono": "800 303 303",
    },
}

# Domini istituzionali considerati verificati anche senza un ente citato.
DOMINI_ISTITUZIONALI = (
    ".gov.it",
    "inps.it",
    "comune.torino.it",
    "agenziaentrate.gov.it",
    "aslcittaditorino.it",
    "poste.it",
)

LESSICO_URGENZA = (
    "entro 24 ore",
    "entro 48 ore",
    "immediatamente",
    "conto bloccato",
    "account bloccato",
    "sospensione immediata",
    "sospeso",
    "verifica subito",
    "verificare subito",
    "urgentemente",
    "pena la chiusura",
    "ultimo avviso",
    "scadra tra",
)

RICHIESTE_CREDENZIALI = (
    "password",
    "codice pin",
    " pin ",
    "posteid",
    "otp",
    "codice di sicurezza",
    "numero della carta",
    "numero di carta",
    "coordinate bancarie",
    "credenziali",
    "cvv",
)

_RE_ANCORA = re.compile(r"<a\s[^>]*href\s*=\s*[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.I | re.S)
_RE_URL = re.compile(r"https?://[^\s<>\"')]+", re.I)


def dominio_di(indirizzo_o_url: str) -> str:
    testo = indirizzo_o_url.strip().lower()
    if "@" in testo:
        return testo.rsplit("@", 1)[1].strip(" >")
    testo = re.sub(r"^https?://", "", testo)
    return testo.split("/", 1)[0].split(":", 1)[0].removeprefix("www.")


def _appartiene(dominio: str, domini_ufficiali: tuple) -> bool:
    return any(dominio == d or dominio.endswith("." + d) for d in domini_ufficiali)


def ente_citato(mittente_nome: str, oggetto: str, corpo: str) -> tuple[str, dict] | None:
    """L'ente nominato nel messaggio, se e' fra quelli noti."""
    ago = f"{mittente_nome} {oggetto} {corpo[:400]}".lower()
    for chiave, dati in RECAPITI_UFFICIALI.items():
        if chiave in ago:
            return chiave, dati
    return None


def link_mascherati(corpo: str) -> list[tuple[str, str]]:
    """Coppie (testo visibile, destinazione) che non coincidono."""
    trovati: list[tuple[str, str]] = []

    for href, testo_visibile in _RE_ANCORA.findall(corpo):
        visibili = _RE_URL.findall(testo_visibile)
        if not visibili:
            continue
        if dominio_di(visibili[0]) != dominio_di(href):
            trovati.append((visibili[0], href))

    # Variante senza HTML: "https://www.poste.it/... (https://altro-dominio/...)"
    senza_html = _RE_ANCORA.sub(" ", corpo)
    url = _RE_URL.findall(senza_html)
    domini = {dominio_di(u) for u in url}
    if len(domini) > 1 and len(url) >= 2:
        primo, secondo = url[0], url[1]
        if dominio_di(primo) != dominio_di(secondo):
            trovati.append((primo, secondo))

    return trovati


# Un ente vero scrive "non le chiederemo mai la password": e' un segnale di
# legittimita', non di truffa. Senza questa distinzione la comunicazione
# autentica dell'INPS verrebbe marcata come phishing — un falso positivo che
# costa piu' di quanto valga la regola.
# Espressione regolare e non una lista di sottostringhe: fra "non" e il verbo
# puo' esserci un pronome ("non LE chiediamo", "non VI richiediamo"), e con il
# confronto per sottostringa quella forma sfuggirebbe. E' la stessa famiglia
# del falso positivo che marcava come phishing l'email autentica dell'INPS.
RE_NEGAZIONE = re.compile(
    r"non\s+(?:le\s+|vi\s+|ci\s+|ti\s+)?(?:richied|chied|domand)"
    r"|non\s+(?:verranno|saranno|sara'|sarà)\s+mai\s+richiest"
    r"|mai\b"
    r"|diffid",
    re.IGNORECASE,
)

# Il segnale di truffa non e' *nominare* una credenziale: e' chiederla. L'INPS
# scrive "previa autenticazione con le credenziali digitali" spiegando come si
# accede al portale; il falso Poste scrive "le verranno richiesti: password".
# Solo il secondo e' una richiesta rivolta al lettore.
RICHIESTE_ESPLICITE = (
    "verranno richiesti",
    "saranno richiesti",
    "le chiediamo di inserire",
    "le chiediamo di fornire",
    "la invitiamo a inserire",
    "inserisca",
    "inserire i",
    "inserire le",
    "fornisca",
    "fornire i",
    "comunichi",
    "ci comunichi",
    "digiti",
    "aggiorni i",
    "confermi i suoi dati",
    "e' necessario inserire",
    "è necessario inserire",
    "deve inserire",
    "deve fornire",
)

FINESTRA_NEGAZIONE = 160
FINESTRA_RICHIESTA = 160


def _chiede_credenziali(testo: str) -> bool:
    """Vero solo se le credenziali sono *richieste*, non semplicemente nominate."""
    for parola in RICHIESTE_CREDENZIALI:
        inizio = testo.find(parola)
        while inizio != -1:
            prima = testo[max(0, inizio - FINESTRA_NEGAZIONE) : inizio]
            if not RE_NEGAZIONE.search(prima):
                contesto = testo[max(0, inizio - FINESTRA_RICHIESTA) : inizio + 60]
                if any(r in contesto for r in RICHIESTE_ESPLICITE):
                    return True
            inizio = testo.find(parola, inizio + 1)
    return False


def valuta(
    mittente_nome: str,
    mittente_email: str,
    oggetto: str,
    corpo: str,
    in_rubrica: bool,
) -> tuple[str, list[str], dict | None]:
    """Restituisce (semaforo, segnali, ente_impersonato).

    Il chiamante costruisce da qui il messaggio e l'azione.
    """
    segnali: list[str] = []
    dominio = dominio_di(mittente_email)
    testo = f"{oggetto}\n{corpo}".lower()

    grave = False
    ente_impersonato: dict | None = None

    citato = ente_citato(mittente_nome, oggetto, corpo)
    if citato:
        _, dati = citato
        if not _appartiene(dominio, dati["domini"]):
            grave = True
            ente_impersonato = dati
            segnali.append(
                f"Il nome dice «{dati['nome']}» ma l'indirizzo non e' quello ufficiale "
                f"(«{dominio}»)."
            )

    for visibile, reale in link_mascherati(corpo):
        grave = True
        segnali.append(
            f"C'e' un collegamento che mostra «{dominio_di(visibile)}» "
            f"ma porta a «{dominio_di(reale)}»."
        )
        break

    if _chiede_credenziali(testo):
        grave = True
        segnali.append(
            "Chiede dati riservati (password o codici) che nessun ente chiede per email."
        )

    urgenze = [p for p in LESSICO_URGENZA if p in testo]
    if urgenze:
        segnali.append("Mette fretta per farle fare qualcosa senza pensarci.")

    # ── verdetto ──
    if grave:
        return "rosso", segnali, ente_impersonato

    if in_rubrica:
        return "verde", segnali, None

    # ★ Il dominio verificato viene PRIMA dell'urgenza, non dopo.
    #
    # La spec (02-sicurezza.md) dice: «due segnali +1 o piu', **senza un
    # dominio verificato** -> rosso». Il codice controllava l'urgenza per
    # prima, quindi una comunicazione autentica da inps.it che dicesse «entro
    # 24 ore» e «ultimo avviso» finiva rossa.
    #
    # E' la terza volta che lo stesso errore si presenta in questo motore: un
    # segnale letto senza guardare **chi lo manda** o **se e' negato**. Un ente
    # vero ha tutto il diritto di mettere fretta: e' il mittente a dire se la
    # fretta e' legittima, non la parola.
    if any(dominio == d.lstrip(".") or dominio.endswith(d) for d in DOMINI_ISTITUZIONALI):
        if urgenze:
            return "giallo", segnali, None
        return "verde", segnali, None

    if len(urgenze) >= 2:
        return "rosso", segnali, ente_impersonato

    # Uno sconosciuto innocuo e' giallo, mai verde. Il costo di un falso verde
    # (Maria si fida di una truffa) non e' paragonabile a quello di un falso
    # giallo (Maria chiede al nipote).
    segnali.append("Non conosco questo mittente.")
    return "giallo", segnali, None
