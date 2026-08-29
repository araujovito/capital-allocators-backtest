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

## A série é preço puro, e isso é medido

✅ A série é **preço puro**, ajustada por desdobramento e não por dividendo — logo
o provento japonês precisa ser somado por fora, como `build_intl` faz.

A afirmação já foi premissa. O teste original (commit `e07d0a4`) procurou a queda
na data-ex e ficou inconclusivo: março e setembro rendem 1,10 e 1,76 p.p. a menos
que os demais meses no 8058 e no 8031, magnitudes compatíveis com o provento
semestral, mas com t de −0,74 e −1,11. O Kabutan guarda ~14 meses de série diária,
então o teste precisou rodar na série mensal, e o ruído de um mês inteiro engole um
dividendo de 1,5%. A leitura ficou registrada honestamente como premissa.

Depois de a premissa oposta se revelar errada no INVE-B — série tratada como total
return por vinte anos quando era preço puro — esta virou risco material, e na
direção contrária: se o Kabutan fosse total return, o dividendo japonês estaria
sendo **contado duas vezes**, justamente na região de maior prêmio do estudo.

`conferir_contra_relatorio()` responde sem depender de data-ex. O ajuste por
dividendo se acumula para trás: em vinte anos, a ~3,5% ao ano, o começo da série
cairia perto da metade. Não é diferença que se confunda com ruído. Contra o preço
publicado pelas próprias companhias (`data/manual/jp_reported_prices.csv`):

| ativo | referência | pontos | razão média |
|---|---|---|---|
| 8058 | média anual do exercício, relatório de 2015 | 5 | **1,009** |
| 8031 | fechamento de 31 de março, relatório de 2015 | 7 | **1,000** |

O 8031 bate ao iene: o fechamento do Kabutan em 31/03/2006 é 851, e o relatório
publica 1.702 antes do desdobramento 1:2. Preço puro, sem margem para dúvida.
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


def conferir_contra_relatorio(curated, manual) -> pd.DataFrame:
    """Compara a série coletada com o preço publicado pelas próprias companhias.

    Devolve uma linha por ponto de referência, com a razão entre o que o Kabutan
    entrega e o que a companhia publicou, já na mesma escala de desdobramento.
    Razão perto de 1 significa preço puro; uma série ajustada por dividendo
    apareceria perto de 0,5 nesta ponta da janela.
    """
    from pathlib import Path

    px = pd.read_parquet(Path(curated) / "jp_prices.parquet")
    ref = pd.read_csv(Path(manual) / "jp_reported_prices.csv", comment="#")

    linhas = []
    for _, r in ref.iterrows():
        g = px[px.ticker == str(r.ticker)].sort_values("date")
        if r.kind == "year_end_close":
            # Exercício japonês encerra em 31 de março: o fechamento do mês é o dado.
            obs = g[(g.date.dt.year == r.fiscal_year) & (g.date.dt.month == 3)]
            coletado = float(obs.close.iloc[0]) if len(obs) else float("nan")
        elif r.kind == "annual_average":
            # Média dos fechamentos mensais de abril de N-1 a março de N.
            ini = pd.Timestamp(year=int(r.fiscal_year) - 1, month=4, day=1)
            fim = pd.Timestamp(year=int(r.fiscal_year), month=3, day=31)
            coletado = float(g[(g.date >= ini) & (g.date <= fim)].close.mean())
        else:
            raise ValueError(f"tipo de referência desconhecido: {r.kind}")

        publicado = float(r.value_jpy) / float(r.split_factor)
        linhas.append({
            "ticker": str(r.ticker),
            "exercicio": int(r.fiscal_year),
            "tipo": r.kind,
            "publicado": publicado,
            "coletado": coletado,
            "razao": coletado / publicado,
            "fonte": r.source,
        })
    return pd.DataFrame(linhas)


def veredito_da_serie(conferencia: pd.DataFrame, tolerancia: float = 0.06) -> list[str]:
    """Traduz a conferência em problemas, ou em nada.

    A tolerância é folgada de propósito: a média anual do relatório é calculada
    sobre todos os pregões, e a nossa sobre doze fechamentos mensais. O que o
    teste precisa separar não são 2% de método — são os ~45% que um ajuste por
    dividendo de vinte anos produziria.
    """
    problemas = []
    for ticker, g in conferencia.groupby("ticker"):
        razao = float(g.razao.mean())
        if abs(razao - 1.0) > tolerancia:
            problemas.append(
                f"{ticker}: razão média {razao:.3f} contra o preço publicado pela "
                f"companhia — a série não está na escala de preço puro"
            )
    return problemas
