"""Universo de ativos do estudo.

Congelado em 2026-08-26. A regra anti-cherry-picking exige que todo ativo seja
justificável com informação existente em 31/12/2005. Depois de fechado o universo,
resultado ruim não é motivo para remover um ativo.
"""

from dataclasses import dataclass
from enum import Enum


class Region(str, Enum):
    BR = "BR"
    US = "US"
    EU = "EU"
    JP = "JP"


class Currency(str, Enum):
    BRL = "BRL"
    USD = "USD"
    SEK = "SEK"
    EUR = "EUR"
    JPY = "JPY"


@dataclass(frozen=True)
class Asset:
    ticker: str
    name: str
    region: Region
    listing_currency: Currency
    #: Moeda da economia subjacente. Difere de listing_currency nos ETFs listados
    #: em USD que replicam mercados não-americanos — o wrapper é transparente para
    #: a decomposição cambial.
    exposure_currency: Currency
    withholding_tax: float


CAPITAL_ALLOCATORS: tuple[Asset, ...] = (
    Asset("ITSA4", "Itaúsa", Region.BR, Currency.BRL, Currency.BRL, 0.00),
    Asset("BRAP4", "Bradespar", Region.BR, Currency.BRL, Currency.BRL, 0.00),
    Asset("BRK-B", "Berkshire Hathaway", Region.US, Currency.USD, Currency.USD, 0.30),
    Asset("MKL", "Markel", Region.US, Currency.USD, Currency.USD, 0.30),
    Asset("INVE-B", "Investor AB", Region.EU, Currency.SEK, Currency.SEK, 0.30),
    Asset("GBLB", "Groupe Bruxelles Lambert", Region.EU, Currency.EUR, Currency.EUR, 0.30),
    Asset("8058", "Mitsubishi Corporation", Region.JP, Currency.JPY, Currency.JPY, 0.15),
    Asset("8031", "Mitsui & Co.", Region.JP, Currency.JPY, Currency.JPY, 0.15),
)

#: Experimento Historical Reality: apenas produtos realmente compráveis em 2006.
PASSIVE_ETFS: tuple[Asset, ...] = (
    Asset("PIBB11", "PIBB IBrX-50", Region.BR, Currency.BRL, Currency.BRL, 0.00),
    Asset("IVV", "iShares Core S&P 500", Region.US, Currency.USD, Currency.USD, 0.30),
    Asset("IEV", "iShares S&P Europe 350", Region.EU, Currency.USD, Currency.EUR, 0.30),
    Asset("EWJ", "iShares MSCI Japan", Region.JP, Currency.USD, Currency.JPY, 0.30),
)

BY_TICKER: dict[str, Asset] = {a.ticker: a for a in (*CAPITAL_ALLOCATORS, *PASSIVE_ETFS)}


def by_region(assets: tuple[Asset, ...], region: Region) -> tuple[Asset, ...]:
    return tuple(a for a in assets if a.region is region)
