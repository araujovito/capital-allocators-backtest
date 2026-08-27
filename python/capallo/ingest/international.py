"""Materializa as séries internacionais obtidas em fontes locais.

Japão via Kabutan (株探) e Suécia via Avanza. Ambas gratuitas, sem chave, na
língua e na praça de origem.

⚠️ **Preço, não total return.** As duas fontes entregam cotação ajustada por
desdobramento, mas não por dividendo. A série de proventos ainda falta, e sem ela
estes ativos não podem entrar no backtest: compará-los com ativos que já têm total
return subestimaria seu retorno de forma sistemática.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from capallo.ingest.avanza import ORDERBOOKS, fetch_monthly as fetch_se
from capallo.ingest.kabutan import TOKYO_CODES, fetch_monthly as fetch_jp

EXPECTED_MONTHS = 240
WINDOW = ("2006-01", "2025-12")


def _in_window(df: pd.DataFrame) -> pd.DataFrame:
    m = df.date.dt.to_period("M")
    return df[(m >= WINDOW[0]) & (m <= WINDOW[1])]


def build(out_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}

    jp = []
    for ticker, code in TOKYO_CODES.items():
        df = fetch_jp(code)
        df["ticker"] = ticker
        jp.append(df)
        counts[ticker] = len(_in_window(df))
    pd.concat(jp, ignore_index=True).to_parquet(out_dir / "jp_prices.parquet", index=False)

    se = []
    for ticker, oid in ORDERBOOKS.items():
        df = fetch_se(oid)
        df["ticker"] = ticker
        se.append(df)
        counts[ticker] = len(_in_window(df))
    pd.concat(se, ignore_index=True).to_parquet(out_dir / "se_prices.parquet", index=False)

    return counts


def validate(out_dir: Path) -> list[str]:
    problems: list[str] = []
    for name in ("jp_prices.parquet", "se_prices.parquet"):
        path = out_dir / name
        if not path.exists():
            problems.append(f"{path} não existe")
            continue
        df = pd.read_parquet(path)
        for ticker, g in df.groupby("ticker"):
            w = _in_window(g)
            if len(w) != EXPECTED_MONTHS:
                problems.append(f"{ticker}: {len(w)} meses, esperado {EXPECTED_MONTHS}")
            if w.close.isna().any() or (w.close <= 0).any():
                problems.append(f"{ticker}: preço nulo ou não positivo")
            if w.date.dt.to_period("M").duplicated().any():
                problems.append(f"{ticker}: mês duplicado")
    return problems
