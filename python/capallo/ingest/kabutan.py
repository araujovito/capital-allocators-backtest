"""Coletor Kabutan (株探) — cotações da bolsa de Tóquio.

Fonte japonesa, em japonês, gratuita e sem chave. Encontrada depois de as fontes
anglófonas falharem: Yahoo Finance bloqueia por IP, JPX renderiza no cliente, e a
Twelve Data cobra a JPX no plano Pro.

A lição de método fica registrada: **procurar o dado na língua e na praça de
origem** contorna barreiras que não são técnicas, e sim comerciais — agregadores
internacionais revendem caro o que a fonte local publica aberto.

A visão mensal (`ashi=mon`) cobre desde 2001 e é exatamente a granularidade do
estudo. Cada página traz ~30 meses; a janela 2006-2025 cabe em 10 páginas.

Colunas em japonês: 日付 data, 始値 abertura, 高値 máxima, 安値 mínima,
終値 fechamento, 売買高 volume.
"""

from __future__ import annotations

import io
import time

import pandas as pd
import requests

URL = "https://kabutan.jp/stock/kabuka"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}

#: Ticker do estudo → código na bolsa de Tóquio.
TOKYO_CODES = {"8058": "8058", "8031": "8031"}

MAX_PAGES = 12
PAUSE_S = 1.5


def _parse_page(html: str) -> pd.DataFrame:
    tables = pd.read_html(io.StringIO(html))
    for t in tables:
        if "日付" in list(t.columns) and t.shape[1] >= 6:
            return t
    return pd.DataFrame()


def _to_date(value: str) -> pd.Timestamp:
    """Kabutan usa AA/MM/DD com ano de dois dígitos."""
    return pd.to_datetime(str(value), format="%y/%m/%d")


def fetch_monthly(code: str, pause: float = PAUSE_S) -> pd.DataFrame:
    """Série mensal completa de um código, percorrendo a paginação."""
    frames = []
    for page in range(1, MAX_PAGES + 1):
        r = requests.get(
            URL, params={"code": code, "ashi": "mon", "page": page},
            headers=HEADERS, timeout=45,
        )
        r.raise_for_status()
        t = _parse_page(r.text)
        if t.empty:
            break
        frames.append(t)
        time.sleep(pause)

    if not frames:
        return pd.DataFrame(columns=["date", "ticker", "close"])

    df = pd.concat(frames, ignore_index=True)
    out = pd.DataFrame(
        {
            "date": df["日付"].map(_to_date),
            "ticker": code,
            "close": pd.to_numeric(df["終値"], errors="coerce"),
        }
    )
    return out.dropna().drop_duplicates("date").sort_values("date").reset_index(drop=True)
