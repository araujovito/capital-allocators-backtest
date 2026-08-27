"""Coletor onvista — cotações via portal alemão.

Encontrado ao procurar o GBL em fontes de língua alemã, depois de a Euronext
cifrar o payload e todas as fontes belgas e francesas falharem.

O detalhe que resolveu: o portal indexa o papel pelo ISIN e expõe **todas as
praças em que ele negocia**, inclusive a bolsa de origem. Para o GBL isso
significa Bruxelas (`idNotation` 29217), em EUR — não a listagem secundária
alemã. A fonte é alemã; o dado é belga.

A API só devolve uma janela de cada vez: `range=Y1` combinado com `startDate`
entrega um ano de pregões. Vinte requisições cobrem o estudo.
"""

from __future__ import annotations

import datetime as dt
import time

import pandas as pd
import requests

SEARCH = "https://api.onvista.de/api/v1/instruments/search"
SNAPSHOT = "https://api.onvista.de/api/v1/stocks/{entity}/snapshot"
HISTORY = "https://api.onvista.de/api/v1/instruments/STOCK/{entity}/eod_history"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}

#: Ticker do estudo → (ISIN, entityValue, idNotation da bolsa de origem).
INSTRUMENTS = {"GBLB": ("BE0003797140", "87328", 29217)}

PAUSE_S = 1.0


def find_instrument(isin: str) -> dict:
    """Resolve um ISIN para entityValue e lista de praças disponíveis."""
    r = requests.get(SEARCH, params={"searchValue": isin}, headers=HEADERS, timeout=40)
    r.raise_for_status()
    items = r.json().get("list") or []
    if not items:
        raise LookupError(f"ISIN {isin} não encontrado")
    return items[0]


def exchanges(entity: str) -> list[dict]:
    r = requests.get(SNAPSHOT.format(entity=entity), headers=HEADERS, timeout=45)
    r.raise_for_status()
    found, seen = [], set()

    def walk(node):
        if isinstance(node, dict):
            if "idNotation" in node and node["idNotation"] not in seen:
                seen.add(node["idNotation"])
                found.append(
                    {k: node.get(k) for k in ("idNotation", "codeExchange", "nameExchange")}
                )
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(r.json())
    return found


def fetch_daily(
    entity: str, id_notation: int, first_year: int = 2006, last_year: int = 2025,
    pause: float = PAUSE_S,
) -> pd.DataFrame:
    """Série diária, ano a ano.

    `range=Y1` sozinho devolve só o mês corrente; combinado com `startDate` ele
    passa a respeitar a janela pedida. Sem essa combinação a API responde 400 ou
    ignora o parâmetro em silêncio — que é o pior dos dois casos.
    """
    rows = []
    for year in range(first_year, last_year + 1):
        params = {"idNotation": id_notation, "range": "Y1", "startDate": f"{year}-01-01"}
        r = requests.get(HISTORY.format(entity=entity), params=params, headers=HEADERS, timeout=50)
        r.raise_for_status()
        payload = r.json()
        stamps, closes = payload.get("datetimeLast") or [], payload.get("last") or []
        for ts, close in zip(stamps, closes):
            rows.append(
                {"date": dt.datetime.fromtimestamp(ts, dt.UTC).date(), "close": close}
            )
        time.sleep(pause)

    if not rows:
        return pd.DataFrame(columns=["date", "close"])
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df.date)
    return df.dropna().drop_duplicates("date").sort_values("date").reset_index(drop=True)
