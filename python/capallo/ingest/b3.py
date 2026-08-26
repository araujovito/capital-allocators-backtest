"""Coletor da B3 — arquivo histórico COTAHIST.

Fonte oficial e gratuita. A B3 publica um arquivo por ano, em largura fixa, e é
por isso a fonte mais acessível do projeto: enquanto emissores e bolsas migraram
para front-ends que cifram ou renderizam o dado no cliente, a B3 continua
publicando um .ZIP como em 1998.

⚠️ COTAHIST traz **preço bruto**, sem ajuste por proventos, splits ou
bonificações. Ele resolve a série de preços, não o total return.

Layout (posições 1-indexed, conforme o manual da B3):
    1-2     TIPREG   tipo de registro (01 = cotação)
    3-10    DATA     AAAAMMDD
    11-12   CODBDI   02 = lote padrão, 14 = certificado de investimento (ETF)
    13-24   CODNEG   código de negociação
    25-27   TPMERC   010 = mercado à vista
    109-121 PREULT   preço de fechamento, 2 decimais implícitos
    153-170 QUATOT   quantidade total negociada
    171-188 VOLTOT   volume financeiro, 2 decimais implícitos
    211-217 FATCOT   fator de cotação (1 ou 1000)
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

URL = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.ZIP"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}

#: Cotações do mercado à vista. Dois CODBDI interessam:
#: 02 = lote padrão (ações) e 14 = certificado de investimento, que é como a B3
#: classifica ETF. PIBB11 aparece sob 14 a vida quase toda e migra para 02 em 2019
#: — filtrar só por 02 perderia 13 dos 20 anos da série.
CODBDI_ACEITOS = {"02", "14"}
TPMERC_VISTA = "010"


def download_year(year: int, raw_dir: Path) -> Path:
    """Baixa o arquivo anual, reaproveitando o que já estiver em disco."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / f"COTAHIST_A{year}.ZIP"
    if dest.exists() and dest.stat().st_size > 1_000_000:
        return dest
    r = requests.get(URL.format(year=year), headers=HEADERS, timeout=300)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def parse_year(path: Path, tickers: set[str]) -> pd.DataFrame:
    """Extrai os tickers pedidos de um arquivo anual."""
    rows = []
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.upper().endswith(".TXT"))
        with z.open(name) as fh:
            for raw in io.TextIOWrapper(fh, encoding="latin-1"):
                if raw[0:2] != "01":
                    continue
                if raw[10:12] not in CODBDI_ACEITOS or raw[24:27] != TPMERC_VISTA:
                    continue
                code = raw[12:24].strip()
                if code not in tickers:
                    continue
                fatcot = int(raw[210:217] or 1)
                rows.append(
                    {
                        "date": raw[2:10],
                        "ticker": code,
                        # 2 decimais implícitos; FATCOT diz a quantas ações o preço se refere
                        "close": int(raw[108:121]) / 100 / (fatcot or 1),
                        "volume": int(raw[170:188]) / 100,
                        "trades": int(raw[152:170]),
                    }
                )
    if not rows:
        return pd.DataFrame(columns=["date", "ticker", "close", "volume", "trades"])
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    # Em 2019 o PIBB11 aparece sob os dois CODBDI; um pregão nunca tem duas cotações.
    return df.drop_duplicates(["ticker", "date"])


def fetch(tickers: set[str], years: range, raw_dir: Path) -> pd.DataFrame:
    frames = [parse_year(download_year(y, raw_dir), tickers) for y in years]
    df = pd.concat(frames, ignore_index=True)
    return df.sort_values(["ticker", "date"]).reset_index(drop=True)


BR_TICKERS = {"ITSA4", "BRAP4", "PIBB11"}
STUDY_YEARS = range(2006, 2026)


def build(out_dir: Path, raw_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = fetch(BR_TICKERS, STUDY_YEARS, raw_dir)
    df.to_parquet(out_dir / "b3_prices.parquet", index=False)
    return {t: int(n) for t, n in df.groupby("ticker").size().items()}


def validate(out_dir: Path) -> list[str]:
    path = out_dir / "b3_prices.parquet"
    if not path.exists():
        return [f"{path} não existe"]

    df = pd.read_parquet(path)
    problems: list[str] = []
    counts = df.groupby("ticker").size()

    faltando = BR_TICKERS - set(counts.index)
    if faltando:
        problems.append(f"tickers ausentes: {sorted(faltando)}")

    # Os três negociam na mesma bolsa: o número de pregões tem de bater entre eles.
    if len(set(counts.values)) > 1:
        problems.append(f"contagem de pregões diverge entre tickers: {dict(counts)}")

    for ticker, g in df.groupby("ticker"):
        if g.close.isna().any() or (g.close <= 0).any():
            problems.append(f"{ticker}: preço nulo ou não positivo")
        if g.date.duplicated().any():
            problems.append(f"{ticker}: datas duplicadas")
        por_ano = g.groupby(g.date.dt.year).size()
        ruins = por_ano[por_ano < 200]
        if len(ruins):
            problems.append(f"{ticker}: anos com menos de 200 pregões: {dict(ruins)}")

    return problems
