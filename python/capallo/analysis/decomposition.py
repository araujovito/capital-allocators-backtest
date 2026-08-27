"""Decomposição do retorno e Allocator Premium por região.

Duas perguntas que o placar não responde.

**De onde veio o retorno?** O investidor brasileiro que compra Mitsubishi ganha
com a empresa e com o iene, e as duas coisas não se somam — se multiplicam. A
decomposição separa os três fatores cujo produto é o resultado em poder de compra:

    retorno real em BRL = retorno local do ativo × efeito da moeda ÷ inflação

**O prêmio compensou o risco?** `docs/methodology.md`, seção 10: "+1 p.p. ao ano"
só significa algo junto de quanto risco extra foi necessário para obtê-lo.

## O wrapper em dólar é transparente

IEV e EWJ replicam Europa e Japão, mas são liquidados em dólar. Atribuir o efeito
cambial deles ao dólar deixaria a decomposição assimétrica: a perna passiva
apareceria como aposta em dólar contra uma perna ativa em euro e iene, quando as
duas carregam a mesma economia subjacente.

A regra da seção 5 da metodologia é atribuir o câmbio à **moeda do mercado
subjacente**. Na prática o wrapper cancela, e o cancelamento é exato:

    tr_brl = tr_usd × USD/BRL = (tr_brl ÷ EUR/BRL) × EUR/BRL

O retorno local em euro não é observado diretamente — é **derivado** do resultado
em real dividido pelo câmbio da moeda de exposição. Nenhuma cotação é inventada:
é a mesma identidade, lida na outra ordem.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from capallo.analysis.scoreboard import _deflator, evaluate
from capallo.universe import BY_TICKER

ANOS = 20

#: Diferença de volatilidade abaixo da qual as duas carteiras correram o **mesmo**
#: risco. Sem esse piso, os EUA — onde a diferença é de 0,005 p.p. — dividiam o
#: prêmio por quase zero e devolviam "prêmio por unidade de risco" de −26,6: um
#: número de aparência plausível saído de uma divisão por ruído. É a mesma
#: armadilha que o `EPS` de `metrics.py` documenta, na escala da volatilidade.
VOL_MINIMA_PP = 0.5


def _fx_mensal(curated: Path, moeda: str, meses: pd.Index) -> pd.Series:
    """PTAX de venda no último dia com cotação de cada mês do painel."""
    if moeda == "BRL":
        return pd.Series(1.0, index=meses)
    ptax = pd.read_parquet(curated / "ptax.parquet")
    cot = ptax[ptax.currency == moeda].sort_values("date")
    if cot.empty:
        raise ValueError(f"PTAX não cobre {moeda}")
    cot = cot.assign(month=cot.date.dt.to_period("M").astype(str))
    return cot.groupby("month").ask.last().reindex(meses).ffill()


def by_asset(curated: Path, engine: Path) -> pd.DataFrame:
    """Fatores acumulados e anualizados de cada ativo, na janela do estudo."""
    panel = pd.read_csv(engine / "panel.csv")
    ipca = 1 / _deflator(curated)  # índice de preços, base no primeiro mês

    linhas = []
    for ticker, g in panel.groupby("ticker"):
        g = g.sort_values("month").reset_index(drop=True)
        exposicao = BY_TICKER[ticker].exposure_currency.value
        fx = _fx_mensal(curated, exposicao, pd.Index(g.month))

        brl = float(g.tr_brl.iloc[-1] / g.tr_brl.iloc[0])
        cambio = float(fx.iloc[-1] / fx.iloc[0])
        # Local na moeda de exposição, derivado — ver o cancelamento do wrapper.
        local = brl / cambio
        infl = float(ipca.iloc[-1] / ipca.iloc[0])

        linhas.append({
            "ticker": ticker,
            "moeda_exposicao": exposicao,
            "moeda_negociacao": g.currency.iloc[0],
            "local": local,
            "cambio": cambio,
            "nominal_brl": brl,
            "real_brl": brl / infl,
            "local_aa": local ** (1 / ANOS) - 1,
            "cambio_aa": cambio ** (1 / ANOS) - 1,
            "real_brl_aa": (brl / infl) ** (1 / ANOS) - 1,
        })
    return pd.DataFrame(linhas).sort_values("real_brl_aa", ascending=False).reset_index(drop=True)


#: Pares comparáveis: allocators e ETF da mesma região, mesma janela, mesmas regras.
PARES: tuple[tuple[str, str, str], ...] = (
    ("Brasil", "br_allocators", "br_etf"),
    ("EUA", "us_allocators", "us_etf"),
    ("Europa", "eu_allocators", "eu_etf"),
    ("Japão", "jp_allocators", "jp_etf"),
    ("Global", "capital_allocators", "passive_etfs"),
)


def premium(results: Path, curated: Path) -> pd.DataFrame:
    """Prêmio dos allocators sobre o ETF equivalente, sempre ao lado do risco.

    A coluna `premio_por_vol_extra` só existe quando houve risco extra **material**
    a compensar. Onde o allocator entregou mais retorno com menos volatilidade não
    há prêmio a normalizar — há **dominância**, e ela ganha rótulo próprio. E onde
    a diferença de volatilidade é menor que `VOL_MINIMA_PP`, as duas carteiras
    correram o mesmo risco: dividir por essa diferença seria dividir por ruído.
    """
    linhas = []
    for regiao, a, b in PARES:
        ea = evaluate(results / f"{a}.csv", curated)
        eb = evaluate(results / f"{b}.csv", curated)
        premio = ea["retorno_real_aa"] - eb["retorno_real_aa"]
        vol_extra = ea["volatilidade"] - eb["volatilidade"]
        material = abs(vol_extra) * 100 >= VOL_MINIMA_PP
        linhas.append({
            "regiao": regiao,
            "alloc_real_aa": ea["retorno_real_aa"],
            "etf_real_aa": eb["retorno_real_aa"],
            "premio_pp": premio * 100,
            "vol_extra_pp": vol_extra * 100,
            "premio_por_vol_extra": premio / vol_extra if material and vol_extra > 0 else float("nan"),
            "delta_sharpe": ea["sharpe"] - eb["sharpe"],
            "delta_max_dd_pp": (ea["max_drawdown"] - eb["max_drawdown"]) * 100,
            "veredito": _veredito(premio, vol_extra, material),
        })
    return pd.DataFrame(linhas)


def _veredito(premio: float, vol_extra: float, material: bool) -> str:
    """Rótulo em quatro casos, com o empate de risco separado dos demais.

    O empate importa: nos EUA as duas carteiras correram a mesma volatilidade e a
    diferença de retorno é de 0,13 p.p. ao ano. Chamar isso de "mais risco" por
    causa de 0,005 p.p. de volatilidade seria ler ruído como resultado.
    """
    if not material:
        return "mesmo risco: " + ("prêmio" if premio > 0 else "sem prêmio")
    if premio > 0 and vol_extra < 0:
        return "dominância: mais retorno com menos risco"
    if premio > 0:
        return "prêmio com risco extra"
    if vol_extra < 0:
        return "menos retorno, mas menos risco"
    return "menos retorno e mais risco"


def contribuicao_por_ativo(results: Path, strategy: str) -> pd.DataFrame:
    """Peso final de cada ativo dentro da estratégia, do arquivo de posições.

    Responde à pergunta que a regra anti-cherry-picking obriga a fazer: o
    resultado da carteira depende de uma empresa excepcional ou está espalhado?
    """
    pos = pd.read_csv(results / f"{strategy}_positions.csv")
    ultimo = pos[pos.month == pos.month.max()]
    total = ultimo.value.sum()
    out = ultimo[["ticker", "value"]].copy()
    out["peso_final"] = out.value / total
    return out.sort_values("peso_final", ascending=False).reset_index(drop=True)


def sem_o_melhor(results: Path, curated: Path, strategy: str) -> dict:
    """Teste de robustez indicado na metodologia, seção 6.

    Não reescreve a carteira — mede quanto do patrimônio final veio do ativo de
    maior peso. Remover o ativo e refazer o backtest é outra estratégia, e a regra
    anti-cherry-picking proíbe escolhê-la depois de ver o resultado.
    """
    pesos = contribuicao_por_ativo(results, strategy)
    topo = pesos.iloc[0]
    return {
        "estrategia": strategy,
        "ativo_dominante": topo.ticker,
        "peso_final": float(topo.peso_final),
        "peso_dos_demais": float(1 - topo.peso_final),
        "concentracao_hhi": float((pesos.peso_final ** 2).sum()),
    }


def validate(results: Path, curated: Path, engine: Path) -> list[str]:
    """A identidade da decomposição precisa fechar em todos os ativos."""
    df = by_asset(curated, engine)
    problemas = []
    erro = (df.local * df.cambio - df.nominal_brl).abs() / df.nominal_brl
    for _, r in df[erro > 1e-9].iterrows():
        problemas.append(f"{r.ticker}: local × câmbio não reproduz o retorno em BRL")
    if not (df.moeda_exposicao == "BRL").any():
        problemas.append("nenhum ativo em BRL — o painel não deveria ficar só com estrangeiros")
    for _, r in df[df.moeda_exposicao == "BRL"].iterrows():
        if abs(r.cambio - 1.0) > 1e-12:
            problemas.append(f"{r.ticker}: ativo em BRL com efeito cambial diferente de 1")
    return problemas


def resumo_global(results: Path, curated: Path) -> dict:
    """Números de manchete do estudo, para o texto não repetir conta à mão."""
    ea = evaluate(results / "capital_allocators.csv", curated)
    eb = evaluate(results / "passive_etfs.csv", curated)
    return {
        "allocators_reais_por_real": ea["reais_por_real"],
        "etfs_reais_por_real": eb["reais_por_real"],
        "premio_pp": (ea["retorno_real_aa"] - eb["retorno_real_aa"]) * 100,
        "vol_allocators": ea["volatilidade"],
        "vol_etfs": eb["volatilidade"],
    }


__all__ = [
    "by_asset",
    "contribuicao_por_ativo",
    "premium",
    "resumo_global",
    "sem_o_melhor",
    "validate",
]