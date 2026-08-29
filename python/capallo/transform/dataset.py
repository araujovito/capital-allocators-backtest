"""Prepara o dataset que o motor Rust consome.

Fronteira entre as duas linguagens: Python resolve fonte, moeda, calendário e
frequência; o Rust recebe um painel já limpo e homogêneo e só simula.

Decisões materializadas aqui:

- **Frequência mensal.** Os aportes do estudo são mensais. O valor do mês é o do
  último pregão com negociação naquele mês, por ativo.
- **Tudo em BRL.** A unidade econômica do estudo é o real. Ativos em moeda
  estrangeira são convertidos pela PTAX de venda da mesma data — venda porque é a
  ponta que o investidor brasileiro paga ao comprar moeda. A escolha é
  parametrizada (`fx_side`) para que o custo dela possa ser medido em vez de
  afirmado; ver `capallo.analysis.sensitivity`.
- **Calendários diferentes não são alinhados à força.** Cada ativo usa o próprio
  último pregão do mês. Forçar uma data comum introduziria preço de um dia em que
  o ativo não negociou.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

#: Moeda de **negociação** de cada ativo — a que o investidor precisa comprar.
#: Não confundir com a moeda de exposição do `universe`: IEV e EWJ replicam Europa
#: e Japão, mas são liquidados em dólar, e é o dólar que o câmbio precisa cobrir.
CURRENCY = {
    "ITSA4": "BRL", "BRAP4": "BRL", "PIBB11": "BRL",
    "BRK-B": "USD", "MKL": "USD", "IVV": "USD", "IEV": "USD", "EWJ": "USD",
    "GBLB": "EUR", "INVE-B": "SEK", "8058": "JPY", "8031": "JPY",
    # Índices do experimento Index Benchmark. A MSCI só publica em dólar, que é
    # também a moeda em que os três ETFs estrangeiros liquidam: as duas pernas
    # atravessam o mesmo câmbio, e a comparação entre elas não vira aposta cambial.
    "IBXL": "BRL", "MXUS": "USD", "MXEU": "USD", "MXJP": "USD",
    # Modern Alternative: o mundo num ticker só, liquidado em dólar.
    "ACWI": "USD",
    # Renda fixa com retorno real contratado, em reais.
    "IPCAP": "BRL",
}


def _monthly_last(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Último valor observado de cada mês, por ticker."""
    out = df.copy()
    out["month"] = out.date.dt.to_period("M")
    idx = out.groupby(["ticker", "month"]).date.idxmax()
    out = out.loc[idx, ["ticker", "month", "date", value_col]]
    return out.rename(columns={value_col: "tr_local"}).reset_index(drop=True)


#: Pontas da PTAX aceitas na conversão. `mid` não é cotação publicada: é a média
#: das duas, útil só como referência de sensibilidade.
FX_SIDES = ("ask", "bid", "mid")


