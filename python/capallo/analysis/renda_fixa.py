"""Tesouro IPCA+ como régua, e a lição que ele dá sobre sequência.

O CDI responde "o risco da bolsa compensou contra o juro nominal?". Esta perna
responde à versão mais dura da mesma pergunta: compensou contra um **retorno real
contratado**? Em 2006 o investidor brasileiro podia travar IPCA + 8% ao ano por
dezoito anos, e é difícil imaginar régua mais exigente que essa.

## O resultado é uma armadilha, e a armadilha é o assunto

O Tesouro IPCA+ longo entrega **6,85% ao ano real** no período — mais que os ETFs
de 2006, quase o que o ACWI global entregou. E entrega **1,41 real de poder de
compra por real aportado**, que é **menos que o CDI**.

Os dois números não se contradizem: eles medem coisas diferentes. O primeiro é
ponderado por tempo, o segundo por dinheiro. A distância entre eles é a
**sequência** dos retornos:

| período | Tesouro IPCA+ | CDI | Capital Allocators |
|---|---|---|---|
| 2006-2012 | **+20,1%** a.a. | +5,8% | −0,5% |
| 2013-2018 | +1,6% | +4,2% | +13,8% |
| 2019-2025 | **−0,6%** | +3,4% | +14,6% |

O título longo teve seu melhor período quando o investidor do estudo ainda quase
não tinha dinheiro aplicado, e o pior quando já tinha quase tudo. Quem acumula não
recebe o retorno médio do ativo — recebe o retorno dos anos em que o patrimônio
dele era grande.

## E isso corta para os dois lados

A tabela acima é também uma ressalva contra o número principal do estudo. Os
Capital Allocators são a **imagem espelhada** do Tesouro IPCA+: fracos em
2006-2012, fortes depois. O placar de 3,75x se beneficiou de uma sequência
favorável exatamente na mesma medida em que o do título sofreu de uma desfavorável.

Não é acusação de sorte, é definição: numa carteira com aporte mensal, quando o
retorno chega importa tanto quanto quanto ele foi. O teste de janelas de início já
mostrava isso por outro caminho — o prêmio dos allocators cresce com entradas mais
tardias. Aqui aparece o mecanismo.

⚠️ E a volatilidade não é detalhe: **21,8% ao ano, com drawdown máximo de −35,4%**.
É risco de ação, num título público. Vem da duration — a série carrega vencimentos
de 18 a 25 anos —, e é exatamente o que `docs/decisions.md` previa ao adiar esta
perna: *"introduz duration e marcação a mercado"*.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from capallo.analysis import metrics as m
from capallo.analysis.scoreboard import _deflator, _load_result, evaluate

TESOURO = "tesouro_ipca"

#: Cortes usados para exibir a sequência. Escolhidos como terços aproximados da
#: janela, **antes** de olhar o resultado de qualquer perna — o mesmo cuidado que
#: as janelas de crise recebem em `analysis.crises`.
PERIODOS = (("2006-01", "2012-12"), ("2013-01", "2018-12"), ("2019-01", "2025-12"))


def _real_mensal(path: Path, curated: Path) -> pd.Series:
    df = _load_result(path)
    r = m.monthly_returns(df.value, df.contribution)
    ipca = (1 / _deflator(curated)).pct_change().reindex(r.index)
    return ((1 + r) / (1 + ipca) - 1).dropna()


def sequencia(resultados: Path, curated: Path,
              estrategias: tuple[str, ...] = (TESOURO, "cdi", "capital_allocators")
              ) -> pd.DataFrame:
    """Retorno real anualizado em cada terço da janela.

    É a tabela que explica por que retorno alto e resultado ruim convivem: um é
    ponderado por tempo, o outro por dinheiro, e a sequência é a diferença.
    """
    linhas = []
    for nome in estrategias:
        s = _real_mensal(resultados / f"{nome}.csv", curated)
        linha = {"estrategia": nome}
        for ini, fim in PERIODOS:
            janela = s.loc[ini:fim]
            linha[f"{ini[:4]}-{fim[:4]}"] = (1 + janela).prod() ** (12 / len(janela)) - 1
        linhas.append(linha)
    return pd.DataFrame(linhas)


def tempo_contra_dinheiro(resultados: Path, curated: Path,
                          estrategias: tuple[str, ...] = (
                              "capital_allocators", "modern_alternative",
                              TESOURO, "passive_etfs", "cdi")) -> pd.DataFrame:
    """Retorno ponderado por tempo ao lado do resultado ponderado por dinheiro.

    Quando as duas colunas discordam de ordem, quem discorda é a sequência — e é
    a segunda que descreve o que o investidor levou para casa.
    """
    linhas = []
    for nome in estrategias:
        d = evaluate(resultados / f"{nome}.csv", curated)
        linhas.append({
            "estrategia": nome,
            "real_aa": d["retorno_real_aa"],
            "reais_por_real": d["reais_por_real"],
            "volatilidade": d["volatilidade"],
            "max_drawdown": d["max_drawdown"],
        })
    out = pd.DataFrame(linhas)
    out["posto_por_tempo"] = out.real_aa.rank(ascending=False).astype(int)
    out["posto_por_dinheiro"] = out.reais_por_real.rank(ascending=False).astype(int)
    return out


def inversoes(tabela: pd.DataFrame) -> list[str]:
    """Onde o ranking por tempo e o por dinheiro discordam."""
    return [
        f"{r.estrategia}: {r.real_aa:.2%} ao ano a coloca em {r.posto_por_tempo}º por "
        f"tempo, mas {r.reais_por_real:.2f}x a coloca em {r.posto_por_dinheiro}º por "
        f"dinheiro"
        for _, r in tabela.iterrows() if r.posto_por_tempo != r.posto_por_dinheiro
    ]
