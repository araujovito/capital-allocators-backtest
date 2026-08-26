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


def detect_unrecorded_events(out_dir, threshold: float = 0.25) -> pd.DataFrame:
    """Procura eventos societários ausentes olhando para saltos na série de preço.

    Desdobramento, grupamento e bonificação deixam uma descontinuidade artificial
    no preço bruto. Se a série salta e a B3 não registrou evento naquela data, ou
    o evento faltou no cadastro, ou o movimento foi de mercado — e a distinção se
    faz pelo sinal e pela magnitude.

    Este teste substituiu uma heurística anterior que comparava o retorno do ativo
    com o CDI e acusava "dado faltando" quando ficava abaixo. Ela produzia falso
    positivo: ação brasileira render menos que o CDI entre 2006 e 2025 é fato
    corriqueiro, não sintoma de dado ausente. Saltos de preço são evidência
    direta; desempenho fraco não é evidência de nada.
    """
    from pathlib import Path

    out_dir = Path(out_dir)
    prices = pd.read_parquet(out_dir / "b3_prices.parquet")
    events = pd.read_parquet(out_dir / "b3_stock_events.parquet")

    found = []
    for ticker, g in prices.groupby("ticker"):
        g = g.sort_values("date").reset_index(drop=True)
        ret = g.close.pct_change()
        known = set(events[events.ticker == ticker].ex_date.dt.date)
        for i in g.index[ret.abs() > threshold]:
            day = g.date[i].date()
            registered = any(abs((day - d).days) <= 3 for d in known)
            found.append(
                {
                    "ticker": ticker,
                    "date": g.date[i],
                    "return": float(ret[i]),
                    "price_before": float(g.close[i - 1]),
                    "price_after": float(g.close[i]),
                    "implied_factor": float(g.close[i - 1] / g.close[i]),
                    "registered": registered,
                }
            )
    return pd.DataFrame(found)


def reconcile(out_dir) -> list[str]:
    """Avisos sobre eventos societários que a B3 não registrou.

    Só reporta queda: desdobramento e grupamento derrubam ou multiplicam o preço
    de forma característica, enquanto altas de 25% em um pregão são movimento de
    mercado corriqueiro em crise — o ITSA4 tem uma em 13/10/2008, no rali global
    seguinte à quebra do Lehman, que não é evento societário nenhum.
    """
    suspects = detect_unrecorded_events(out_dir)
    if suspects.empty:
        return []
    alerts = []
    for _, r in suspects[(~suspects.registered) & (suspects["return"] < 0)].iterrows():
        alerts.append(
            f"{r.ticker}: queda de {r['return']*100:.1f}% em {r.date.date()} "
            f"({r.price_before:.2f} -> {r.price_after:.2f}, fator implícito "
            f"{r.implied_factor:.2f}) sem evento registrado na B3"
        )
    return alerts
