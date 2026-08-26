"""Mapa ticker do estudo → símbolo Yahoo.

Isolado de propósito: o símbolo é detalhe de fonte, não parte do universo. Se a
fonte mudar, muda este arquivo, não `universe.py`.
"""

YAHOO_SYMBOLS: dict[str, str] = {
    # Capital Allocators
    "ITSA4": "ITSA4.SA",
    "BRAP4": "BRAP4.SA",
    "BRK-B": "BRK-B",
    "MKL": "MKL",
    "INVE-B": "INVE-B.ST",
    "GBLB": "GBLB.BR",
    "8058": "8058.T",
    "8031": "8031.T",
    # ETFs
    "PIBB11": "PIBB11.SA",
    "IVV": "IVV",
    "IEV": "IEV",
    "EWJ": "EWJ",
    # Câmbio (BRL como moeda base)
    "USDBRL": "USDBRL=X",
    "EURBRL": "EURBRL=X",
    "SEKBRL": "SEKBRL=X",
    "JPYBRL": "JPYBRL=X",
}
