"""06 · Compositore — la risposta si sceglie, non si scrive.

Specifica: agents/runtime/06-compositore.md

E' il punto esatto in cui Maria oggi si ferma: il riquadro bianco vuoto chiede
«cosa vuoi scrivere?», domanda a cui non sa rispondere per iscritto. Qui la
domanda diventa «cosa vuoi fare?», e le risposte sono tre pulsanti.
"""

from __future__ import annotations

import json

from ..contracts import BozzaRisposta, Categoria, Fatto, Intento
from ..engines import normalize
from ..llm import client


def esegui(
    mittente_nome: str,
    categoria: Categoria,
    fatti_verificati: list[Fatto],
    nome_utente: str,
) -> tuple[list[BozzaRisposta], int]:
    risposta = _prova_seam(mittente_nome, fatti_verificati, nome_utente)
    if risposta is not None:
        return risposta

    return _a_regole(mittente_nome, categoria, fatti_verificati, nome_utente), 0


def _apertura(mittente_nome: str, categoria: Categoria) -> str:
    if categoria is Categoria.PERSONA_CONOSCIUTA:
        return f"Ciao {mittente_nome.split()[0]},"
    if categoria is Categoria.SANITA:
        return f"Gentile {mittente_nome},"
    return "Spettabile ufficio,"


def _riferimento(fatti: list[Fatto]) -> str:
    """La frase che cita data e ora — solo se sono fra i fatti verificati.

    Uno slot senza fatto corrispondente si omette: la frase si accorcia, non
    si inventa. Una bozza che afferma un orario sbagliato *a nome di Maria*
    e' molto peggio di una bozza vaga.
    """
    data = next((f for f in fatti if f.tipo.value == "data"), None)
    orario = next((f for f in fatti if f.tipo.value == "orario"), None)

    if data and orario:
        return (
            f" del {normalize.formatta_data_italiana(data.valore_normalizzato)}"
            f" alle ore {orario.valore_normalizzato}"
        )
    if data:
        return f" del {normalize.formatta_data_italiana(data.valore_normalizzato)}"
    if orario:
        return f" alle ore {orario.valore_normalizzato}"
    return ""


def _a_regole(
    mittente_nome: str,
    categoria: Categoria,
    fatti: list[Fatto],
    nome_utente: str,
) -> list[BozzaRisposta]:
    apertura = _apertura(mittente_nome, categoria)
    rif = _riferimento(fatti)
    chiusura = (
        f"\n\nCordiali saluti,\n{nome_utente}"
        if categoria is not Categoria.PERSONA_CONOSCIUTA
        else f"\n\nUn abbraccio,\n{nome_utente.split()[0]}"
    )
    usati = [f for f in fatti if f.tipo.value in ("data", "orario")]

    return [
        BozzaRisposta(
            intento=Intento.CONFERMA,
            etichetta="Confermo che vengo",
            testo=f"{apertura}\nle confermo che sarò presente all'appuntamento{rif}.{chiusura}",
            fatti_usati=usati,
        ),
        BozzaRisposta(
            intento=Intento.CHIEDI_INFO,
            etichetta="Ho bisogno di più informazioni",
            testo=(
                f"{apertura}\nho ricevuto la sua comunicazione"
                f"{rif} ma non mi è tutto chiaro.\n"
                f"Può spiegarmi meglio cosa devo fare?{chiusura}"
            ),
            fatti_usati=usati,
        ),
        BozzaRisposta(
            intento=Intento.NON_POSSO,
            etichetta="Non posso, chiedo di spostare",
            testo=(
                f"{apertura}\npurtroppo non posso essere presente all'appuntamento{rif}.\n"
                f"Le chiedo la cortesia di spostarlo a un'altra data.{chiusura}"
            ),
            fatti_usati=usati,
        ),
    ]


def _prova_seam(
    mittente_nome: str, fatti: list[Fatto], nome_utente: str
) -> tuple[list[BozzaRisposta], int] | None:
    elenco = "\n".join(
        f"- {f.tipo.value}: {f.testo_originale} (valore esatto: {f.valore_normalizzato})"
        for f in fatti
    ) or "(nessuno)"

    risposta = client.invoca(
        "compositore",
        client.MODELLO_LINGUA,
        {
            "mittente_nome": mittente_nome,
            "nome_utente": nome_utente,
            "fatti_verificati": elenco,
        },
    )
    if risposta is None:
        return None

    try:
        dati = json.loads(risposta.contenuto)
        bozze = [BozzaRisposta.model_validate(b) for b in dati["bozze"]]
        return bozze, risposta.token
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
