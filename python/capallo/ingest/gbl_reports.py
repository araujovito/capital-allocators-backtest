"""Proventos do GBL, extraídos dos relatórios anuais da companhia.

Nenhuma fonte gratuita de mercado cobria a janela do estudo: onvista dá seis anos,
stockanalysis cinco, wallstreet-online começa em 2021. A companhia, porém, publica
o dado sobre si mesma — e o arquivo de relatórios em `gbl.com` vai até 2006.

O que resolve é a tabela de **dez anos** que aparece no fim de cada relatório
anual: dois documentos cobrem vinte anos sem sobreposição.

- `annual_report_2025.pdf` → exercícios 2025 a 2016
- `GBL_RA2015_EN_LR.pdf`   → exercícios 2015 a 2006

A linha é `Gross dividend (in EUR)` seguida de dez valores em **ordem decrescente
de ano**, o que o parser assume e verifica.

⚠️ O valor é o dividendo **bruto do exercício**, pago em maio do ano seguinte —
a Assembleia de maio de 2025 aprovou o dividendo do exercício de 2024. O
alinhamento com a data-ex é responsabilidade de quem monta o total return, não do
coletor.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests
from pypdf import PdfReader

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}

#: (URL, ano mais recente da tabela de dez anos daquele relatório).
REPORTS: tuple[tuple[str, int], ...] = (
    ("https://www.gbl.com/en/media/4293/annual_report_2025.pdf", 2025),
    ("https://www.gbl.com/en/media/2754/GBL_RA2015_EN_LR.pdf", 2015),
)

ROW_LABEL = re.compile(r"Gross dividend\s*\(in EUR\)\s*(.+)", re.I)
YEARS_PER_TABLE = 10


def download(url: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / url.rsplit("/", 1)[-1]
    if dest.exists() and dest.stat().st_size > 100_000:
        return dest
    r = requests.get(url, headers=HEADERS, timeout=300)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def extract(pdf: Path, latest_year: int) -> pd.DataFrame:
    """Lê a linha `Gross dividend (in EUR)` da tabela de dez anos."""
    reader = PdfReader(str(pdf))
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:  # página com fonte que o extrator não abre
            continue
        for line in (l.strip() for l in text.splitlines() if l.strip()):
            m = ROW_LABEL.match(line)
            if not m:
                continue
            values = [float(v) for v in re.findall(r"\d+[.,]\d+", m.group(1).replace(",", "."))]
            if len(values) != YEARS_PER_TABLE:
                continue
            years = list(range(latest_year, latest_year - YEARS_PER_TABLE, -1))
            return pd.DataFrame({"ticker": "GBLB", "fiscal_year": years, "gross_dividend": values})
    raise LookupError(f"linha de dividendo não encontrada em {pdf.name}")


def build(out_dir: Path, raw_dir: Path) -> pd.DataFrame:
    frames = [extract(download(url, raw_dir), year) for url, year in REPORTS]
    df = pd.concat(frames, ignore_index=True).drop_duplicates("fiscal_year")
    df = df.sort_values("fiscal_year").reset_index(drop=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "be_dividends.parquet", index=False)
    return df


def validate(out_dir: Path) -> list[str]:
    path = out_dir / "be_dividends.parquet"
    if not path.exists():
        return [f"{path} não existe"]
    df = pd.read_parquet(path)
    problems = []
    esperados = set(range(2006, 2026))
    faltando = esperados - set(df.fiscal_year)
    if faltando:
        problems.append(f"exercícios ausentes: {sorted(faltando)}")
    if (df.gross_dividend <= 0).any():
        problems.append("dividendo não positivo")
    # Salto acima de 3x entre anos consecutivos indica linha lida da coluna errada.
    razao = df.sort_values("fiscal_year").gross_dividend.pct_change().abs()
    if (razao > 2).any():
        problems.append("variação anual implausível — possível desalinhamento de coluna")
    return problems
