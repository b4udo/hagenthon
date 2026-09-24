"""L'orologio del sistema — deliberatamente fermo.

Il corpus di demo contiene scadenze ("entro il 10 ottobre") e appuntamenti
("14 ottobre"). Se "oggi" fosse `date.today()`, il corpus scadrebbe da solo e i
test diventerebbero non deterministici nel giro di qualche giorno.
"""

from __future__ import annotations

import os
from datetime import date

# Martedi' 6 ottobre 2026. Scelto perche' rende coerente tutto il corpus:
# la visita del 14 ottobre cade di mercoledi', la domenica di Luca e' l'11.
OGGI_DEFAULT = date(2026, 10, 6)


def oggi() -> date:
    """La data corrente del sistema.

    Sovrascrivibile con POSTA_CHIARA_OGGI (formato ISO) per i test o per
    spostare la demo in avanti senza toccare il corpus.
    """
    grezzo = os.environ.get("POSTA_CHIARA_OGGI", "").strip()
    if grezzo:
        try:
            return date.fromisoformat(grezzo)
        except ValueError:
            pass
    return OGGI_DEFAULT


def anno_corrente() -> int:
    return oggi().year
