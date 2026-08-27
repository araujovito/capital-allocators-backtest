"""Total return americano **líquido** de retenção na fonte.

Correção de uma assimetria que passou despercebida até a análise regional ficar
pronta. A seção 4 da metodologia congela 30% de retenção para o investidor
brasileiro em papel americano, e avisa por quê: *"ignorar retenção favoreceria
artificialmente allocators estrangeiros de alto payout — exatamente o viés que a
metodologia quer evitar"*. Brasil, Bélgica e Japão aplicavam a alíquota. Os
Estados Unidos, não: a série vinha do fechamento ajustado da Twelve Data, que
reinveste o dividendo **bruto**.

O viés não era simétrico entre as pernas, e por um motivo que só aparece olhando
os dados: **Berkshire e Markel não pagam dividendo**. O ajuste bruto e o preço
puro coincidem casa a casa nos dois — 1,000x de provento acumulado em vinte anos.
Quem se beneficiava da isenção indevida era o **lado passivo**: IVV rendeu 1,89%
ao ano de dividendo, IEV 2,88% e EWJ 1,69%, todos sem imposto.

## Como o imposto incide sobre um preço já ajustado

A Twelve Data não expõe `/dividends` no plano gratuito, mas expõe o mesmo papel
com dois ajustes: `adjust=all` (total return bruto) e `adjust=splits` (preço puro,
já corrigido por desdobramento). O provento do mês é o que sobra entre os dois:

    d = (1 + retorno ajustado) / (1 + retorno de preço) − 1
    retorno líquido = (1 + retorno de preço) × (1 + d × (1 − alíquota)) − 1

A identidade é exata quando a fonte ajusta pelo método padrão de razão de
proventos. Com alíquota zero ela reproduz o total return bruto, e é isso que o
teste verifica — a correção não pode mudar nada onde não há imposto.

⚠️ A conferência que sustenta o método é Berkshire e Markel: `d` tem de dar zero
todo mês nos dois. Se der outra coisa, a decomposição está lendo ruído de
arredondamento como dividendo.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from capallo.universe import BY_TICKER

#: Tolerância para `d` negativo. O provento de um mês não pode ser negativo; o que
#: aparece abaixo de zero é arredondamento da fonte, na quinta casa decimal.
TOL_NEGATIVO = 1e-4

#: Tolerância no nível acumulado. `d` é limitado a zero, o que impede o líquido de
#: herdar o arredondamento negativo do bruto e o deixa uma fração acima dele em
#: alguns meses. Medido nas séries reais: 104 meses do EWJ somam −1e-5 de provento
#: negativo. É esse resíduo que a folga cobre — não erro de método.
TOL_NIVEL = 1e-4


def dividend_yield(g: pd.DataFrame) -> pd.Series:
    """Componente de provento de cada mês, entre o ajustado e o preço puro."""
    g = g.sort_values("date")
    r_adj = g.close_adj.pct_change()
    r_px = g.close_px.pct_change()
    return ((1 + r_adj) / (1 + r_px) - 1).fillna(0.0)


def net_series(g: pd.DataFrame, withholding: float) -> pd.Series:
    """Índice de total return líquido, na mesma escala do bruto."""
    g = g.sort_values("date")
    d = dividend_yield(g).clip(lower=0.0)
    r_px = g.close_px.pct_change().fillna(0.0)
    liquido = (1 + r_px) * (1 + d * (1 - withholding)) - 1
    return float(g.close_adj.iloc[0]) * (1 + liquido).cumprod()


def build(curated: Path) -> pd.DataFrame:
    """Adiciona `close_net` a `equities_us.parquet`, sem descartar o bruto.

    O bruto fica: é ele que permite refazer a conta com outra alíquota e medir
    quanto a escolha custa, em vez de afirmar que custa pouco.
    """
    path = curated / "equities_us.parquet"
    df = pd.read_parquet(path)
    partes = []
    for ticker, g in df.groupby("ticker"):
        w = BY_TICKER[ticker].withholding_tax
        g = g.sort_values("date").copy()
        g["close_net"] = net_series(g, w).to_numpy()
        partes.append(g)
    out = pd.concat(partes, ignore_index=True)
    out.to_parquet(path, index=False)
    return out


def validate(curated: Path) -> list[str]:
    df = pd.read_parquet(curated / "equities_us.parquet")
    problemas = []
    if "close_net" not in df.columns:
        return ["equities_us.parquet sem a coluna close_net"]
    for ticker, g in df.groupby("ticker"):
        g = g.sort_values("date")
        d = dividend_yield(g)
        if (d < -TOL_NEGATIVO).any():
            pior = float(d.min())
            problemas.append(f"{ticker}: provento negativo de {pior:.5f} — ajuste da fonte suspeito")
        # Berkshire e Markel não pagam dividendo: o líquido tem de bater com o bruto.
        if BY_TICKER[ticker].withholding_tax > 0 and d.abs().max() < TOL_NEGATIVO:
            razao = float(g.close_net.iloc[-1] / g.close_adj.iloc[-1])
            if abs(razao - 1.0) > 1e-9:
                problemas.append(f"{ticker}: sem dividendo, mas líquido difere do bruto")
        if (g.close_net > g.close_adj * (1 + TOL_NIVEL)).any():
            problemas.append(f"{ticker}: líquido acima do bruto — imposto não pode aumentar retorno")
        # E onde há dividendo tributado, o líquido tem de ficar mesmo abaixo.
        paga = d.max() > TOL_NEGATIVO
        if paga and BY_TICKER[ticker].withholding_tax > 0 and g.close_net.iloc[-1] >= g.close_adj.iloc[-1]:
            problemas.append(f"{ticker}: paga dividendo tributado, mas o líquido não ficou abaixo do bruto")
    return problemas


def custo_da_retencao(curated: Path) -> pd.DataFrame:
    """Quanto a retenção americana tira de cada papel, em vinte anos."""
    df = pd.read_parquet(curated / "equities_us.parquet")
    linhas = []
    for ticker, g in df.groupby("ticker"):
        g = g.sort_values("date")
        bruto = float(g.close_adj.iloc[-1] / g.close_adj.iloc[0])
        liquido = float(g.close_net.iloc[-1] / g.close_net.iloc[0])
        linhas.append({
            "ticker": ticker,
            "aliquota": BY_TICKER[ticker].withholding_tax,
            "yield_bruto_aa": (bruto / float(g.close_px.iloc[-1] / g.close_px.iloc[0])) ** (1 / 20) - 1,
            "bruto": bruto,
            "liquido": liquido,
            "custo_pp_aa": (bruto ** (1 / 20) - liquido ** (1 / 20)) * 100,
        })
    return pd.DataFrame(linhas).sort_values("custo_pp_aa", ascending=False).reset_index(drop=True)
