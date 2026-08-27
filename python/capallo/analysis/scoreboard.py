"""Placar comparativo entre estratégias.

A seção 23 do estudo é explícita: vencedor não se declara por patrimônio final.
Duas estratégias com retorno parecido podem oferecer experiências completamente
diferentes, e é isso que as colunas de risco mostram.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from capallo.analysis import metrics as m


def _load_result(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["month"] = pd.PeriodIndex(df.month, freq="M")
    return df.set_index("month")


def _deflator(curated: Path) -> pd.Series:
    """Fator que leva um valor de cada mês para o poder de compra do fim da série."""
    ipca = pd.read_parquet(curated / "ipca.parquet")
    ipca["month"] = ipca.date.dt.to_period("M")
    f = (1 + ipca.set_index("month").value / 100).loc["2006-01":"2025-12"].cumprod()
    return f.iloc[-1] / f


def _cdi_monthly(curated: Path) -> pd.Series:
    cdi = pd.read_parquet(curated / "cdi.parquet")
    cdi["month"] = cdi.date.dt.to_period("M")
    return cdi.groupby("month").value.apply(lambda s: float((1 + s / 100).prod()) - 1)


def evaluate(path: Path, curated: Path) -> dict:
    df = _load_result(path)
    wealth = df.value
    contributions = df.contribution
    deflator = _deflator(curated).reindex(wealth.index)
    rf = _cdi_monthly(curated)

    returns = m.monthly_returns(wealth, contributions)
    # Retorno real: desconta a inflação do mês do retorno nominal.
    ipca_m = (1 / deflator).pct_change().reindex(returns.index)
    real_returns = ((1 + returns) / (1 + ipca_m) - 1).dropna()

    contributed_real = float((contributions * deflator).sum())
    final_value = float(wealth.iloc[-1])

    rec = m.recovery_months(wealth)
    best, worst = m.best_worst_12m(returns)

    return {
        "patrimonio_nominal": final_value,
        "aportado_real": contributed_real,
        "reais_por_real": final_value / contributed_real,
        "retorno_real_aa": m.annualized_return(real_returns),
        "volatilidade": m.volatility(returns),
        "max_drawdown": m.max_drawdown(wealth),
        "recuperacao_meses": rec,
        "sharpe": m.sharpe(returns, rf),
        "sortino": m.sortino(returns, rf),
        "melhor_12m": best,
        "pior_12m": worst,
    }


def win_rate(a: Path, b: Path, years: int) -> float:
    """Fração das janelas de `years` anos em que `a` superou `b`."""
    da, db = _load_result(a), _load_result(b)
    wa = m.rolling_window_returns(m.monthly_returns(da.value, da.contribution), years)
    wb = m.rolling_window_returns(m.monthly_returns(db.value, db.contribution), years)
    common = wa.index.intersection(wb.index)
    if common.empty:
        return float("nan")
    return float((wa.loc[common] > wb.loc[common]).mean())


def build(results_dir: Path, curated: Path, names: dict[str, str]) -> pd.DataFrame:
    rows = {}
    for key, label in names.items():
        path = results_dir / f"{key}.csv"
        if path.exists():
            rows[label] = evaluate(path, curated)
    return pd.DataFrame(rows)