def build(curated: Path, fx_side: str = "ask") -> pd.DataFrame:
    if fx_side not in FX_SIDES:
        raise ValueError(f"fx_side deve ser um de {FX_SIDES}, veio {fx_side!r}")
    frames = []

    br = pd.read_parquet(curated / "br_total_return.parquet")
    frames.append(_monthly_last(br, "tr_index"))

    us = pd.read_parquet(curated / "equities_us.parquet")
    # `close_net`, não `close_adj`: o fechamento ajustado reinveste o dividendo
    # bruto, e a retenção de 30% da seção 4 da metodologia precisa incidir também
    # sobre o papel americano. Ver `transform.us_net`.
    if "close_net" not in us.columns:
        raise ValueError("equities_us.parquet sem close_net — rode `capallo build-us-net`")
    frames.append(_monthly_last(us, "close_net"))

    intl = pd.read_parquet(curated / "intl_total_return.parquet")
    frames.append(_monthly_last(intl, "tr_index"))

    # Índices do Index Benchmark, quando já coletados. Opcional porque o
    # experimento principal — Historical Reality — não depende deles, e o painel
    # tem de continuar montando para quem só rodou o pipeline até aqui.
    caminho_tesouro = curated / "tesouro_total_return.parquet"
    if caminho_tesouro.exists():
        tes = pd.read_parquet(caminho_tesouro)
        frames.append(_monthly_last(tes, "tr_index"))

    caminho_indices = curated / "indices.parquet"
    if caminho_indices.exists():
        idx = pd.read_parquet(caminho_indices)
        if "close_net" not in idx.columns:
            raise ValueError(
                "indices.parquet sem close_net — rode `capallo build-indices`"
            )
        frames.append(_monthly_last(idx, "close_net"))

    panel = pd.concat(frames, ignore_index=True)
    panel["currency"] = panel.ticker.map(CURRENCY)

    # Ticker sem moeda vira NaN, e `groupby` descarta NaN sem avisar: o ativo
    # simplesmente não chega ao motor, que só reclama quando uma estratégia pede
    # por ele. Aconteceu ao entrar o ACWI. A guarda transforma o sumiço silencioso
    # em erro no lugar certo.
    orfaos = sorted(set(panel.ticker[panel.currency.isna()]))
    if orfaos:
        raise ValueError(f"tickers sem moeda declarada em CURRENCY: {orfaos}")

    # Conversão para BRL pela PTAX de venda da mesma data, moeda a moeda.
    # O `merge_asof` volta no tempo até a última PTAX publicada: o fim de mês de
    # um mercado cai em feriado brasileiro sem que isso invente uma cotação.
    ptax = pd.read_parquet(curated / "ptax.parquet")
    panel = panel.sort_values("date").reset_index(drop=True)
    partes = []
    for moeda, g in panel.groupby("currency", sort=False):
        if moeda == "BRL":
            partes.append(g.assign(fx=1.0))
            continue
        cot = ptax[ptax.currency == moeda].sort_values("date").copy()
        if cot.empty:
            raise ValueError(f"PTAX não cobre {moeda}")
        cot["mid"] = (cot.bid + cot.ask) / 2
        cot = cot[["date", fx_side]]
        m = pd.merge_asof(g.sort_values("date"), cot, on="date", direction="backward")
        partes.append(m.rename(columns={fx_side: "fx"}))
    panel = pd.concat(partes, ignore_index=True).sort_values(["ticker", "month"])

    panel["tr_brl"] = panel.tr_local * panel.fx

    missing = panel[panel.tr_brl.isna()]
    if len(missing):
        raise ValueError(f"{len(missing)} linhas sem conversão de câmbio")

    return panel[["month", "date", "ticker", "currency", "tr_local", "fx", "tr_brl"]]


def build_macro(curated: Path) -> pd.DataFrame:
    """Painel macro mensal: fator do CDI no mês e variação do IPCA."""
    cdi = pd.read_parquet(curated / "cdi.parquet")
    cdi["month"] = cdi.date.dt.to_period("M")
    # CDI é taxa diária em %; o fator do mês é o produto dos dias úteis.
    cdi_m = cdi.groupby("month").value.apply(lambda s: float((1 + s / 100).prod()))

    ipca = pd.read_parquet(curated / "ipca.parquet")
    ipca["month"] = ipca.date.dt.to_period("M")
    ipca_m = ipca.groupby("month").value.last() / 100 + 1

    macro = pd.DataFrame({"cdi_factor": cdi_m, "ipca_factor": ipca_m}).dropna()
    return macro.reset_index()


def export(curated: Path, out_dir: Path, fx_side: str = "ask") -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    panel = build(curated, fx_side=fx_side)
    macro = build_macro(curated)

    # O motor lê CSV: formato estável, inspecionável e sem dependência de schema
    # binário entre as duas linguagens. O Parquet segue como armazenamento curado.
    p = panel.assign(month=panel.month.astype(str)).drop(columns=["date"])
    p.to_csv(out_dir / "panel.csv", index=False, float_format="%.10f")
    macro.assign(month=macro.month.astype(str)).to_csv(
        out_dir / "macro.csv", index=False, float_format="%.10f"
    )
    return {"panel": len(p), "macro": len(macro), "tickers": panel.ticker.nunique()}
