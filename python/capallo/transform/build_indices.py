"""Retenção na fonte sobre os índices, para a perna do Index Benchmark.

Reaproveita inteiro o método de `transform.us_net` — o provento do mês é o que
sobra entre a variante bruta e a de preço puro, e a alíquota incide só sobre ele.
Aqui o insumo vem pronto: a MSCI publica as duas variantes do mesmo índice, então
não é preciso deduzir nada da fonte.

## Por que não usar a variante líquida da MSCI

`NETR` existe e já vem líquida — mas com **as alíquotas que a MSCI assume**, que
são as de um investidor institucional estrangeiro genérico, não os 30% que a §4
da metodologia congelou para o investidor brasileiro antes de qualquer resultado.
Usar `NETR` trocaria o regime tributário do estudo pelo de outra pessoa, e faria a
perna do índice ser tributada diferente da perna do ETF — a comparação passaria a
medir regime fiscal em vez de custo de produto, que é o que ela existe para medir.

`NETR` fica disponível como referência: `distancia_da_variante_liquida()` mede o
quanto as duas convenções diferem, para o leitor saber o tamanho da escolha.

⚠️ O IBrX-50 não passa por aqui. Índice brasileiro, investidor brasileiro,
alíquota congelada em zero na §4 — não há retenção a aplicar, e inventar uma
para "ficar simétrico" seria pior que a assimetria.

## A taxa do Modern Alternative

O grupo `index` é o mercado sem produto: taxa zero, por definição — é o piso
teórico, não algo comprável. O grupo `modern` é o contrário: existe justamente
para representar um **produto de verdade**, comprável hoje, e um produto cobra.

Então a série do ACWI sai daqui com uma taxa de administração descontada mês a
mês. A alíquota base é `TER_MODERN`, e o número é **premissa declarada, não fato
coletado**: os fundos globais de índice acessíveis hoje ficam entre cerca de 0,06%
ao ano no extremo mais barato e cerca de 0,30% nos veículos negociados na B3, que
é onde o investidor deste estudo compraria sem abrir conta no exterior. A base é a
ponta cara dessa faixa — escolher a ponta barata favoreceria o contrafactual, que
é o lado contra o qual a tese do estudo está sendo testada.

Escolha conservadora não dispensa medir: `capallo modern-alternative` roda o
experimento inteiro em três alíquotas, e a conclusão não pode depender de qual.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from capallo.transform.us_net import net_series
from capallo.universe import BY_TICKER

#: Taxa de administração anual do produto moderno. Premissa declarada — ver o
#: cabeçalho do módulo — e medida em três níveis por `capallo modern-alternative`.
TER_MODERN = 0.0030


def build(curated: Path, ter_modern: float = TER_MODERN) -> pd.DataFrame:
    """Adiciona `close_net` a `indices.parquet`, sem descartar o bruto.

    Para o grupo `modern`, `close_net` já sai **líquido da taxa de administração**:
    é um produto, não um índice, e comparar um produto sem a taxa dele com um
    ativo real seria o mesmo erro que o Index Benchmark existe para expor.
    """
    path = curated / "indices.parquet"
    df = pd.read_parquet(path)
    partes = []
    for ticker, g in df.groupby("ticker"):
        g = g.sort_values("date").copy()
        w = BY_TICKER[ticker].withholding_tax
        liquido = net_series(g, w)
        if (g.grupo == "modern").all():
            # A taxa corre por tempo decorrido, não por evento: um duodécimo do
            # ano por mês, composto, do primeiro mês em diante.
            meses = pd.Series(range(len(g)), index=liquido.index)
            liquido = liquido * (1 - ter_modern) ** (meses / 12)
        g["close_net"] = liquido.to_numpy()
        g["ter"] = ter_modern if (g.grupo == "modern").all() else 0.0
        partes.append(g)
    out = pd.concat(partes, ignore_index=True)
    out.to_parquet(path, index=False)
    return out


def custo_da_taxa(curated: Path) -> pd.DataFrame:
    """Quanto a taxa de administração tira do produto moderno em vinte anos.

    Separado do custo da retenção de propósito: são duas mordidas de naturezas
    diferentes — uma é imposto sobre o provento, a outra é preço do veículo — e
    somá-las numa linha só esconderia que apenas a segunda depende de premissa
    nossa.
    """
    df = pd.read_parquet(curated / "indices.parquet")
    linhas = []
    for ticker, g in df[df.grupo == "modern"].groupby("ticker"):
        g = g.sort_values("date")
        ter = float(g.ter.iloc[0])
        sem_taxa = net_series(g, BY_TICKER[ticker].withholding_tax)
        com_taxa = g.close_net
        n = len(g) - 1
        linhas.append({
            "produto": ticker,
            "ter": ter,
            "sem_taxa_aa": float(sem_taxa.iloc[-1] / sem_taxa.iloc[0]) ** (12 / n) - 1,
            "com_taxa_aa": float(com_taxa.iloc[-1] / com_taxa.iloc[0]) ** (12 / n) - 1,
        })
    out = pd.DataFrame(linhas)
    out["custo_pp_aa"] = (out.sem_taxa_aa - out.com_taxa_aa) * 100
    return out


def custo_da_retencao(curated: Path) -> pd.DataFrame:
    """Quanto a retenção tira de cada índice em vinte anos."""
    df = pd.read_parquet(curated / "indices.parquet")
    linhas = []
    for ticker, g in df.groupby("ticker"):
        g = g.sort_values("date")
        bruto = float(g.close_adj.iloc[-1] / g.close_adj.iloc[0])
        liquido = float(g.close_net.iloc[-1] / g.close_net.iloc[0])
        linhas.append({
            "indice": ticker,
            "aliquota": BY_TICKER[ticker].withholding_tax,
            "bruto_aa": bruto ** (1 / 20) - 1,
            "liquido_aa": liquido ** (1 / 20) - 1,
            "custo_pp_aa": (bruto ** (1 / 20) - liquido ** (1 / 20)) * 100,
        })
    return pd.DataFrame(linhas).sort_values("custo_pp_aa", ascending=False)


def distancia_da_variante_liquida(curated: Path) -> pd.DataFrame:
    """Compara a nossa retenção com a que a MSCI já aplica na variante `NETR`.

    Serve para dimensionar a escolha, não para substituí-la: se as duas
    convenções ficassem muito distantes, a comparação com o ETF — que carrega os
    mesmos 30% — passaria a depender de qual delas foi usada.
    """
    from capallo.ingest.indices import MSCI_CODES, fetch_msci

    df = pd.read_parquet(curated / "indices.parquet")
    linhas = []
    for ticker, code in MSCI_CODES.items():
        g = df[df.ticker == ticker].sort_values("date")
        nosso = float(g.close_net.iloc[-1] / g.close_net.iloc[0]) ** (1 / 20) - 1
        netr = fetch_msci(code, "NETR")
        deles = float(netr.iloc[-1] / netr.iloc[0]) ** (1 / 20) - 1
        linhas.append({
            "indice": ticker,
            "nossa_retencao_aa": nosso,
            "msci_netr_aa": deles,
            "diferenca_pp": (nosso - deles) * 100,
        })
    return pd.DataFrame(linhas)


def validate(curated: Path) -> list[str]:
    path = curated / "indices.parquet"
    if not path.exists():
        return [f"{path} não existe"]
    df = pd.read_parquet(path)
    if "close_net" not in df.columns:
        return ["indices.parquet sem a coluna close_net"]

    problemas = []
    for ticker, g in df.groupby("ticker"):
        g = g.sort_values("date")
        w = BY_TICKER[ticker].withholding_tax
        razao = float(g.close_net.iloc[-1] / g.close_net.iloc[0]) / float(
            g.close_adj.iloc[-1] / g.close_adj.iloc[0]
        )
        if (g.grupo == "modern").all() and float(g.ter.iloc[0]) <= 0:
            problemas.append(f"{ticker}: produto do Modern Alternative sem taxa")
        if w == 0 and abs(razao - 1.0) > 1e-9:
            problemas.append(f"{ticker}: alíquota zero, mas o líquido difere do bruto")
        if w > 0 and razao >= 1.0:
            problemas.append(f"{ticker}: imposto não pode aumentar o retorno")
        if (g.close_net <= 0).any():
            problemas.append(f"{ticker}: série líquida com nível não positivo")
    return problemas
