"""Prepara o dataset que o motor Rust consome.

Fronteira entre as duas linguagens: Python resolve fonte, moeda, calendário e
frequência; o Rust recebe um painel já limpo e homogêneo e só simula.

Decisões materializadas aqui:

- **Frequência mensal.** Os aportes do estudo são mensais. O valor do mês é o do
  último pregão com negociação naquele mês, por ativo.
- **Tudo em BRL.** A unidade econômica do estudo é o real. Ativos em moeda
  estrangeira são convertidos pela PTAX de venda da mesma data — venda porque é a
  ponta que o investidor brasileiro paga ao comprar moeda.
- **Calendários diferentes não são alinhados à força.** Cada ativo usa o próprio
  último pregão do mês. Forçar uma data comum introduziria preço de um dia em que
  o ativo não negociou.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

#: Moeda de exposição de cada ativo já coletado.
CURRENCY = {
    "ITSA4": "BRL", "BRAP4": "BRL", "PIBB11": "BRL",
    "BRK-B": "USD", "MKL": "USD", "IVV": "USD", "IEV": "USD", "EWJ": "USD",
}


def _monthly_last(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Último valor observado de cada mês, por ticker."""
    out = df.copy()
    out["month"] = out.date.dt.to_period("M")
    idx = out.groupby(["ticker", "month"]).date.idxmax()
    out = out.loc[idx, ["ticker", "month", "date", value_col]]
    return out.rename(columns={value_col: "tr_local"}).reset_index(drop=True)


def build(curated: Path) -> pd.DataFrame:
    frames = []

    br = pd.read_parquet(curated / "br_total_return.parquet")
    frames.append(_monthly_last(br, "tr_index"))

    us = pd.read_parquet(curated / "equities_us.parquet")
    us_m = _monthly_last(us, "close_adj")
    frames.append(us_m)

    panel = pd.concat(frames, ignore_index=True)
    panel["currency"] = panel.ticker.map(CURRENCY)

    # Conversão para BRL pela PTAX de venda da mesma data.
    ptax = pd.read_parquet(curated / "ptax.parquet")
    usd = ptax[ptax.currency == "USD"][["date", "ask"]].sort_values("date")
    panel = panel.sort_values("date")
    panel = pd.merge_asof(panel, usd, on="date", direction="backward")

    panel["fx"] = panel.ask.where(panel.currency != "BRL", 1.0)
    panel["tr_brl"] = panel.tr_local * panel.fx

    missing = panel[panel.tr_brl.isna()]
    if len(missing):
        raise ValueError(f"{len(missing)} linhas sem conversão de câmbio")

    return panel[["month", "date", "ticker", "currency", "tr_local", "fx", "tr_brl"]]


def build_macro(curated: Path) -> pd.DataFrame:
    """Painel macro mensal: fator do CDI no mês e variação do IPCA."""
    cdi = pd.read_parquet(curated / "cdi.parquet")
    cdi["month"] = cdi.date.dt.to_period("M")
    # CDI é taxa diária em %; o fator do mês é o produto dos dias úteis.
    cdi_m = cdi.groupby("month").value.apply(lambda s: float((1 + s / 100).prod()))

    ipca = pd.read_parquet(curated / "ipca.parquet")
    ipca["month"] = ipca.date.dt.to_period("M")
    ipca_m = ipca.groupby("month").value.last() / 100 + 1

    macro = pd.DataFrame({"cdi_factor": cdi_m, "ipca_factor": ipca_m}).dropna()
    return macro.reset_index()


def export(curated: Path, out_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    panel = build(curated)
    macro = build_macro(curated)

    # O motor lê CSV: formato estável, inspecionável e sem dependência de schema
    # binário entre as duas linguagens. O Parquet segue como armazenamento curado.
    p = panel.assign(month=panel.month.astype(str)).drop(columns=["date"])
    p.to_csv(out_dir / "panel.csv", index=False, float_format="%.10f")
    macro.assign(month=macro.month.astype(str)).to_csv(
        out_dir / "macro.csv", index=False, float_format="%.10f"
    )
    return {"panel": len(p), "macro": len(macro), "tickers": panel.ticker.nunique()}
