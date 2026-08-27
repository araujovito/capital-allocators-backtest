"""Coletor Twelve Data (plano gratuito).

O plano Basic não expõe `/dividends` nem `/splits` — ambos são pagos. Mas o
`time_series` aceita `adjust=all`, que devolve o fechamento já ajustado por
proventos e desdobramentos. É por aí que se chega ao total return sem custo.

Verificado: IVV em jan/2006 fecha a 127,75 bruto e 87,35 ajustado. A razão de
0,684 corresponde a ~20 anos de dividendos do S&P 500 reinvestidos, o que confirma
que o ajuste é real.

Cobertura do plano gratuito: ações e ETFs listados nos EUA. Bolsas estrangeiras
respondem 404 com mensagem explícita de upgrade.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import pandas as pd
import requests

BASE = "https://api.twelvedata.com"

#: Plano gratuito: 8 requisições por minuto.
MIN_INTERVAL_S = 8.0


class TwelveDataError(RuntimeError):
    pass


@dataclass
class Quota:
    """Espaça as chamadas para respeitar o limite do plano gratuito."""

    last: float = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self.last
        if self.last and elapsed < MIN_INTERVAL_S:
            time.sleep(MIN_INTERVAL_S - elapsed)
        self.last = time.monotonic()


def api_key() -> str:
    key = os.environ.get("TWELVEDATA_API_KEY", "").strip()
    if not key:
        raise TwelveDataError(
            "TWELVEDATA_API_KEY não definida. Copie .env.example para .env e preencha."
        )
    return key


def fetch_monthly(
    symbol: str,
    start: str = "2006-01-01",
    end: str = "2025-12-31",
    quota: Quota | None = None,
    adjust: str = "all",
) -> pd.DataFrame:
    """Série mensal, ajustada conforme `adjust`.

    Mensal, não diária, é decisão metodológica: os aportes do estudo são mensais e
    o histórico mensal de 20 anos cabe em uma chamada, enquanto o diário estoura a
    cota gratuita.

    `adjust="all"` traz o fechamento ajustado por proventos e desdobramentos — o
    total return **bruto**. `adjust="splits"` traz o mesmo papel ajustado só por
    desdobramento, ou seja, **preço puro**. A diferença entre as duas séries é o
    provento reinvestido, e é dela que sai a retenção na fonte: sem a segunda
    chamada não há como tributar um dividendo que a fonte já embutiu no preço.
    """
    (quota or Quota()).wait()
    params = {
        "symbol": symbol,
        "interval": "1month",
        "start_date": start,
        "end_date": end,
        "adjust": adjust,
        "outputsize": 5000,
        "apikey": api_key(),
    }
    r = requests.get(f"{BASE}/time_series", params=params, timeout=60)
    payload = r.json()
    if payload.get("status") != "ok" or not payload.get("values"):
        raise TwelveDataError(f"{symbol}: {payload.get('code')} {payload.get('message')}")

    df = pd.DataFrame(payload["values"])
    coluna = "close_adj" if adjust == "all" else "close_px"
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(df["datetime"]),
            coluna: pd.to_numeric(df["close"]),
        }
    ).sort_values("date").reset_index(drop=True)
    out.insert(1, "symbol", symbol)
    out.insert(2, "currency", payload["meta"].get("currency"))
    return out
