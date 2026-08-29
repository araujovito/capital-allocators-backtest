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

#: Experimento Index Benchmark (§7): o **índice** no lugar do produto, para separar
#: "o allocator venceu o mercado" de "o allocator venceu o ETF que existia em 2006".
#: Não é um universo alternativo — é a mesma exposição regional sem taxa de
#: administração, sem tracking error e sem o custo de embrulhar tudo num fundo.
#:
#: ⚠️ Duas das quatro linhas são **substitutas declaradas**. O índice do PIBB11
#: (IBrX-50) e o do EWJ (MSCI Japan) são publicados de graça pelos próprios
#: provedores. Os da S&P — S&P 500 e S&P Europe 350 — não são: o site responde 403.
#: MSCI USA e MSCI Europe entram no lugar, cobrindo o mesmo mercado com outra regra
#: de construção. O custo dessa troca é medido, não suposto — ver `ingest.indices`.
INDICES: tuple[Asset, ...] = (
    Asset("IBXL", "IBrX-50 (B3)", Region.BR, Currency.BRL, Currency.BRL, 0.00),
    Asset("MXUS", "MSCI USA", Region.US, Currency.USD, Currency.USD, 0.30),
    Asset("MXEU", "MSCI Europe", Region.EU, Currency.USD, Currency.EUR, 0.30),
    Asset("MXJP", "MSCI Japan", Region.JP, Currency.USD, Currency.JPY, 0.30),
)

#: Experimento Modern Alternative (§7): o contrafactual com o produto que existe
#: **hoje** e não existia em 2006 — um fundo global de índice, um ticker só,
#: comprável em reais sem conta no exterior.
#:
#: A escolha do MSCI ACWI não é hindsight sobre qual mercado ganhou: o índice usa
#: os pesos **contemporâneos** de cada data, então em 2006 ele carregava a
#: participação americana de 2006, não a de hoje. O anacronismo está no **acesso
#: ao produto**, não na regra do índice — e é exatamente esse o contrafactual. A
#: ideia de comprar o mundo ponderado por capitalização já era recomendação de
#: manual em 2006; o que faltava ao investidor brasileiro era o veículo.
#:
#: ⚠️ Viola a regra anti-cherry-picking **de propósito**, e por isso os resultados
#: nunca se misturam com os do placar principal (§7).
MODERN_ALTERNATIVE: tuple[Asset, ...] = (
    Asset("ACWI", "MSCI ACWI", Region.US, Currency.USD, Currency.USD, 0.30),
)

#: Referência de renda fixa com retorno real contratado. Fica ao lado do CDI, não
#: dentro das carteiras: é régua, não ativo do universo.
#:
#: ⚠️ Declarado como pendente em `docs/decisions.md` desde 26/08/2026 — antes de
#: existir motor e antes de qualquer resultado. Não é acréscimo pós-resultado, e o
#: `Tesouro IPCA+` já era comprável em 31/12/2005, o que a regra anti-cherry-picking
#: exigiria mesmo se fosse ativo.
RENDA_FIXA: tuple[Asset, ...] = (
    Asset("IPCAP", "Tesouro IPCA+ (NTN-B Principal)", Region.BR, Currency.BRL,
          Currency.BRL, 0.00),
)

#: Índice → ETF da mesma região, para medir o custo do produto.
INDICE_DO_ETF: dict[str, str] = {
    "PIBB11": "IBXL", "IVV": "MXUS", "IEV": "MXEU", "EWJ": "MXJP",
}

BY_TICKER: dict[str, Asset] = {
    a.ticker: a
    for a in (*CAPITAL_ALLOCATORS, *PASSIVE_ETFS, *INDICES, *MODERN_ALTERNATIVE,
              *RENDA_FIXA)
}


def by_region(assets: tuple[Asset, ...], region: Region) -> tuple[Asset, ...]:
    return tuple(a for a in assets if a.region is region)
