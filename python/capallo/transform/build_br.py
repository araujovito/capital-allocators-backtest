"""Monta o total return brasileiro e valida o resultado.

Junta preço do COTAHIST, proventos em dinheiro e eventos societários da B3, os
eventos inferidos por descontinuidade de preço e os proventos em espécie.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from capallo.transform.total_return import build_series

MANUAL = Path("data/manual")


def _load_manual(name: str) -> pd.DataFrame:
    path = MANUAL / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, comment="#")


def build(out_dir: Path) -> pd.DataFrame:
    prices = pd.read_parquet(out_dir / "b3_prices.parquet")
    cash = pd.read_parquet(out_dir / "b3_cash_dividends.parquet")
    stock = pd.read_parquet(out_dir / "b3_stock_events.parquet")

    # Eventos ausentes do cadastro da B3, inferidos por salto de preço.
    extra = _load_manual("b3_missing_events.csv")
    if not extra.empty:
        stock = pd.concat(
            [
                stock,
                pd.DataFrame(
                    {
                        "ticker": extra.ticker,
                        "ex_date": pd.to_datetime(extra.ex_date) - pd.Timedelta(days=1),
                        "kind": extra.kind,
                        # o CSV traz razão (2.0); o campo da B3 é percentual
                        "factor_pct": (extra.factor - 1) * 100,
                        "asset": "",
                    }
                ),
            ],
            ignore_index=True,
        )

    in_kind = _load_manual("b3_in_kind.csv")

    frames = [
        build_series(t, prices, cash, stock, in_kind)
        for t in sorted(prices.ticker.unique())
    ]
    df = pd.concat(frames, ignore_index=True)
    df.to_parquet(out_dir / "br_total_return.parquet", index=False)
    return df


def validate(out_dir: Path, threshold: float = 0.25) -> list[str]:
    """O índice de total return não pode ter descontinuidade artificial.

    Se sobrar salto depois de aplicados todos os eventos, algum evento está
    faltando, com fator errado, ou com data-ex trocada. É a checagem que fecha o
    ciclo: os mesmos saltos que denunciaram dado ausente têm de sumir agora.
    """
    df = pd.read_parquet(out_dir / "br_total_return.parquet")
    verified = _load_manual("verified_market_moves.csv")
    allow = set()
    if not verified.empty:
        allow = {(r.ticker, pd.Timestamp(r.date)) for _, r in verified.iterrows()}

    problems = []
    for ticker, g in df.groupby("ticker"):
        g = g.sort_values("date").reset_index(drop=True)
        ret = g.tr_index.pct_change()
        for i in g.index[ret.abs() > threshold]:
            if (ticker, g.date[i]) in allow:
                continue
            problems.append(
                f"{ticker}: salto residual de {ret[i]*100:+.1f}% em {g.date[i].date()} "
                f"no índice de total return"
            )
        if (g.units <= 0).any() or g.tr_index.isna().any():
            problems.append(f"{ticker}: unidades ou índice inválidos")
    return problems
