"""Materializa as séries de renda variável obteníveis no plano gratuito.

Cobre os ativos listados nos EUA: os dois allocators americanos e os três ETFs
(sim, IEV e EWJ replicam Europa e Japão, mas são listados em Nova York — por isso
entram aqui).

O que **não** está aqui: INVE-B, GBLB, 8058 e 8031, bloqueados na bolsa de origem.
Ver `docs/spike-dados.md`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from capallo.ingest.twelvedata import Quota, fetch_monthly

#: Ticker do estudo → símbolo na Twelve Data.
US_LISTED: dict[str, str] = {
    "BRK-B": "BRK.B",
    "MKL": "MKL",
    "IVV": "IVV",
    "IEV": "IEV",
    "EWJ": "EWJ",
}

EXPECTED_MONTHS = 240


def build(out_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    quota = Quota()
    frames, counts = [], {}
    for ticker, symbol in US_LISTED.items():
        # Duas séries do mesmo papel: total return bruto e preço puro. A diferença
        # é o provento reinvestido, e sem ela a retenção na fonte americana não
        # tem sobre o que incidir — ver `transform.net_of_tax`.
        bruto = fetch_monthly(symbol, quota=quota, adjust="all")
        preco = fetch_monthly(symbol, quota=quota, adjust="splits")
        df = bruto.merge(preco[["date", "close_px"]], on="date", how="inner")
        df.insert(0, "ticker", ticker)
        frames.append(df)
        counts[ticker] = len(df)
    pd.concat(frames, ignore_index=True).to_parquet(out_dir / "equities_us.parquet", index=False)
    return counts


def validate(out_dir: Path) -> list[str]:
    path = out_dir / "equities_us.parquet"
    if not path.exists():
        return [f"{path} não existe"]

    df = pd.read_parquet(path)
    problems: list[str] = []
    for ticker in US_LISTED:
        g = df[df.ticker == ticker]
        if len(g) != EXPECTED_MONTHS:
            problems.append(f"{ticker}: {len(g)} meses, esperado {EXPECTED_MONTHS}")
        if g.close_adj.isna().any():
            problems.append(f"{ticker}: contém nulos")
        if (g.close_adj <= 0).any():
            problems.append(f"{ticker}: preço não positivo")
        if "close_px" not in g.columns:
            problems.append(f"{ticker}: falta a série de preço puro (adjust=splits)")
        elif (g.close_px <= 0).any():
            problems.append(f"{ticker}: preço puro não positivo")
        if g.date.duplicated().any():
            problems.append(f"{ticker}: datas duplicadas")
    return problems
