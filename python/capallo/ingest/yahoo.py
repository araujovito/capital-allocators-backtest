"""Coletor Yahoo Finance.

Usado no spike de viabilidade. A qualidade das séries pré-2010 fora dos EUA é
irregular e os eventos societários não são rastreáveis individualmente — por isso
o probe reporta evidências, não conclusões.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

import requests

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

# Sem User-Agent de navegador o endpoint responde 429.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}


@dataclass
class Probe:
    """O que o Yahoo realmente entrega para um símbolo."""

    symbol: str
    ok: bool
    error: str | None = None
    currency: str | None = None
    exchange: str | None = None
    first_date: date | None = None
    last_date: date | None = None
    n_bars: int = 0
    n_null_close: int = 0
    #: Barras faltantes vs. dias úteis esperados, por ano.
    coverage_by_year: dict[int, int] = field(default_factory=dict)
    n_dividends: int = 0
    first_dividend: date | None = None
    n_splits: int = 0
    has_adjclose: bool = False


def _to_date(ts: int) -> date:
    return datetime.fromtimestamp(ts, tz=timezone.utc).date()


def probe(symbol: str, start: str = "1995-01-01", session: requests.Session | None = None) -> Probe:
    """Interroga um símbolo e resume a evidência disponível."""
    sess = session or requests.Session()
    period1 = int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp())
    params = {
        "period1": period1,
        "period2": int(time.time()),
        "interval": "1d",
        "events": "div|split",
        "includeAdjustedClose": "true",
    }
    try:
        r = sess.get(CHART_URL.format(symbol=symbol), params=params, headers=HEADERS, timeout=30)
    except requests.RequestException as exc:
        return Probe(symbol, ok=False, error=f"rede: {exc}")

    if r.status_code != 200:
        return Probe(symbol, ok=False, error=f"HTTP {r.status_code}")

    payload = r.json().get("chart") or {}
    if payload.get("error"):
        return Probe(symbol, ok=False, error=str(payload["error"].get("description")))
    results = payload.get("result") or []
    if not results:
        return Probe(symbol, ok=False, error="resposta sem result")

    res = results[0]
    meta = res.get("meta", {})
    stamps = res.get("timestamp") or []
    if not stamps:
        return Probe(symbol, ok=False, error="sem barras no período")

    quote = (res.get("indicators", {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    adj = res.get("indicators", {}).get("adjclose") or []
    events = res.get("events", {}) or {}
    divs = events.get("dividends", {}) or {}
    splits = events.get("splits", {}) or {}

    dates = [_to_date(t) for t in stamps]
    by_year: dict[int, int] = {}
    for d in dates:
        by_year[d.year] = by_year.get(d.year, 0) + 1

    div_dates = sorted(_to_date(int(v["date"])) for v in divs.values() if "date" in v)

    return Probe(
        symbol=symbol,
        ok=True,
        currency=meta.get("currency"),
        exchange=meta.get("fullExchangeName") or meta.get("exchangeName"),
        first_date=dates[0],
        last_date=dates[-1],
        n_bars=len(dates),
        n_null_close=sum(1 for c in closes if c is None),
        coverage_by_year=by_year,
        n_dividends=len(divs),
        first_dividend=div_dates[0] if div_dates else None,
        n_splits=len(splits),
        has_adjclose=bool(adj and adj[0].get("adjclose")),
    )
