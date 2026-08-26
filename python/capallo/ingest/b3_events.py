"""Eventos societários da B3.

Fonte: o proxy oficial que alimenta o site de companhias listadas da B3. Público,
gratuito, sem chave. O payload vai em base64 na própria URL.

Dois endpoints, com contratos diferentes:

- ``GetListedCashDividends`` — proventos em dinheiro, **paginado e com histórico
  completo** (Itaúsa devolve 504 registros desde 1996). Aceita ``tradingName``.
- ``GetListedSupplementCompany`` — traz ``stockDividends`` (bonificação,
  desdobramento, grupamento) e ``subscriptions``. Aceita ``issuingCompany``, não
  é paginado.

⚠️ O ``factor`` dos eventos em ações vem em **percentual**, não em razão: um
desdobramento 1:2 aparece como ``factor = 100``.
"""

from __future__ import annotations

import base64
import json

import pandas as pd
import requests

BASE = "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}

#: Ticker do estudo → (tradingName, issuingCompany) na B3.
COMPANIES: dict[str, tuple[str, str]] = {
    "ITSA4": ("ITAUSA", "ITSA"),
    "BRAP4": ("BRADESPAR", "BRAP"),
}


def _encode(payload: dict) -> str:
    return base64.b64encode(json.dumps(payload).encode()).decode()


def _get(endpoint: str, payload: dict):
    r = requests.get(f"{BASE}/{endpoint}/{_encode(payload)}", headers=HEADERS, timeout=60)
    r.raise_for_status()
    if not r.content:
        return None
    return r.json()


def _br_number(value: str | None) -> float | None:
    """Converte número em formato brasileiro ('0,13800000000')."""
    if value in (None, "", "-"):
        return None
    return float(str(value).replace(".", "").replace(",", "."))


def fetch_cash_dividends(trading_name: str) -> pd.DataFrame:
    """Proventos em dinheiro, todas as páginas."""
    rows, page = [], 1
    while True:
        payload = {
            "language": "pt-br",
            "pageNumber": page,
            "pageSize": 120,
            "tradingName": trading_name,
        }
        data = _get("GetListedCashDividends", payload) or {}
        rows += data.get("results", [])
        info = data.get("page", {})
        if page >= info.get("totalPages", 1):
            break
        page += 1

    if not rows:
        return pd.DataFrame(columns=["ex_date", "payment_date", "kind", "value", "stock_type"])

    df = pd.DataFrame(rows)
    return pd.DataFrame(
        {
            "ex_date": pd.to_datetime(df["lastDatePriorEx"], format="%d/%m/%Y", errors="coerce"),
            "payment_date": pd.to_datetime(df.get("paymentDate"), format="%d/%m/%Y", errors="coerce"),
            "kind": df["corporateAction"].str.strip(),
            "value": df["valueCash"].map(_br_number),
            "stock_type": df["typeStock"].str.strip(),
        }
    ).dropna(subset=["ex_date"]).sort_values("ex_date").reset_index(drop=True)


def fetch_stock_events(issuing_company: str) -> pd.DataFrame:
    """Bonificações, desdobramentos e grupamentos."""
    data = _get("GetListedSupplementCompany", {"issuingCompany": issuing_company,
                                               "language": "pt-br"})
    if not data:
        return pd.DataFrame(columns=["ex_date", "kind", "factor_pct", "asset"])
    entry = data[0] if isinstance(data, list) else data
    rows = entry.get("stockDividends") or []
    if not rows:
        return pd.DataFrame(columns=["ex_date", "kind", "factor_pct", "asset"])

    df = pd.DataFrame(rows)
    return pd.DataFrame(
        {
            "ex_date": pd.to_datetime(df["lastDatePrior"], format="%d/%m/%Y", errors="coerce"),
            "kind": df["label"].str.strip(),
            "factor_pct": df["factor"].map(_br_number),
            "asset": df.get("assetIssued", pd.Series([""] * len(df))).fillna(""),
        }
    ).dropna(subset=["ex_date"]).drop_duplicates().sort_values("ex_date").reset_index(drop=True)


def build(out_dir) -> dict[str, int]:
    from pathlib import Path

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cash, stock, counts = [], [], {}
    for ticker, (trading_name, issuing) in COMPANIES.items():
        d = fetch_cash_dividends(trading_name)
        d.insert(0, "ticker", ticker)
        cash.append(d)
        e = fetch_stock_events(issuing)
        e.insert(0, "ticker", ticker)
        stock.append(e)
        counts[f"{ticker} dinheiro"] = len(d)
        counts[f"{ticker} acoes"] = len(e)
    pd.concat(cash, ignore_index=True).to_parquet(out_dir / "b3_cash_dividends.parquet", index=False)
    pd.concat(stock, ignore_index=True).to_parquet(out_dir / "b3_stock_events.parquet", index=False)
    return counts


def reconcile(out_dir) -> list[str]:
    """Confronta preço bruto + proventos com o CDI do mesmo período.

    Não prova que os dados estão certos — mas expõe quando estão implausíveis.
    Um allocator que rende menos que o CDI por vinte anos é possível; o que não é
    plausível é uma empresa conhecida por bonificar anualmente registrar um único
    evento em ações em vinte anos.
    """
    from pathlib import Path

    out_dir = Path(out_dir)
    warnings: list[str] = []
    w0, w1 = pd.Timestamp("2006-01-01"), pd.Timestamp("2025-12-31")

    prices = pd.read_parquet(out_dir / "b3_prices.parquet")
    cash = pd.read_parquet(out_dir / "b3_cash_dividends.parquet")
    stock = pd.read_parquet(out_dir / "b3_stock_events.parquet")

    for ticker in COMPANIES:
        g = prices[prices.ticker == ticker].sort_values("date")
        d = cash[(cash.ticker == ticker) & cash.stock_type.str.contains("PN", na=False)]
        d = d[(d.ex_date >= w0) & (d.ex_date <= w1)]
        e = stock[(stock.ticker == ticker) & (stock.ex_date >= w0) & (stock.ex_date <= w1)]

        naive = (g.close.iloc[-1] + d.value.sum()) / g.close.iloc[0] - 1
        anual = (1 + naive) ** (1 / 20) - 1
        if anual < 0.1020:  # CDI nominal do período
            warnings.append(
                f"{ticker}: retorno ingênuo {anual*100:.2f}% a.a. fica abaixo do CDI "
                f"(10,20% a.a.) — eventos em ações podem estar incompletos"
            )
        if len(e) < 5:
            warnings.append(
                f"{ticker}: apenas {len(e)} eventos em ações em 20 anos — validar contra o RI"
            )
    return warnings
