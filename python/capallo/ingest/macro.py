"""Materializa a camada macro em Parquet.

CDI, IPCA e PTAX das quatro moedas. Tudo do Banco Central: fonte oficial, gratuita,
sem chave e sem anti-bot.

A janela começa em 2005-12 de propósito. O primeiro aporte é em jan/2006 e o
reajuste do aporte usa o IPCA do período anterior — sem dez/2005 o primeiro
reajuste ficaria sem base.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from capallo.ingest.bacen import PTAX_CURRENCIES, fetch_ptax, fetch_sgs

#: Um mês antes do início do estudo, para dar base ao primeiro reajuste.
DEFAULT_START = date(2005, 12, 1)
DEFAULT_END = date(2025, 12, 31)


def build(out_dir: Path, start: date = DEFAULT_START, end: date = DEFAULT_END) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}

    for name in ("CDI", "IPCA"):
        df = fetch_sgs(name, start, end)
        df.to_parquet(out_dir / f"{name.lower()}.parquet", index=False)
        counts[name] = len(df)

    fx = []
    for cur in PTAX_CURRENCIES:
        df = fetch_ptax(cur, start, end)
        df.insert(1, "currency", cur)
        counts[f"{cur}BRL"] = len(df)
        fx.append(df)
    pd.concat(fx, ignore_index=True).to_parquet(out_dir / "ptax.parquet", index=False)

    return counts


def validate(out_dir: Path) -> list[str]:
    """Checagens que precisam passar antes de qualquer backtest. Retorna problemas."""
    problems: list[str] = []

    ipca = pd.read_parquet(out_dir / "ipca.parquet")
    janela = ipca[(ipca.date >= "2006-01-01") & (ipca.date <= "2025-12-31")]
    if len(janela) != 240:
        problems.append(f"IPCA: {len(janela)} meses na janela, esperado 240")

    cdi = pd.read_parquet(out_dir / "cdi.parquet")
    if cdi.value.isna().any():
        problems.append("CDI: contém nulos")
    if (cdi.value < 0).any():
        problems.append("CDI: contém taxa negativa")

    ptax = pd.read_parquet(out_dir / "ptax.parquet")
    for cur, g in ptax.groupby("currency"):
        if (g.ask < g.bid).any():
            problems.append(f"PTAX {cur}: venda abaixo da compra")
        if g.date.duplicated().any():
            problems.append(f"PTAX {cur}: datas duplicadas")
    faltando = set(PTAX_CURRENCIES) - set(ptax.currency.unique())
    if faltando:
        problems.append(f"PTAX: moedas ausentes {sorted(faltando)}")

    return problems
