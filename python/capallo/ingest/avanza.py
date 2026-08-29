"""Coletor Avanza — cotações da bolsa de Estocolmo.

Fonte sueca, gratuita e sem chave, usada para Investor AB (INVE-B). Encontrada
pelo mesmo método que resolveu o Japão: procurar o dado na praça de origem em vez
de num agregador internacional.

A API de gráfico da corretora aceita `timePeriod=infinity`, que devolve série
mensal desde 1984, e também um intervalo explícito via `from`/`to`.

⚠️ As cotações vêm em **SEK**, ajustadas por desdobramento e **não** por dividendo:
são preço puro. Este arquivo já afirmou o contrário, com um teste de cinco datas-ex
que estava desalinhado em um dia e mediu o pregão *seguinte* à queda. A refutação,
com a data-ex verdadeira e 27 eventos, está em `investor_ir.py` — que é de onde
vêm os proventos de INVE-B.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import requests

BASE = "https://www.avanza.se/_api"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}

#: Ticker do estudo → orderbookId na Avanza. Conferido via /market-guide/stock,
#: que devolve o ISIN: INVE-B = SE0015811963.
ORDERBOOKS = {"INVE-B": "5247"}


def fetch_monthly(
    orderbook_id: str, start: str = "2005-06-01", end: str = "2026-06-30"
) -> pd.DataFrame:
    """Série mensal. A janela pedida é folgada de propósito.

    O timestamp de cada barra é o **último pregão do mês**, então pedir a partir
    de 2006-01-01 devolve como primeira barra 2005-12-31. Buscar folgado e filtrar
    por período depois evita perder o primeiro e o último mês do estudo.
    """
    url = f"{BASE}/price-chart/stock/{orderbook_id}"
    params = {"from": start, "to": end, "resolution": "month"}
    r = requests.get(url, params=params, headers=HEADERS, timeout=60)
    r.raise_for_status()
    ohlc = r.json().get("ohlc") or []
    if not ohlc:
        return pd.DataFrame(columns=["date", "close"])

    return pd.DataFrame(
        {
            "date": [
                pd.Timestamp(dt.datetime.fromtimestamp(p["timestamp"] / 1000, dt.UTC).date())
                for p in ohlc
            ],
            "close": [p["close"] for p in ohlc],
        }
    ).sort_values("date").reset_index(drop=True)


def verify_isin(orderbook_id: str) -> str | None:
    """Confirma que o orderbookId aponta para o papel esperado."""
    r = requests.get(f"{BASE}/market-guide/stock/{orderbook_id}", headers=HEADERS, timeout=40)
    r.raise_for_status()
    return r.json().get("isin")


def fetch_daily(orderbook_id: str, start: int = 2005, end: int = 2026) -> pd.DataFrame:
    """Série diária, ano a ano.

    A API recusa (400) uma janela diária de vinte anos de uma vez, mas aceita um
    ano por chamada. Só é usada para medir o comportamento do preço na data-ex —
    o painel do estudo é mensal.
    """
    partes = []
    for ano in range(start, end + 1):
        r = requests.get(
            f"{BASE}/price-chart/stock/{orderbook_id}",
            params={"from": f"{ano}-01-01", "to": f"{ano}-12-31", "resolution": "day"},
            headers=HEADERS,
            timeout=60,
        )
        if not r.ok:
            continue
        ohlc = r.json().get("ohlc") or []
        partes.append(pd.DataFrame({
            "date": [
                pd.Timestamp(dt.datetime.fromtimestamp(p["timestamp"] / 1000, dt.UTC).date())
                for p in ohlc
            ],
            "close": [p["close"] for p in ohlc],
        }))
    if not partes:
        return pd.DataFrame(columns=["date", "close"])
    return (pd.concat(partes).drop_duplicates("date")
            .sort_values("date").reset_index(drop=True))
