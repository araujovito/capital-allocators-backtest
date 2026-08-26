"""Coletor do Banco Central do Brasil.

Fonte oficial e gratuita para a camada macro do estudo: CDI, IPCA e PTAX.
Sem chave de API e sem anti-bot — ao contrário das fontes de renda variável.

Duas APIs distintas:
- **SGS** (séries temporais) para CDI e IPCA. Limita ~10 anos por requisição em
  séries diárias, então as janelas são fatiadas.
- **Olinda/PTAX** para câmbio, que cobre SEK — o SGS não expõe a coroa sueca.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import requests

SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
PTAX_URL = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,"
    "dataFinalCotacao=@dataFinalCotacao)"
)

SGS_SERIES: dict[str, int] = {
    "CDI": 12,     # taxa over diária, % ao dia
    "IPCA": 433,   # variação mensal, %
    "SELIC": 11,   # reservado para a V2
}

#: PTAX cobre estas moedas contra o BRL.
PTAX_CURRENCIES = ("USD", "EUR", "JPY", "SEK")


def _sgs_chunk(code: int, start: date, end: date) -> pd.DataFrame:
    params = {
        "formato": "json",
        "dataInicial": start.strftime("%d/%m/%Y"),
        "dataFinal": end.strftime("%d/%m/%Y"),
    }
    r = requests.get(SGS_URL.format(code=code), params=params, timeout=60)
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return pd.DataFrame(columns=["date", "value"])
    df = pd.DataFrame(rows)
    return pd.DataFrame(
        {
            "date": pd.to_datetime(df["data"], format="%d/%m/%Y"),
            "value": pd.to_numeric(df["valor"]),
        }
    )


def fetch_sgs(name: str, start: date, end: date) -> pd.DataFrame:
    """Baixa uma série do SGS, fatiando em janelas de 9 anos."""
    code = SGS_SERIES[name]
    parts = []
    cursor = start
    while cursor <= end:
        stop = min(date(cursor.year + 9, cursor.month, cursor.day), end)
        parts.append(_sgs_chunk(code, cursor, stop))
        cursor = date(stop.year, stop.month, stop.day) + pd.Timedelta(days=1)
    df = pd.concat(parts, ignore_index=True).drop_duplicates("date").sort_values("date")
    return df.reset_index(drop=True)


def fetch_ptax(currency: str, start: date, end: date) -> pd.DataFrame:
    """Baixa a PTAX de uma moeda contra o BRL, fatiando por ano.

    Retorna compra e venda. A escolha de qual usar é decisão do pipeline, não
    do coletor: compra e venda diferem em ~0,5%, o que ao longo de 240 aportes
    não é ruído desprezível.
    """
    parts = []
    for year in range(start.year, end.year + 1):
        lo = max(start, date(year, 1, 1))
        hi = min(end, date(year, 12, 31))
        params = {
            "@moeda": f"'{currency}'",
            "@dataInicial": f"'{lo.strftime('%m-%d-%Y')}'",
            "@dataFinalCotacao": f"'{hi.strftime('%m-%d-%Y')}'",
            "$format": "json",
            "$select": "cotacaoCompra,cotacaoVenda,dataHoraCotacao",
        }
        r = requests.get(PTAX_URL, params=params, timeout=60)
        r.raise_for_status()
        rows = r.json().get("value", [])
        if rows:
            parts.append(pd.DataFrame(rows))
    if not parts:
        return pd.DataFrame(columns=["date", "bid", "ask"])
    df = pd.concat(parts, ignore_index=True)
    return (
        pd.DataFrame(
            {
                "date": pd.to_datetime(df["dataHoraCotacao"]).dt.normalize(),
                "bid": pd.to_numeric(df["cotacaoCompra"]),
                "ask": pd.to_numeric(df["cotacaoVenda"]),
            }
        )
        .drop_duplicates("date")
        .sort_values("date")
        .reset_index(drop=True)
    )
