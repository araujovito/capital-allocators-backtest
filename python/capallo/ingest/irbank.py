"""Coletor IR Bank (irbank.net) — proventos das companhias japonesas.

Fonte japonesa, gratuita e sem chave. Encontrada depois de o RI da Mitsubishi
responder 403 e o da Mitsui 404, inclusive com navegador.

A coluna **分割調整** entrega o dividendo por ação **já ajustado por
desdobramento**, que é exatamente o campo necessário: as séries de preço do
Kabutan também são ajustadas por desdobramento, então os dois lados falam da
mesma unidade.

⚠️ **Esta fonte não fechou.** Duas limitações, ambas verificadas:

1. **Cobertura começa em 2010.** Os exercícios de 2006 a 2009 não estão na página
   nem no CSV de download, que só traz cinco anos.
2. **O layout é um log de anúncios, não uma série anual.** Linhas referenciam mais
   de um exercício e usam `rowspan` de forma irregular. Mesmo com o normalizador de
   grade, parte das linhas sai desalinhada — e o número desalinhado é plausível,
   o que o torna perigoso. A guarda em `fetch_dividends` descarta essas linhas, e
   o que sobra não cobre a janela do estudo.

O módulo fica no repositório pelo normalizador de tabela, que é correto e
reutilizável, e como registro do que foi tentado.

Exercício social japonês: `2010年3月` significa o ano fiscal encerrado em março de
2010, ou seja, os proventos correm de abril/2009 a março/2010.
"""

from __future__ import annotations

import re

import pandas as pd
import requests
from lxml import html as LH

URL = "https://irbank.net/{code}/dividend"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}

TOKYO_CODES = ("8058", "8031")

#: A página não é uma série anual: é um **log de anúncios**. Cada exercício
#: aparece uma ou mais vezes, com 区分 igual a 実績 (realizado), 修正 (revisado) ou
#: 予想 (projetado no momento do anúncio). Filtrar só por 実績 devolve quatro anos.
#:
#: O valor correto de um exercício **já encerrado** é o do último anúncio dele —
#: aí a projeção já virou fato. Exercícios ainda em curso são descartados: usar
#: projeção da companhia seria colocar no backtest informação que não existia.
STATUS_FORECAST = "予想"

#: Valores admissíveis da coluna 区分. Qualquer outra coisa indica linha
#: desalinhada — ver a guarda em `fetch_dividends`.
VALID_STATUS = {"実績", "修正", "予想"}


def normalize_table(table) -> list[list[str]]:
    """Expande `rowspan` e `colspan` numa grade retangular.

    Sem isso o parse é silenciosamente errado, não quebrado: uma linha cuja
    primeira célula tem `rowspan` vem com menos `<td>`, e todas as colunas
    seguintes deslizam uma posição. O valor lido como "dividendo ajustado" acaba
    sendo o dividendo semestral da coluna anterior — um número plausível, na
    ordem de grandeza certa, e errado pela metade.
    """
    grid: dict[tuple[int, int], str] = {}
    for r, tr in enumerate(table.xpath(".//tr")):
        c = 0
        for cell in tr.xpath("./th|./td"):
            while (r, c) in grid:
                c += 1
            text = (cell.text_content() or "").strip()
            rs = int(cell.get("rowspan") or 1)
            cs = int(cell.get("colspan") or 1)
            for dr in range(rs):
                for dc in range(cs):
                    grid[(r + dr, c + dc)] = text
            c += cs
    if not grid:
        return []
    rows = max(k[0] for k in grid) + 1
    cols = max(k[1] for k in grid) + 1
    return [[grid.get((r, c), "") for c in range(cols)] for r in range(rows)]


def _to_float(value: str) -> float | None:
    v = (value or "").strip().replace(",", "")
    if not v or v in {"-", "－", "—"}:
        return None
    m = re.match(r"-?\d+(\.\d+)?", v)
    return float(m.group(0)) if m else None


def fetch_dividends(code: str) -> pd.DataFrame:
    """Dividendo anual por ação, ajustado por desdobramento."""
    r = requests.get(URL.format(code=code), headers=HEADERS, timeout=45)
    r.raise_for_status()
    doc = LH.fromstring(r.text)

    rows = []
    for table in doc.xpath("//table"):
        grid = normalize_table(table)
        if not grid:
            continue
        header = grid[0]
        if "年度" not in header or "分割調整" not in header:
            continue
        idx = {name: i for i, name in enumerate(header)}
        for cells in grid[1:]:
            if len(cells) < len(header):
                continue
            period = cells[idx["年度"]]
            m = re.match(r"(\d{4})年\s*(\d{1,2})月", period)
            if not m:
                continue
            rows.append(
                {
                    "ticker": code,
                    "fiscal_year_end": pd.Timestamp(int(m.group(1)), int(m.group(2)), 1)
                    + pd.offsets.MonthEnd(0),
                    "status": cells[idx["区分"]],
                    "dps_adjusted": _to_float(cells[idx["分割調整"]]),
                }
            )
        break

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.dropna(subset=["dps_adjusted"])

    # Guarda contra leitura silenciosamente errada. A coluna 区分 só admite três
    # valores; se vier outra coisa — um ano, por exemplo — a linha está desalinhada
    # e o número lido pertence a outra coluna. Descartar é obrigatório: o valor
    # errado é plausível (mesma ordem de grandeza) e não seria notado depois.
    df = df[df.status.isin(VALID_STATUS)]

    df = df.sort_values("fiscal_year_end").groupby("fiscal_year_end", as_index=False).last()
    today = pd.Timestamp.today().normalize()
    return df[df.fiscal_year_end <= today].sort_values("fiscal_year_end").reset_index(drop=True)


def build(out_dir) -> dict[str, int]:
    from pathlib import Path

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frames, counts = [], {}
    for code in TOKYO_CODES:
        df = fetch_dividends(code)
        frames.append(df)
        counts[code] = len(df)
    pd.concat(frames, ignore_index=True).to_parquet(
        out_dir / "jp_dividends.parquet", index=False
    )
    return counts
