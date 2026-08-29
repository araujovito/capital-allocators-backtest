"""Modern Alternative: e se o investidor de 2006 pudesse comprar o de hoje?

Terceiro e último tipo de experimento da §7. Os dois anteriores comparam a gestão
ativa com o que existia em 2006 — o ETF (Historical Reality) e o índice que ele
replica (Index Benchmark). Este pergunta outra coisa: **o allocator vence o
produto que um investidor brasileiro compraria hoje?**

O contrafactual é um fundo global de índice: o mundo inteiro ponderado por
capitalização, num ticker só, em reais, sem conta no exterior. Em 2006 isso não
existia para ele; hoje é a recomendação padrão.

## Por que este é o benchmark mais duro do estudo

A perna passiva do placar principal tem quatro ETFs regionais em **pesos iguais**,
o que espelha a construção da perna ativa — oito empresas, duas por região. É uma
comparação justa, e é uma comparação que subponderou os Estados Unidos justamente
no período em que os Estados Unidos ganharam de todo mundo.

O ACWI não faz isso: ele carrega o peso de mercado de cada região a cada data. Nos
vinte anos da janela, isso significa uma carteira cada vez mais americana — não
por escolha nossa, e sim porque foi o que o mercado fez. Então este experimento
enfrenta a tese do estudo com a alocação que mais se beneficiou do período.

**Não há lookahead na regra do índice.** Os pesos de 2006 são os de 2006. O que é
anacrônico é o acesso ao veículo, e é exatamente isso que o contrafactual quer
medir.

## O que fica declarado como premissa

A taxa de administração do produto moderno (`TER_MODERN`) é premissa, não dado
coletado — ver `transform.build_indices`. `sensibilidade_da_taxa()` refaz o
experimento inteiro em três alíquotas para que a conclusão não dependa dela.

⚠️ Resultados dos três tipos de experimento **nunca se misturam** (§7). Esta
tabela fica ao lado do placar principal, não no lugar dele.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

from capallo.analysis import metrics as m
from capallo.analysis.scoreboard import _load_result, evaluate, win_rate

ATIVA = "capital_allocators"
MODERNA = "modern_alternative"

#: As três referências passivas do estudo, uma por tipo de experimento. Ficam
#: juntas só nesta tabela, e com o tipo escrito ao lado de cada uma.
REFERENCIAS = (
    ("Modern Alternative — ACWI global", MODERNA, "Modern Alternative (§7)"),
    ("Índices regionais, pesos iguais", "passive_indices", "Index Benchmark (§7)"),
    ("ETFs de 2006, pesos iguais", "passive_etfs", "Historical Reality"),
    ("CDI", "cdi", "custo de oportunidade"),
)

HORIZONTES = (1, 3, 5, 10)


def comparar(resultados: Path, curated: Path) -> pd.DataFrame:
    """A carteira ativa contra cada referência passiva, com o risco ao lado."""
    linhas = []
    for rotulo, arquivo, tipo in (("Capital Allocators", ATIVA, "carteira ativa"),
                                  *REFERENCIAS):
        d = evaluate(resultados / f"{arquivo}.csv", curated)
        linhas.append({
            "estrategia": rotulo,
            "experimento": tipo,
            "reais_por_real": d["reais_por_real"],
            "real_aa": d["retorno_real_aa"],
            "volatilidade": d["volatilidade"],
            "max_drawdown": d["max_drawdown"],
            "sharpe": d["sharpe"],
        })
    return pd.DataFrame(linhas)


def premio_sobre_a_alternativa_moderna(resultados: Path, curated: Path) -> dict:
    """Prêmio, risco e frequência de vitória contra o contrafactual moderno.

    Frequência importa mais aqui que nos outros experimentos: o ACWI é uma carteira
    só, sem a diversificação regional forçada das outras pernas, então a diferença
    entre "venceu no acumulado" e "venceu com regularidade" é maior.
    """
    a = evaluate(resultados / f"{ATIVA}.csv", curated)
    b = evaluate(resultados / f"{MODERNA}.csv", curated)
    return {
        "premio_pp": (a["retorno_real_aa"] - b["retorno_real_aa"]) * 100,
        "vol_extra_pp": (a["volatilidade"] - b["volatilidade"]) * 100,
        "delta_sharpe": a["sharpe"] - b["sharpe"],
        "delta_maxdd_pp": (a["max_drawdown"] - b["max_drawdown"]) * 100,
        "vitorias": {
            anos: win_rate(resultados / f"{ATIVA}.csv",
                           resultados / f"{MODERNA}.csv", anos)
            for anos in HORIZONTES
        },
    }


def pior_periodo_relativo(resultados: Path, curated: Path) -> dict:
    """A pior janela de 5 anos da carteira ativa contra o contrafactual moderno.

    O placar acumulado é a experiência de quem nunca desistiu. Esta linha é a
    experiência de quem entrou na pior hora possível — e é ela que decide se a
    estratégia é sustentável por uma pessoa de verdade.
    """
    ra = m.rolling_window_returns(
        m.monthly_returns(*_partes(resultados / f"{ATIVA}.csv")), 5)
    rb = m.rolling_window_returns(
        m.monthly_returns(*_partes(resultados / f"{MODERNA}.csv")), 5)
    comum = ra.index.intersection(rb.index)
    dif = (ra.loc[comum] - rb.loc[comum]) * 100
    return {
        "pior_janela": str(dif.idxmin()),
        "pior_diferenca_pp": float(dif.min()),
        "melhor_janela": str(dif.idxmax()),
        "melhor_diferenca_pp": float(dif.max()),
        "janelas": len(dif),
    }


def _partes(path: Path):
    df = _load_result(path)
    return df.value, df.contribution


def sensibilidade_da_taxa(
    curated: Path, engine_dir: Path, strategies: Path,
    taxas: tuple[float, ...] = (0.0006, 0.0030, 0.0050),
) -> pd.DataFrame:
    """Refaz o experimento inteiro em cada taxa de administração.

    Reconstrói o painel e roda o motor de novo a cada alíquota — em vez de
    descontar a taxa do resultado por fora — porque o aporte mensal interage com o
    nível da série, e a aproximação analítica esconderia essa interação.
    """
    from capallo.analysis.sensitivity import _binario, _rodar
    from capallo.transform.build_indices import build as build_indices
    from capallo.transform.dataset import export

    exe = _binario(engine_dir)
    ativa = evaluate(Path("data/results") / f"{ATIVA}.csv", curated)["retorno_real_aa"]

    linhas = []
    for ter in taxas:
        build_indices(curated, ter_modern=ter)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            dados, saida = tmp / "engine", tmp / f"{MODERNA}.csv"
            export(curated, dados)
            _rodar(exe, strategies / f"{MODERNA}.toml", dados, saida)
            d = evaluate(saida, curated)
        linhas.append({
            "ter": ter,
            "moderna_aa": d["retorno_real_aa"],
            "reais_por_real": d["reais_por_real"],
            "premio_da_ativa_pp": (ativa - d["retorno_real_aa"]) * 100,
        })

    # Restaura a taxa base: o parquet não pode ficar com a última do laço.
    from capallo.transform.build_indices import TER_MODERN

    build_indices(curated, ter_modern=TER_MODERN)
    return pd.DataFrame(linhas)
