"""Tesouro Direto — preços e taxas históricas dos títulos públicos.

Fonte primária e aberta: o portal **Tesouro Transparente** publica, num CSV único,
o preço unitário e a taxa de todo título ofertado desde 2002, pregão a pregão.
Não há chave, não há paginação e não há limite de requisição — é o oposto de tudo
o que a coleta internacional deste estudo enfrentou.

## Qual título, e por quê

Entre os dois sabores de IPCA+, entra o **`Tesouro IPCA+` sem juros semestrais**
(NTN-B Principal), e a escolha é metodológica, não de conveniência:

- É **zero-cupom**. O total return é a variação do preço unitário, e ponto. O
  primo com juros semestrais exigiria modelar reinvestimento de cupom a cada seis
  meses por vinte anos, com uma convenção nova em cada passo — a mesma família de
  problema que a data-ex criou no lado internacional, e sem necessidade.
- Está disponível desde **18/07/2005**, antes do início da janela. Satisfaz a
  regra anti-cherry-picking sem folga: o investidor de 31/12/2005 podia comprá-lo.

Cobertura verificada: nenhum dos 240 meses da janela fica sem cotação.

## A convenção de compra e venda, que é o inverso da PTAX

No arquivo, `PU Compra` é o preço **pelo qual o investidor compra** e `PU Venda` é
por onde ele **vende de volta** ao Tesouro. Compra é sempre o maior dos dois, e a
diferença — 1,13% em média, 0,82% na mediana — fica com o Tesouro.

⚠️ É o oposto do vocabulário da PTAX, em que "venda" é a ponta que o investidor
paga. Confundir os dois inverteria o spread e faria o título render de graça o que
custa.

## `PU Base` não serve de marcação, e a validação é que descobriu

A leitura inicial deste módulo foi que `PU Base` era o preço de marcação, porque
nas linhas recentes ele coincide com `PU Venda`. A guarda de coerência reprovou —
**coincide em 30% da amostra e diverge em 70%**, e a divergência não é ruído: até
2021 o `PU Base` fica sistematicamente ~0,04% **abaixo** do `PU Venda`, e a partir
de 2022 os dois passam a ser o mesmo número. É uma coluna que **mudou de
significado no meio da série**, que é o tipo de armadilha que só aparece olhando a
amostra inteira em vez das últimas linhas.

A marcação usa `PU Venda`, que tem definição estável nos vinte anos: é o que o
investidor recebe se vender de volta hoje. `PU Compra` entra só onde há compra de
verdade. `PU Base` fica no arquivo, sem uso.

## Um pregão descartado, declarado

Em **01/07/2010**, para o vencimento 2015-05-15, o arquivo traz preço de compra
**abaixo** do de venda — spread negativo, que não existe. É 1 linha em 17.438. Ela
é descartada na coleta, com o motivo escrito, em vez de virar exceção silenciosa
numa tolerância frouxa.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import requests

CKAN = ("https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"
        "?id=taxas-dos-titulos-ofertados-pelo-tesouro-direto")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}

#: Sem juros semestrais: o total return é a variação do preço unitário.
TITULO = "Tesouro IPCA+"

#: Dezembro de 2005 entra como mês-base, como no painel dos demais ativos.
START, END = pd.Timestamp("2005-12-01"), pd.Timestamp("2025-12-31")

#: Pregões com spread negativo tolerados como erro de fonte antes de virar erro
#: de método. Medido em 2026-08-29: 1 linha em 17.438.
MAX_SPREAD_NEGATIVO = 5

COLUNAS = {
    "Data Base": "date",
    "Data Vencimento": "maturity",
    "PU Compra Manha": "pu_compra",
    "PU Venda Manha": "pu_venda",
    "PU Base Manha": "pu_base",
    "Taxa Compra Manha": "taxa_compra",
}


def _url_do_csv() -> str:
    r = requests.get(CKAN, headers=HEADERS, timeout=60)
    r.raise_for_status()
    recursos = r.json()["result"]["resources"]
    csvs = [x for x in recursos if (x.get("format") or "").upper() == "CSV"]
    if not csvs:
        raise ValueError("o pacote do Tesouro Transparente não expõe recurso CSV")
    return csvs[0]["url"]


def fetch() -> pd.DataFrame:
    """Baixa o CSV inteiro e devolve só o Tesouro IPCA+ dentro da janela."""
    r = requests.get(_url_do_csv(), headers=HEADERS, timeout=300)
    r.raise_for_status()
    # O arquivo é latin-1, separado por ponto e vírgula, com vírgula decimal.
    df = pd.read_csv(io.BytesIO(r.content), sep=";", encoding="latin-1", decimal=",")
    df.columns = [c.strip() for c in df.columns]

    df = df[df["Tipo Titulo"].str.strip() == TITULO].copy()
    for c in ("Data Vencimento", "Data Base"):
        df[c] = pd.to_datetime(df[c], format="%d/%m/%Y")
    df = df[(df["Data Base"] >= START) & (df["Data Base"] <= END)]

    out = df[list(COLUNAS)].rename(columns=COLUNAS)

    # Spread negativo não existe: é erro da fonte. Descartar é seguro porque são
    # pouquíssimas linhas — a guarda garante que continue sendo verdade se a
    # fonte mudar.
    ruim = out.pu_compra < out.pu_venda
    if ruim.sum() > MAX_SPREAD_NEGATIVO:
        raise ValueError(
            f"{int(ruim.sum())} pregões com spread negativo — não é mais glitch "
            f"isolado, e a convenção de compra e venda precisa ser reexaminada"
        )
    out = out[~ruim]
    return out.sort_values(["maturity", "date"]).reset_index(drop=True)


def build(out_dir: Path) -> pd.DataFrame:
    df = fetch()
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "tesouro_ipca.parquet", index=False)
    return df


def validate(out_dir: Path) -> list[str]:
    path = out_dir / "tesouro_ipca.parquet"
    if not path.exists():
        return [f"{path} não existe"]
    df = pd.read_parquet(path)

    problemas = []
    if df.empty:
        return ["nenhuma cotação de Tesouro IPCA+ na janela"]

    # A guarda que sustenta a série: todo mês do estudo tem pregão.
    meses = set(df.date.dt.to_period("M"))
    faltando = [str(m) for m in pd.period_range("2006-01", "2025-12", freq="M")
                if m not in meses]
    if faltando:
        problemas.append(f"{len(faltando)} meses sem cotação: {faltando[:6]}")

    # Compra acima de venda, sempre: o spread fica com o Tesouro. Invertido,
    # o título passaria a render o que na verdade custa.
    if (df.pu_compra < df.pu_venda).any():
        n = int((df.pu_compra < df.pu_venda).sum())
        problemas.append(f"{n} pregões com PU de compra abaixo do de venda — "
                         f"a coleta deveria tê-los descartado")
    if (df[["pu_compra", "pu_venda", "pu_base"]] <= 0).to_numpy().any():
        problemas.append("preço unitário zero ou negativo")
    return problemas
