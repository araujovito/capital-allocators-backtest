"""Índices dos quatro mercados, para o experimento *Index Benchmark* da §7.

O experimento existe para separar duas afirmações que o placar principal mistura:
o allocator venceu **o mercado**, ou venceu **o produto que dava para comprar em
2006**? A diferença é taxa de administração, tracking error e o custo de embrulhar
uma carteira num fundo — e ela não é desprezível em ETF de mercado estrangeiro.

## As fontes, e por que duas linhas são substitutas

| Índice | Fonte | É o índice do ETF? |
|---|---|---|
| IBrX-50 (IBXL) | B3, estatísticas históricas | ✅ sim — é o índice do PIBB11 |
| MSCI Japan | MSCI, dados de fim de dia | ✅ sim — é o índice do EWJ |
| MSCI USA | MSCI | ⚠️ não — o do IVV é o S&P 500 |
| MSCI Europe | MSCI | ⚠️ não — o do IEV é o S&P Europe 350 |

A S&P Dow Jones responde **403** a qualquer requisição de nível de índice, com
navegador ou sem. A MSCI publica de graça, mensal, desde os anos 1970, nas três
variantes (bruto, líquido e só preço). Então metade do experimento usa o índice
exato e metade usa o índice da mesma região com outra regra de construção.

**O custo dessa troca é medido, não suposto.** `risco_da_substituicao()` compara
cada índice com o total return bruto do próprio ETF: onde o índice é o do ETF, a
diferença é o que o produto custa; onde é substituto, a diferença mistura o custo
do produto com a diferença entre os dois índices, e é isso que fica declarado.

## As três variantes da MSCI, e qual entra

`GRTR` reinveste o dividendo **bruto**; `NETR` reinveste líquido, mas com as
alíquotas que a MSCI assume, não com as que a §4 da metodologia congelou para o
investidor brasileiro; `STRD` é só preço. Entra `GRTR` **com a retenção da
metodologia aplicada por fora**, pelo mesmo método de `transform.us_net`: o
provento do mês é o que sobra entre o bruto e o preço puro. Assim a perna do
índice recebe exatamente o tratamento tributário da perna do ETF, e a comparação
mede o produto, não o regime fiscal.

## O IBrX-50 é total return, e o PIBB11 não distribui — os dois verificados

Depois do caso INVE-B, nenhuma série entra aqui com a classificação suposta.

Duas afirmações precisavam de teste. A primeira: o IBrX-50 reinveste dividendo?
A segunda é mais estranha e apareceu ao testar a primeira: `b3_cash_dividends`
não tem **nenhum** provento do PIBB11 em vinte anos, e as unidades do ETF nunca
crescem — a mesma assinatura do erro sueco.

O teste de ordenação responde às duas de uma vez, e a resposta é que **as duas
estão certas**: o PIBB11 acumula o dividendo dentro do fundo em vez de distribuir,
que é característica declarada do produto. Se ele distribuísse e a coleta tivesse
perdido, o preço puro dele ficaria vários pontos ao ano abaixo do índice de
retorno total; se o índice fosse só preço, ficaria abaixo do ETF. Nenhum dos dois
acontece — os dois andam colados, que é o único arranjo compatível com índice de
retorno total e fundo que reinveste internamente.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pandas as pd
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}

#: Serviço público de níveis de índice da MSCI, o mesmo que alimenta a busca de
#: dados de fim de dia do site. Devolve série mensal em USD.
MSCI_URL = "https://app2.msci.com/products/service/index/indexmaster/getLevelDataForGraph"

#: Ticker do estudo → código MSCI. Os códigos foram lidos do próprio serviço.
MSCI_CODES = {"MXUS": "984000", "MXEU": "990500", "MXJP": "939200"}

#: Índice do experimento Modern Alternative (§7): o mundo inteiro, ponderado por
#: capitalização, num ticker só. Fica separado de `MSCI_CODES` porque não é
#: benchmark de ETF nenhum do estudo — é outro experimento, e §7 manda não
#: misturar. A coluna `grupo` do parquet carrega essa separação adiante.
MSCI_MODERN = {"ACWI": "892400"}

#: Estatísticas históricas de índice da B3. O parâmetro é um JSON em base64.
B3_URL = ("https://sistemaswebb3-listados.b3.com.br/indexStatisticsProxy/"
          "IndexCall/GetPortfolioDay/")

#: Dezembro de 2005 entra como mês-base: o retorno de janeiro/2006 precisa de um
#: nível anterior, exatamente como no painel dos ativos.
START, END = pd.Timestamp("2005-12-01"), pd.Timestamp("2025-12-31")


def fetch_msci(code: str, variant: str = "GRTR") -> pd.Series:
    """Nível mensal de fim de mês, em dólar.

    `variant`: `GRTR` bruto, `NETR` líquido pelas alíquotas da MSCI, `STRD` preço.
    """
    r = requests.get(MSCI_URL, params={
        "currency_symbol": "USD", "index_variant": variant,
        "start_date": START.strftime("%Y%m%d"), "end_date": END.strftime("%Y%m%d"),
        "data_frequency": "END_OF_MONTH", "index_codes": code,
    }, headers=HEADERS, timeout=60)
    r.raise_for_status()
    niveis = r.json()["indexes"]["INDEX_LEVELS"]
    if not niveis:
        raise ValueError(f"MSCI não devolveu nível para o código {code}")
    return pd.Series(
        {pd.Timestamp(str(x["calc_date"])): float(x["level_eod"]) for x in niveis}
    ).sort_index()


def fetch_b3_index(index: str, anos: range) -> pd.Series:
    """Fechamentos diários de um índice da B3, ano a ano.

    A resposta é uma grade de 31 dias × 12 meses por ano, com nulo onde não houve
    pregão. Ler a grade em vez de uma série é feio, mas é o formato que a fonte
    publica — e converter aqui deixa o resto do pipeline com uma série normal.
    """
    valores: dict[pd.Timestamp, float] = {}
    for ano in anos:
        payload = json.dumps({"language": "pt-br", "index": index, "year": str(ano)})
        url = B3_URL + base64.b64encode(payload.encode()).decode()
        r = requests.get(url, headers=HEADERS, timeout=60)
        r.raise_for_status()
        for linha in r.json().get("results") or []:
            for mes in range(1, 13):
                bruto = linha.get(f"rateValue{mes}")
                if not bruto:
                    continue
                # Formato brasileiro: 26.965,31
                valor = float(bruto.replace(".", "").replace(",", "."))
                valores[pd.Timestamp(year=ano, month=mes, day=int(linha["day"]))] = valor
    if not valores:
        raise ValueError(f"B3 não devolveu série para o índice {index}")
    return pd.Series(valores).sort_index()


def build(out_dir: Path) -> pd.DataFrame:
    """Grava `indices.parquet` com bruto e preço puro de cada índice.

    Guarda as duas variantes porque a retenção incide entre elas — é o método de
    `transform.us_net`, e sem o preço puro não há como separar o provento do mês.
    O IBrX-50 não tem par: índice brasileiro não sofre retenção na fonte para
    pessoa física, e a §4 congelou Brasil em zero.
    """
    frames = []
    for grupo, codigos in (("index", MSCI_CODES), ("modern", MSCI_MODERN)):
        for ticker, code in codigos.items():
            bruto = fetch_msci(code, "GRTR")
            preco = fetch_msci(code, "STRD")
            frames.append(pd.DataFrame({
                "date": bruto.index, "ticker": ticker, "grupo": grupo,
                "close_adj": bruto.to_numpy(),
                "close_px": preco.reindex(bruto.index).to_numpy(),
            }))

    ibxl = fetch_b3_index("IBXL", range(START.year, END.year + 1))
    mensal = ibxl.resample("ME").last().dropna()
    mensal = mensal[(mensal.index >= START) & (mensal.index <= END)]
    # Índice brasileiro de retorno total: bruto e "preço puro" coincidem porque
    # não há retenção a aplicar. Repetir a coluna mantém o esquema uniforme.
    frames.append(pd.DataFrame({
        "date": mensal.index, "ticker": "IBXL", "grupo": "index",
        "close_adj": mensal.to_numpy(), "close_px": mensal.to_numpy(),
    }))

    df = pd.concat(frames, ignore_index=True).sort_values(["ticker", "date"])
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "indices.parquet", index=False)
    return df


def _cagr(s: pd.Series, anos: int = 20) -> float:
    return float(s.iloc[-1] / s.iloc[0]) ** (1 / anos) - 1


#: Base e fim da comparação, em fim de mês. Comparar séries que começam em dias
#: diferentes — o índice em 31/12/2005 e o ETF em 02/01/2006 — embute o retorno de
#: um mês inteiro na diferença, e um mês de bolsa é maior que o custo anual de
#: qualquer ETF. Toda comparação aqui passa por esta grade.
BASE, FIM = pd.Timestamp("2005-12-31"), pd.Timestamp("2025-12-31")


def _mensal(df: pd.DataFrame, coluna: str) -> pd.Series:
    """Último valor de cada mês, recortado na mesma base para todas as séries."""
    g = df.sort_values("date")
    s = pd.Series(g[coluna].to_numpy(), index=pd.DatetimeIndex(g.date))
    s = s.resample("ME").last().dropna()
    return s[(s.index >= BASE) & (s.index <= FIM)]


def risco_da_substituicao(curated: Path) -> pd.DataFrame:
    """Compara cada índice com o total return **bruto** do ETF da mesma região.

    A leitura da coluna `diferenca_pp` depende de qual linha é:

    - **EWJ** e **PIBB11** — o índice é o do próprio produto, então a diferença é
      o que o produto custa: taxa, tracking error, amostragem.
    - **IVV** e **IEV** — o índice é substituto, então a diferença mistura o custo
      do produto com a distância entre dois índices da mesma região. Não dá para
      separar as duas parcelas com esta fonte, e é isso que fica declarado.
    """
    from capallo.universe import INDICE_DO_ETF

    idx = pd.read_parquet(curated / "indices.parquet")
    us = pd.read_parquet(curated / "equities_us.parquet")
    br = pd.read_parquet(curated / "br_total_return.parquet")

    linhas = []
    for etf, indice in INDICE_DO_ETF.items():
        ind = _mensal(idx[idx.ticker == indice], "close_adj")
        fonte = br[br.ticker == etf] if etf == "PIBB11" else us[us.ticker == etf]
        col = "tr_index" if etf == "PIBB11" else "close_adj"
        produto = _mensal(fonte, col)
        # A base do ETF brasileiro é o fim de dez/2005 se houver pregão coletado;
        # sem ele, as duas séries são reancoradas no primeiro mês comum.
        comum = ind.index.intersection(produto.index)
        ind, produto = ind.loc[comum], produto.loc[comum]
        anos = (comum[-1] - comum[0]).days / 365.25
        linhas.append({
            "etf": etf,
            "indice": indice,
            "e_o_indice_do_etf": etf in ("PIBB11", "EWJ"),
            "meses": len(comum),
            "indice_bruto_aa": _cagr(ind, anos),
            "etf_bruto_aa": _cagr(produto, anos),
            "diferenca_pp": (_cagr(ind, anos) - _cagr(produto, anos)) * 100,
        })
    return pd.DataFrame(linhas)


def teste_de_retorno_total(curated: Path) -> pd.DataFrame:
    """Ordenação que classifica a série brasileira sem depender de data-ex.

    Três números, em moeda local, no mesmo período:

    1. preço puro do PIBB11 (COTAHIST),
    2. total return do PIBB11 como o pipeline o monta,
    3. o IBrX-50 publicado pela B3.

    Se o índice fosse **só preço**, ficaria vários pontos ao ano **abaixo** do
    total return do ETF. Se o PIBB11 distribuísse provento e a coleta tivesse
    perdido, o preço puro dele ficaria muito abaixo do índice. Os dois cenários
    de erro deslocam a ordenação; o cenário correto — índice de retorno total e
    fundo que reinveste internamente — deixa os três colados.
    """
    idx = pd.read_parquet(curated / "indices.parquet")
    precos = pd.read_parquet(curated / "b3_prices.parquet")
    tr = pd.read_parquet(curated / "br_total_return.parquet")

    p = _mensal(precos[precos.ticker == "PIBB11"], "close")
    t = _mensal(tr[tr.ticker == "PIBB11"], "tr_index")
    i = _mensal(idx[idx.ticker == "IBXL"], "close_adj")
    comum = p.index.intersection(t.index).intersection(i.index)
    anos = (comum[-1] - comum[0]).days / 365.25

    return pd.DataFrame([
        {"serie": "PIBB11 — só preço (COTAHIST)", "cagr_aa": _cagr(p.loc[comum], anos)},
        {"serie": "PIBB11 — total return do pipeline", "cagr_aa": _cagr(t.loc[comum], anos)},
        {"serie": "IBrX-50 — publicado pela B3", "cagr_aa": _cagr(i.loc[comum], anos)},
    ])


def validate(curated: Path) -> list[str]:
    path = curated / "indices.parquet"
    if not path.exists():
        return [f"{path} não existe"]
    df = pd.read_parquet(path)

    problemas = []
    esperados = set(MSCI_CODES) | set(MSCI_MODERN) | {"IBXL"}
    if set(df.ticker) != esperados:
        problemas.append(f"tickers {sorted(set(df.ticker))}, esperados {sorted(esperados)}")

    for ticker, g in df.groupby("ticker"):
        g = g.sort_values("date")
        # 241 observações: dez/2005 como mês-base mais os 240 meses do estudo.
        if len(g) != 241:
            problemas.append(f"{ticker}: {len(g)} meses, esperados 241")
        if g.date.iloc[-1] < pd.Timestamp("2025-12-01"):
            problemas.append(f"{ticker}: série termina em {g.date.iloc[-1].date()}")
        if (g.close_adj <= 0).any() or (g.close_px <= 0).any():
            problemas.append(f"{ticker}: nível zero ou negativo")
        # Bruto reinveste dividendo, preço não: o bruto tem de crescer mais.
        if ticker != "IBXL":
            bruto, preco = _cagr(g.close_adj), _cagr(g.close_px)
            if bruto <= preco:
                problemas.append(
                    f"{ticker}: variante bruta ({bruto:.2%}) não supera a de preço "
                    f"({preco:.2%}) — as duas variantes podem estar trocadas"
                )

    # A ordenação brasileira é a guarda contra os dois erros de classificação.
    ordem = teste_de_retorno_total(curated)
    disp = float(ordem.cagr_aa.max() - ordem.cagr_aa.min())
    if disp > 0.02:
        problemas.append(
            f"PIBB11 e IBrX-50 divergem {disp * 100:.1f} p.p. ao ano — ou o índice "
            f"não é de retorno total, ou falta provento do ETF"
        )
    return problemas
