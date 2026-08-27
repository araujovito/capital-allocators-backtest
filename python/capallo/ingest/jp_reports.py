"""Proventos de Mitsubishi (8058) e Mitsui (8031), lidos dos relatórios anuais.

Último buraco do estudo. As fontes de mercado não cobriram a janela: o IR Bank
entrega quatro exercícios confiáveis por empresa (2010-2013) depois das guardas
contra desalinhamento de coluna, e o Kabutan mistura dividendo com revisão de
resultado. A saída é a mesma que resolveu o GBL — **a companhia publica o dado
sobre si mesma**, na tabela de dez anos do relatório anual.

Duas particularidades, e as duas viraram guarda no código.

**A Mitsubishi bloqueia o Brasil.** `mitsubishicorp.com` devolve 403 do Akamai
para qualquer requisição desta rede, com ou sem cabeçalho de navegador, e também
sob Playwright — não é anti-bot, é geografia. Os PDFs vêm do Internet Archive,
que serve o mesmo arquivo. O snapshot é fixado por timestamp: captura sem
timestamp é redirecionada para a mais recente, que pode mudar, e uma delas está
truncada em 5 MB.

**Ambas desdobraram as ações em 2024**, depois da última leitura de preço do
estudo: a Mitsubishi 3:1 em 01/01/2024, a Mitsui 2:1 em julho de 2024. Os
relatórios anteriores ao desdobramento trazem o valor por ação antiga; os
posteriores reexpressam a série inteira. O fator **não é assumido**: é medido na
sobreposição entre um documento de cada lado do desdobramento e conferido contra
o que a companhia declara em nota. Se a medida discordar da nota, a coleta falha.

⚠️ O valor é o dividendo do **exercício fiscal encerrado em março**, não o
dividendo pago no ano-calendário. Casar com a data-ex é responsabilidade de quem
monta o total return.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
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

#: Desdobramentos de 2024, como as próprias companhias declaram em nota de rodapé.
#: Usados só para conferir o fator medido na sobreposição — nunca para produzi-lo.
SPLITS_2024 = {"8058": 3.0, "8031": 2.0}


@dataclass(frozen=True)
class Source:
    """Uma linha de dividendo em um relatório anual.

    `years` lista os exercícios **na ordem em que aparecem na linha**. É uma lista
    explícita, e não um intervalo, porque a Mitsubishi repete 2013 em duas colunas
    na transição de US GAAP para IFRS: um intervalo leria 2014 onde há 2013 e
    deslocaria toda a metade direita da tabela.

    `post_split` marca o documento publicado depois do desdobramento de 2024, que
    reexpressa a série inteira em ações novas.
    """

    ticker: str
    filename: str
    url: str
    label: str
    years: tuple[int, ...]
    post_split: bool = False


SOURCES: tuple[Source, ...] = (
    # Mitsui — relatórios servidos pelo próprio site.
    Source(
        "8031", "en_ar2015_all.pdf",
        "https://www.mitsui.com/jp/en/ir/library/report/__icsFiles/afieldfile/2015/12/25/en_ar2015_all.pdf",
        "Cash Dividends", tuple(range(2006, 2015)),
    ),
    Source(
        "8031", "en_ar2020_all.pdf",
        "https://www.mitsui.com/jp/en/ir/library/report/__icsFiles/afieldfile/2020/10/08/en_ar2020_all.pdf",
        "Cash Dividends", tuple(range(2014, 2021)),
    ),
    Source(
        "8031", "en_ir2022_all.pdf",
        "https://www.mitsui.com/jp/en/ir/library/report/__icsFiles/afieldfile/2022/09/20/en_ir2022_all_web.pdf",
        "Cash Dividends", tuple(range(2018, 2023)),
    ),
    Source(
        "8031", "mitsui_factdata2025.pdf",
        "https://www.mitsui.com/jp/en/ir/library/online2025/pdf/8_Gate4_FactData.pdf",
        "Dividend", tuple(range(2021, 2026)), post_split=True,
    ),
    # Mitsubishi — o site recusa o Brasil; os mesmos arquivos vêm do Internet Archive.
    Source(
        "8058", "mc_ar2015.pdf",
        "https://web.archive.org/web/20241123043930id_/"
        "https://www.mitsubishicorp.com/jp/en/ir/library/ar/assets_r24/pdf/areport/2015/all.pdf",
        "Cash dividends per share", tuple(range(2006, 2011)),
    ),
    Source(
        "8058", "mc_ar2020.pdf",
        "https://web.archive.org/web/20241123041519id_/"
        "https://www.mitsubishicorp.com/jp/en/ir/library/ar/assets_r24/pdf/areport/2020/all.pdf",
        "Cash dividends per share",
        (2011, 2012, 2013, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020),
    ),
    Source(
        "8058", "mc_ar2025.pdf",
        "https://web.archive.org/web/20260310051106id_/"
        "https://www.mitsubishicorp.com/jp/en/ir/library/ar/assets_r24/pdf/areport/2025/all.pdf",
        "Cash dividends per share", tuple(range(2016, 2026)), post_split=True,
    ),
)

def download(src: Source, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.filename
    if dest.exists() and dest.stat().st_size > 1_000_000:
        return dest
    r = requests.get(src.url, headers=HEADERS, timeout=900)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


#: Um número da linha da tabela; a vírgula é separador de milhar.
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")

#: O que pode aparecer entre o rótulo e a primeira coluna: marca de nota (`*4`),
#: unidade entre parênteses (`(yen, US dollars)`) e o pontilhado do sumário.
PREFIXO = re.compile(r"^(?:\*+\d*|\([^)]*\)|[.\s·…]+)+")


def _values(line: str, label: str) -> list[float] | None:
    """Números da linha, ou `None` se o que segue o rótulo não é uma tabela.

    O rótulo precisa terminar ali: `Dividend` não pode casar com `Dividend income`
    nem com `Dividend payout ratio`, que ficam na mesma página do fact book da
    Mitsui e têm contagem de colunas parecida o bastante para enganar a guarda.
    """
    resto = PREFIXO.sub("", line.strip()[len(label):], count=1)
    if not resto or not resto[0].isdigit():
        return None
    return [float(m.group().replace(",", "")) for m in NUMBER.finditer(resto)] or None


def extract(pdf: Path, src: Source) -> pd.DataFrame:
    """Lê a linha de dividendo, exigindo o número exato de colunas esperado.

    A tabela traz, além dos exercícios, uma coluna final em dólar. Aceitar a linha
    com `len(years)` ou `len(years) + 1` números e recusar qualquer outra contagem
    é a guarda contra ler a linha de outra tabela — ou a mesma linha com as colunas
    deslocadas, que foi o erro que quase passou na coleta japonesa anterior.
    """
    reader = PdfReader(str(pdf))
    if reader.is_encrypted:
        reader.decrypt("")
    n = len(src.years)
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:  # página com fonte que o extrator não abre
            continue
        for raw in text.splitlines():
            line = raw.strip()
            if not line.startswith(src.label):
                continue
            values = _values(line, src.label)
            if values is None or len(values) not in (n, n + 1):
                continue
            return pd.DataFrame(
                {"ticker": src.ticker, "fiscal_year": src.years,
                 "dps": values[:n], "source": src.filename,
                 "post_split": src.post_split}
            )
    raise LookupError(f"linha '{src.label}' com {n} colunas não encontrada em {pdf.name}")


def split_factor(df: pd.DataFrame, ticker: str) -> float:
    """Mede o desdobramento na sobreposição entre documentos dos dois lados dele.

    Sem sobreposição não há medida, e sem medida não há coleta: preferir falhar a
    aplicar o fator que a nota de rodapé afirma sem confirmação no dado.
    """
    g = df[df.ticker == ticker]
    antes = g[~g.post_split].groupby("fiscal_year").dps.median()
    depois = g[g.post_split].groupby("fiscal_year").dps.median()
    comum = antes.index.intersection(depois.index)
    if comum.empty:
        raise LookupError(f"{ticker}: nenhum exercício comum entre documentos antes e depois do split")
    razoes = antes[comum] / depois[comum]
    # As companhias arredondam o valor reexpresso (50 vira 16,67), então a razão
    # oscila na terceira casa. O que não pode oscilar é o fator em si.
    if razoes.max() - razoes.min() > 0.01:
        raise ValueError(f"{ticker}: razão instável na sobreposição — {razoes.round(3).to_dict()}")
    medido = float(razoes.median())
    declarado = SPLITS_2024[ticker]
    if abs(medido - declarado) > 0.02:
        raise ValueError(f"{ticker}: split medido {medido} contradiz o declarado {declarado}")
    return declarado


def build(out_dir: Path, raw_dir: Path) -> pd.DataFrame:
    bruto = pd.concat([extract(download(s, raw_dir), s) for s in SOURCES], ignore_index=True)

    partes = []
    for ticker in sorted(bruto.ticker.unique()):
        fator = split_factor(bruto, ticker)
        g = bruto[bruto.ticker == ticker].copy()
        # Tudo em ações novas: o preço do Kabutan já vem ajustado pelo desdobramento.
        g["dps_ajustado"] = g.dps.where(g.post_split, g.dps / fator)
        partes.append(g)

    df = pd.concat(partes, ignore_index=True)
    conflitos = conferir_sobreposicao(df)
    if conflitos:
        raise ValueError("documentos discordam: " + "; ".join(conflitos))

    # Onde há mais de uma leitura, fica a da companhia depois do desdobramento:
    # é ela que arredonda o valor reexpresso, e é dela que o mercado se lembra.
    # Dividir 50 por 3 daria 16,6667 onde a Mitsubishi publica 16,67.
    escolha = df.sort_values("post_split").groupby(["ticker", "fiscal_year"]).last()
    final = (escolha.reset_index()[["ticker", "fiscal_year", "dps_ajustado"]]
                    .rename(columns={"dps_ajustado": "dps_jpy"})
                    .merge(df.groupby(["ticker", "fiscal_year"], as_index=False)
                             .source.nunique().rename(columns={"source": "fontes"}),
                           on=["ticker", "fiscal_year"])
                    .sort_values(["ticker", "fiscal_year"])
                    .reset_index(drop=True))
    out_dir.mkdir(parents=True, exist_ok=True)
    final.to_parquet(out_dir / "jp_dividends.parquet", index=False)
    return final


def conferir_sobreposicao(df: pd.DataFrame, tol: float = 0.01) -> list[str]:
    """Exercícios lidos em mais de um relatório precisam bater.

    É a checagem que sustenta a coleta inteira: quatro documentos da Mitsui e três
    da Mitsubishi se sobrepõem de propósito, e coluna deslocada em qualquer um
    deles aparece aqui como divergência.
    """
    problemas = []
    for (ticker, ano), g in df.groupby(["ticker", "fiscal_year"]):
        vs = g.dps_ajustado.round(4).unique()
        if len(vs) > 1 and (vs.max() - vs.min()) > tol * max(abs(vs.max()), 1.0):
            fontes = ", ".join(f"{s}={v:g}" for s, v in zip(g.source, g.dps_ajustado))
            problemas.append(f"{ticker} {ano}: {fontes}")
    return problemas


def validate(out_dir: Path) -> list[str]:
    path = out_dir / "jp_dividends.parquet"
    if not path.exists():
        return [f"{path} não existe"]
    df = pd.read_parquet(path)
    problemas = []
    for ticker in ("8058", "8031"):
        anos = set(df[df.ticker == ticker].fiscal_year)
        faltando = set(range(2006, 2026)) - anos
        if faltando:
            problemas.append(f"{ticker}: exercícios ausentes {sorted(faltando)}")
    if (df.dps_jpy <= 0).any():
        problemas.append("dividendo não positivo")
    return problemas
