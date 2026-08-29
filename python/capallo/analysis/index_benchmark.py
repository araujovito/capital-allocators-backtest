"""Index Benchmark: o allocator venceu o mercado, ou venceu o produto?

O experimento da §7 troca o ETF pelo **índice** que ele replica e refaz a
comparação. A diferença entre os dois é o que custa embrulhar um mercado num
fundo — taxa de administração, tracking error, amostragem — e a pergunta é se o
Allocator Premium sobrevive quando esse custo sai da conta.

É o teste mais desconfortável que o estudo pode fazer contra a própria tese, e por
isso ele existe: o placar principal compara gestão ativa com **o produto que dava
para comprar em 2006**, o que é a pergunta certa para um investidor, mas não é a
pergunta "gestão ativa bate o mercado". Esta é.

⚠️ **Os dois tipos de experimento nunca se misturam** (§7). O placar principal
continua sendo o Historical Reality, com ETFs. Esta tabela fica ao lado, não no
lugar.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from capallo.analysis.scoreboard import evaluate

#: Região → (allocators, ETF, índice). A perna ativa é a mesma nas duas colunas:
#: o que muda é só com quem ela é comparada.
TRIOS = (
    ("Brasil", "br_allocators", "br_etf", "br_index"),
    ("EUA", "us_allocators", "us_etf", "us_index"),
    ("Europa", "eu_allocators", "eu_etf", "eu_index"),
    ("Japão", "jp_allocators", "jp_etf", "jp_index"),
    ("Global", "capital_allocators", "passive_etfs", "passive_indices"),
)


def comparar(resultados: Path, curated: Path) -> pd.DataFrame:
    """Prêmio contra o ETF e contra o índice, lado a lado.

    `custo_do_produto_pp` é quanto o índice rendeu a mais que o ETF da mesma
    região — e é exatamente quanto o prêmio encolhe ao trocar de referência.
    """
    linhas = []
    for regiao, alloc, etf, indice in TRIOS:
        a = evaluate(resultados / f"{alloc}.csv", curated)["retorno_real_aa"]
        e = evaluate(resultados / f"{etf}.csv", curated)["retorno_real_aa"]
        i = evaluate(resultados / f"{indice}.csv", curated)["retorno_real_aa"]
        linhas.append({
            "regiao": regiao,
            "alloc_aa": a,
            "etf_aa": e,
            "indice_aa": i,
            "premio_vs_etf_pp": (a - e) * 100,
            "premio_vs_indice_pp": (a - i) * 100,
            "custo_do_produto_pp": (i - e) * 100,
        })
    return pd.DataFrame(linhas)


def veredito(tabela: pd.DataFrame) -> list[str]:
    """Onde a conclusão muda de sinal ao trocar o ETF pelo índice.

    Um prêmio que sobrevive à troca é sobre gestão de capital. Um que não
    sobrevive era sobre custo de produto — e a diferença entre as duas frases é
    a razão de o experimento existir.
    """
    frases = []
    for _, r in tabela.iterrows():
        vira = (r.premio_vs_etf_pp > 0) != (r.premio_vs_indice_pp > 0)
        if vira:
            frases.append(
                f"{r.regiao}: o prêmio inverte de sinal — {r.premio_vs_etf_pp:+.2f} p.p. "
                f"contra o ETF, {r.premio_vs_indice_pp:+.2f} contra o índice"
            )
        elif r.custo_do_produto_pp < 0:
            frases.append(
                f"{r.regiao}: o ETF **superou** o próprio índice em "
                f"{-r.custo_do_produto_pp:.2f} p.p. ao ano, e a troca aumenta o prêmio"
            )
    return frases
