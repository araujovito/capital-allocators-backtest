"""Universo completo da B3, sem viés de sobrevivência.

O COTAHIST publica **todo** papel negociado em cada ano, inclusive os que
deixaram de existir. É a única fonte deste projeto imune a viés de sobrevivência
por construção — e ela já estava no disco, baixada para os três tickers do estudo.

Este módulo lê os mesmos arquivos sem filtrar por ticker: monta o painel mensal de
tudo o que negociou entre 2006 e 2025. Serve à pergunta que o README declarou como
ataque em aberto: os oito allocators foram escolhidos com informação de 2005, mas
**por alguém que já sabia quais existiriam em 2025**.

⚠️ Os preços são **brutos**, sem ajuste por provento ou desdobramento — a mesma
ressalva de `ingest.b3`. Para o universo inteiro não há como corrigir isso ativo a
ativo, então este painel serve para contar empresas e medir permanência, **não**
para calcular retorno de vinte anos. O que ele não sustenta está escrito em
`analysis.sobrevivencia`.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

from capallo.ingest.b3 import CODBDI_ACEITOS

#: Mercado à vista. O resto do arquivo é opção, termo e leilão.
TPMERC_AVISTA = "010"

#: Volume financeiro mínimo no mês de referência. Sem corte de liquidez o universo
#: enche de papéis que negociaram uma vez no mês, cujo "retorno" é ruído de um
#: negócio. R$ 1 milhão por mês é baixo o bastante para não excluir empresa real e
#: alto o bastante para excluir o que não dava para comprar.
VOLUME_MINIMO = 1_000_000.0

#: Mês em que o universo é fotografado, e mês final de referência.
MES_BASE, MES_FIM = "200601", "202512"


def _ler_ano(caminho: Path) -> pd.DataFrame:
    """Último pregão de cada mês, por papel, num arquivo anual do COTAHIST."""
    registros: dict[tuple[str, str], tuple[str, float, float]] = {}
    with zipfile.ZipFile(caminho) as z, z.open(z.namelist()[0]) as f:
        for linha in io.TextIOWrapper(f, encoding="latin-1"):
            if (linha[0:2] != "01" or linha[24:27] != TPMERC_AVISTA
                    or linha[10:12] not in CODBDI_ACEITOS):
                continue
            data = linha[2:10]
            # O dicionário guarda a última ocorrência do mês porque o arquivo vem
            # em ordem cronológica: o último a escrever é o último pregão.
            registros[(linha[12:24].strip(), data[:6])] = (
                linha[27:39].strip(),
                int(linha[108:121]) / 100,
                int(linha[170:188]) / 100,
            )
    return pd.DataFrame(
        [{"ticker": t, "mes": m, "nome": v[0], "preco": v[1], "volume": v[2]}
         for (t, m), v in registros.items()]
    )


def build(raw_dir: Path, out_dir: Path,
          anos: range = range(2006, 2026)) -> pd.DataFrame:
    """Painel mensal de todo papel negociado à vista na janela do estudo."""
    partes = []
    for ano in anos:
        caminho = raw_dir / f"COTAHIST_A{ano}.ZIP"
        if not caminho.exists():
            raise FileNotFoundError(f"{caminho} — rode `capallo fetch-b3` antes")
        partes.append(_ler_ano(caminho))
    df = pd.concat(partes, ignore_index=True).sort_values(["ticker", "mes"])
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "b3_universo.parquet", index=False)
    return df.reset_index(drop=True)


def universo_investavel(painel: pd.DataFrame, mes: str = MES_BASE,
                        volume_minimo: float = VOLUME_MINIMO) -> pd.DataFrame:
    """Uma linha por empresa negociável no mês de referência.

    Uma classe por empresa — a de maior volume —, porque para contar empresas ON e
    PN da mesma companhia são a mesma aposta, e mantê-las separadas inflaria o
    universo com duplicatas.
    """
    mes_base = painel[(painel.mes == mes) & (painel.volume >= volume_minimo)]
    return (mes_base.sort_values("volume").groupby("nome").tail(1)
            .sort_values("nome").reset_index(drop=True))


def validate(out_dir: Path) -> list[str]:
    path = out_dir / "b3_universo.parquet"
    if not path.exists():
        return [f"{path} não existe"]
    df = pd.read_parquet(path)

    problemas = []
    meses = set(df.mes)
    faltando = [m for m in (MES_BASE, MES_FIM) if m not in meses]
    if faltando:
        problemas.append(f"meses de referência ausentes: {faltando}")
    if df.ticker.nunique() < 1000:
        problemas.append(f"{df.ticker.nunique()} tickers — o filtro provavelmente "
                         f"está estreito demais para ser 'o universo'")
    # A guarda que dá sentido ao módulo: os três tickers do estudo têm de estar
    # aqui, com os mesmos preços brutos que `ingest.b3` coletou separadamente.
    for ticker in ("ITSA4", "BRAP4", "PIBB11"):
        if ticker not in set(df.ticker):
            problemas.append(f"{ticker} ausente do universo — o parser divergiu de ingest.b3")
    if (df.preco <= 0).any():
        problemas.append("preço zero ou negativo")
    return problemas
