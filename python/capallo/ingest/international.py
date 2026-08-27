"""Materializa as séries internacionais obtidas em fontes locais.

Japão via Kabutan (株探), Suécia via Avanza e Bélgica via onvista. Todas gratuitas,
sem chave, na língua e na praça de origem.

A belga é a que melhor ilustra o método: a Euronext cifra o próprio histórico, mas
um portal **alemão** indexa o papel pelo ISIN e expõe a série da bolsa de
**Bruxelas** — a fonte é alemã, o dado é belga, em EUR.

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
from capallo.ingest.onvista import INSTRUMENTS, fetch_daily as fetch_be

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

    be = []
    for ticker, (_isin, entity, notation) in INSTRUMENTS.items():
        # A onvista devolve série diária; o estudo usa o último pregão do mês.
        df = fetch_be(entity, notation)
        df["ticker"] = ticker
        be.append(df)
        counts[ticker] = df.set_index("date").close.resample("ME").last().dropna().shape[0]
    pd.concat(be, ignore_index=True).to_parquet(out_dir / "be_prices.parquet", index=False)

    return counts


def validate(out_dir: Path) -> list[str]:
    problems: list[str] = []
    for name in ("jp_prices.parquet", "se_prices.parquet", "be_prices.parquet"):
        path = out_dir / name
        if not path.exists():
            problems.append(f"{path} não existe")
            continue
        df = pd.read_parquet(path)
        for ticker, g in df.groupby("ticker"):
            # A série belga é diária; compara-se no fecho mensal, como as demais.
            if len(g) > 400:
                g = (
                    g.set_index("date").close.resample("ME").last().dropna()
                    .rename("close").reset_index().assign(ticker=ticker)
                )
            w = _in_window(g)
            if len(w) != EXPECTED_MONTHS:
                problems.append(f"{ticker}: {len(w)} meses, esperado {EXPECTED_MONTHS}")
            if w.close.isna().any() or (w.close <= 0).any():
                problems.append(f"{ticker}: preço nulo ou não positivo")
            if w.date.dt.to_period("M").duplicated().any():
                problems.append(f"{ticker}: mês duplicado")
    return problems
