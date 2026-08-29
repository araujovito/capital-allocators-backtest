"""Proventos da Investor AB, pela central de dados do IR da própria companhia.

Este coletor existe por causa de um erro do projeto, e a história importa mais
que o código.

## A hipótese refutada

`avanza.py` afirmava — e o README repetiu por dois dias — que a série da Avanza
para INVE-B já era **total return**, com dividendo reembolsado no preço. A
conclusão veio de um teste de cinco datas-ex em que o retorno médio do papel era
positivo (+0,146%) em vez de cair os ~1,6% do dividendo. Parecia demonstração.

Era **erro de alinhamento de um dia**. As datas usadas como "data-ex" vinham do
calendário de assembleia, e o teste comparava o fechamento do dia-ex com o do dia
**seguinte** — mediu o dia depois da queda, não a queda. Com a data-ex verdadeira
publicada pelo IR, e com 27 eventos em vez de 5, o sinal é inequívoco:

| medida | valor |
|---|---|
| retorno médio no dia-ex | **−2,085%** |
| dividendo esperado, sobre o preço cum | **−1,992%** |
| resíduo | −0,093 p.p. |
| retorno de um dia qualquer | +0,066% (dp 1,51%) |
| t contra zero | **−5,63** |

O papel cai exatamente o dividendo na data-ex. A série da Avanza é **preço puro**,
não total return. Confere também com o nível: o fechamento de 2005-01-02 é 21,44
SEK pós-desdobramento (85,8 pré), que é o preço que a Investor B tinha — uma série
com vinte anos de dividendo reinvestido começaria bem abaixo disso.

## O que o erro custava, e para que lado

INVE-B entrava no estudo **sem provento nenhum** por vinte anos, não sem os 30% de
retenção. O erro não era de 0,5 a 0,8 p.p. ao ano; era o dividendo inteiro, ~2,5%
ao ano bruto. E o viés corria **contra** os allocators europeus, não a favor —
exatamente o contrário do que o README declarava como assimetria conhecida. A
lição que fica: um teste que confirma a hipótese barata merece a mesma
desconfiança que um que a contraria.

## A fonte

O site da Investor AB embute a página de dividendos num iframe do provedor de IR
(`vp053.alertir.com`), que por sua vez lê um endpoint público de dados de mercado
alimentado pela Millistream. Ele devolve a série de eventos societários desde
1976, com data-ex, valor nominal e valor **ajustado por desdobramento** — este
último é o que interessa, porque a série de preço da Avanza também é ajustada.

O desdobramento 4:1 de 2021 aparece no próprio dado, como `adjustmentfactor` 0,25
até maio de 2021 e 1,00 depois: não é premissa nossa.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import requests

#: Endpoint de dados do provedor de IR da Investor AB, e o identificador do papel.
#: `MDA:354` foi lido da configuração da própria página de dividendos do IR.
BASE = "https://vp053.alertir.com/afw/MarketDataServer.php"
INSTRUMENT = "MDA:354"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Referer": "https://vp053.alertir.com/v4/en/dividends",
}

#: Janela do estudo. Eventos fora dela são coletados mas não usados.
START, END = pd.Timestamp("2006-01-01"), pd.Timestamp("2025-12-31")


def fetch_events() -> pd.DataFrame:
    """Eventos societários de INVE-B, com data-ex e valor ajustado."""
    r = requests.get(
        BASE,
        params={"type": "corporateaction_events", "format": "json_compact", "id": INSTRUMENT},
        headers=HEADERS,
        timeout=60,
    )
    r.raise_for_status()
    serie = r.json()["data"][INSTRUMENT]["compact_series"]
    df = pd.DataFrame(serie["vals"], columns=serie["keys"])
    df["ex_date"] = [
        pd.Timestamp(dt.datetime.fromtimestamp(t, dt.UTC).date()) for t in df.timestamp
    ]
    return df


def build(out_dir: Path) -> pd.DataFrame:
    """Grava `se_dividends.parquet` com os proventos da janela, já pós-desdobramento."""
    ev = fetch_events()
    d = ev[(ev.type == "dividend") & (ev.ex_date >= START) & (ev.ex_date <= END)].copy()
    out = pd.DataFrame({
        "ticker": "INVE-B",
        "ex_date": d.ex_date.to_numpy(),
        # `dividend` é o valor nominal da época; `dividend_adjusted` já traz o 4:1
        # de 2021 aplicado, na mesma base da série de preço da Avanza.
        "dps_sek": d.dividend_adjusted.astype(float).to_numpy(),
        "dps_nominal": d.dividend.astype(float).to_numpy(),
        "parcela": d.subtype.to_numpy(),
    }).sort_values("ex_date").reset_index(drop=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_dir / "se_dividends.parquet", index=False)
    return out


def conferir_avanza(out_dir: Path) -> list[str]:
    """Confere os eventos recentes contra a Avanza, que é a fonte do preço.

    A Avanza só publica dividendo desde 2019 — não serve para montar a série, mas
    serve de segunda fonte no trecho em que existe. A data-ex dela é o dia
    seguinte à do IR: a Millistream marca o **último dia com direito**, e é essa
    diferença de um dia que produziu o erro que este módulo corrige.
    """
    nosso = pd.read_parquet(out_dir / "se_dividends.parquet")
    r = requests.get(
        "https://www.avanza.se/_api/market-guide/stock/5247/details",
        headers={"User-Agent": HEADERS["User-Agent"]},
        timeout=40,
    )
    r.raise_for_status()
    eventos = r.json()["dividends"]["pastEvents"]
    deles = {pd.Timestamp(e["exDate"]): float(e["amount"]) for e in eventos}

    divergencias = []
    conferidos = 0
    for _, x in nosso.iterrows():
        # A data-ex da Avanza é o pregão seguinte ao último dia com direito.
        par = [v for d, v in deles.items() if 0 <= (d - x.ex_date).days <= 4]
        if not par:
            continue
        conferidos += 1
        if abs(par[0] - x.dps_sek) > 0.005:
            divergencias.append(
                f"{x.ex_date.date()}: IR diz {x.dps_sek:.2f} SEK, Avanza diz {par[0]:.2f}"
            )
    if conferidos < 10:
        divergencias.append(f"apenas {conferidos} eventos puderam ser cruzados com a Avanza")
    return divergencias


def validate(out_dir: Path) -> list[str]:
    """Guardas de sanidade sobre o que foi coletado."""
    path = out_dir / "se_dividends.parquet"
    if not path.exists():
        return [f"{path} não existe"]
    df = pd.read_parquet(path)

    problemas = []
    if (df.dps_sek <= 0).any():
        problemas.append("provento zero ou negativo na janela")
    anos = set(df.ex_date.dt.year)
    faltando = sorted(set(range(2006, 2026)) - anos)
    if faltando:
        problemas.append(f"anos sem provento: {faltando}")
    # A Investor AB passou a pagar em duas parcelas a partir de 2018. Antes disso,
    # uma por ano. Um ano com três eventos indicaria dado duplicado.
    for ano, n in df.groupby(df.ex_date.dt.year).size().items():
        if n > 2:
            problemas.append(f"{ano}: {n} proventos — duplicidade provável")
    return problemas


def evidencia_data_ex(out_dir: Path) -> pd.DataFrame:
    """Mede, evento a evento, o que o preço faz na data-ex.

    É esta medida que decide se a série da Avanza é preço puro ou total return, e
    ela roda toda vez que o coletor roda — a afirmação não fica congelada num
    comentário. Uma série de preço cai o dividendo; uma de total return não cai.
    """
    from capallo.ingest.avanza import ORDERBOOKS, fetch_daily

    px = fetch_daily(ORDERBOOKS["INVE-B"]).set_index("date")
    div = pd.read_parquet(out_dir / "se_dividends.parquet")

    linhas = []
    idx = px.index
    for _, r in div.iterrows():
        pos = idx.searchsorted(r.ex_date)
        if pos == 0 or pos >= len(idx) or idx[pos] != r.ex_date:
            continue
        p_cum, p_ex = float(px.close.iloc[pos - 1]), float(px.close.iloc[pos])
        linhas.append({
            "ex_date": r.ex_date,
            "retorno_pct": (p_ex / p_cum - 1) * 100,
            "dividendo_pct": -float(r.dps_sek) / p_cum * 100,
        })
    ev = pd.DataFrame(linhas)
    diario = px.close.pct_change().dropna() * 100
    ev.attrs["dia_qualquer_pct"] = float(diario.mean())
    ev.attrs["dp_diario_pct"] = float(diario.std())
    ev.attrs["t_stat"] = float(
        ev.retorno_pct.mean() / (ev.retorno_pct.std() / len(ev) ** 0.5)
    )
    ev.attrs["residuo_pp"] = float((ev.retorno_pct - ev.dividendo_pct).mean())
    return ev
