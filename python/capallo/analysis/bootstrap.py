"""Quanto do prêmio sobrevive a uma história diferente da que aconteceu.

O estudo tem um resultado e **uma** amostra: os 240 meses que existiram. A
pergunta adversarial natural é quanto do prêmio de +3,66 p.p. é sinal e quanto é
a mão que a história sorteou. Este módulo responde com dois testes, e eles
respondem a **coisas diferentes** — confundi-los seria pior que não fazê-los.

## Teste 1 — embaralhar a ordem: o que a sequência decide

Reordena os mesmos 240 meses. É a resposta direta à ressalva que o Tesouro IPCA+
expôs: o placar de 3,75x se beneficiou de retornos fracos no começo e fortes no
fim, quando o patrimônio já era grande.

O resultado tem uma metade **analítica** e uma **empírica**, e vale separar:

- O retorno anualizado é a média geométrica dos retornos mensais, e média
  geométrica **não depende da ordem**. Então o prêmio em pontos ao ano é
  *exatamente* invariante a qualquer reordenação — não aproximadamente, não com
  desvio pequeno: idêntico. Isso não é achado do bootstrap; é aritmética, e o
  bootstrap serve para conferir que o código faz o que a aritmética manda.
- O **múltiplo por real aportado** não é invariante. Ele pondera por dinheiro, e
  dinheiro é o que a sequência move. É aqui que a incerteza aparece.

A conclusão que sai daí é limpa: **a ressalva de sequência atinge o placar de
3,75x, não o prêmio de +3,66 p.p.** São afirmações diferentes e o estudo passa a
distinguir as duas.

## Teste 2 — reamostrar com reposição: o que a amostra decide

Sorteia blocos de meses **com reposição**, formando histórias que poderiam ter
acontecido a partir dos mesmos regimes. Aqui a média geométrica muda, porque o
conjunto de meses muda — e é este o teste de significância de verdade.

Blocos, e não meses soltos, porque retorno mensal tem memória: volatilidade se
agrupa e regimes duram. Sortear mês a mês fabricaria uma série sem 2008 e sem
2020 como *eventos*, e superestimaria a estabilidade de tudo.

## A escolha que decide se o teste presta

**Todas as pernas são reamostradas com os mesmos índices.** Se cada estratégia
sorteasse seus próprios meses, a correlação entre elas seria destruída, os
allocators de um mês bom encontrariam o ETF de um mês ruim e a distribuição do
prêmio ficaria larga por artefato. O bootstrap é do **calendário**, não das
séries: sorteia-se qual mês da história cada período é, e todas as pernas vivem
aquele mesmo mês.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from capallo.analysis.renda_fixa import _real_mensal

#: Pernas trazidas para o teste. A ordem importa só para leitura.
PERNAS = ("capital_allocators", "passive_etfs", "modern_alternative", "cdi")

#: Tamanho de bloco em meses. Um ano preserva o ciclo anual e o agrupamento de
#: volatilidade; a sensibilidade a essa escolha é medida por `sensibilidade_do_bloco`.
BLOCO = 12

#: Sorteios por experimento. Alto o bastante para o percentil de 5% ser estável.
SORTEIOS = 4000


def retornos_reais(resultados: Path, curated: Path,
                   pernas: tuple[str, ...] = PERNAS) -> pd.DataFrame:
    """Retorno real mensal de cada perna, num calendário comum.

    O calendário comum é o requisito do teste: reamostrar exige que a linha `t`
    de todas as pernas seja o **mesmo mês** da história.
    """
    series = {n: _real_mensal(resultados / f"{n}.csv", curated) for n in pernas}
    df = pd.DataFrame(series).dropna()
    if df.empty:
        raise ValueError("as pernas não compartilham nenhum mês")
    return df


def simular(retornos: np.ndarray, aporte: float = 1.0) -> tuple[float, float]:
    """Aporte constante em termos reais, e o que ele vira.

    Devolve `(reais por real aportado, retorno real anualizado)`. O aporte entra
    no início do mês e rende o mês inteiro, que é a convenção do motor.
    """
    patrimonio = 0.0
    for r in retornos:
        patrimonio = (patrimonio + aporte) * (1.0 + r)
    aportado = aporte * len(retornos)
    anualizado = float(np.prod(1.0 + retornos)) ** (12 / len(retornos)) - 1
    return patrimonio / aportado, anualizado


def _indices_em_blocos(n: int, bloco: int, rng: np.random.Generator,
                       com_reposicao: bool) -> np.ndarray:
    """Índices de meses formados por blocos contíguos.

    **Com reposição** os blocos são circulares — o que passa do fim volta ao
    começo — para que todo mês tenha a mesma chance de ser sorteado. Sem isso as
    pontas da janela entrariam menos, e 2008 e 2025 ficariam sub-representados por
    acidente de borda.

    **Sem reposição** o resultado precisa ser uma permutação **exata** dos meses,
    e é aqui que a primeira versão errou: blocos circulares de tamanho fixo não
    ladrilham 239 meses, então o corte final duplicava alguns meses e descartava
    outros. O prêmio, que deveria ser idêntico sob reordenação, saía 0,38 p.p.
    diferente — a checagem de invariância existe justamente para pegar isso, e
    pegou. Aqui a janela é **particionada** em blocos contíguos (o último menor,
    se n não for múltiplo) e só a ordem dos blocos é sorteada.
    """
    if com_reposicao:
        quantos = int(np.ceil(n / bloco))
        inicios = rng.integers(0, n, size=quantos)
        return np.concatenate([(np.arange(i, i + bloco) % n) for i in inicios])[:n]

    partes = [np.arange(i, min(i + bloco, n)) for i in range(0, n, bloco)]
    ordem = rng.permutation(len(partes))
    return np.concatenate([partes[i] for i in ordem])


def rodar(retornos: pd.DataFrame, com_reposicao: bool, bloco: int = BLOCO,
          sorteios: int = SORTEIOS, semente: int = 20260829) -> pd.DataFrame:
    """Uma linha por sorteio, com as métricas de cada perna e o prêmio.

    `com_reposicao=False` embaralha a história (teste 1);
    `com_reposicao=True` reamostra dela (teste 2).
    """
    rng = np.random.default_rng(semente)
    dados = {c: retornos[c].to_numpy() for c in retornos.columns}
    n = len(retornos)

    linhas = []
    for _ in range(sorteios):
        idx = _indices_em_blocos(n, bloco, rng, com_reposicao)
        linha = {}
        for nome, serie in dados.items():
            multiplo, aa = simular(serie[idx])
            linha[f"{nome}__multiplo"] = multiplo
            linha[f"{nome}__aa"] = aa
        linha["premio_pp"] = (linha["capital_allocators__aa"]
                              - linha["passive_etfs__aa"]) * 100
        linha["razao_multiplo"] = (linha["capital_allocators__multiplo"]
                                   / linha["passive_etfs__multiplo"])
        linhas.append(linha)
    return pd.DataFrame(linhas)


def observado(retornos: pd.DataFrame) -> dict:
    """As mesmas métricas na ordem em que a história aconteceu."""
    a_mult, a_aa = simular(retornos.capital_allocators.to_numpy())
    e_mult, e_aa = simular(retornos.passive_etfs.to_numpy())
    return {
        "alloc_multiplo": a_mult, "alloc_aa": a_aa,
        "etf_multiplo": e_mult, "etf_aa": e_aa,
        "premio_pp": (a_aa - e_aa) * 100,
        "razao_multiplo": a_mult / e_mult,
    }


def resumo(draws: pd.DataFrame, obs: dict, coluna: str) -> dict:
    """Distribuição de uma métrica, com o valor observado situado nela."""
    v = draws[coluna].to_numpy()
    return {
        "metrica": coluna,
        "observado": obs[coluna],
        "media": float(v.mean()),
        "desvio": float(v.std(ddof=1)),
        "p5": float(np.percentile(v, 5)),
        "p50": float(np.percentile(v, 50)),
        "p95": float(np.percentile(v, 95)),
        "fracao_positiva": float((v > 0).mean()) if coluna == "premio_pp"
        else float((v > 1).mean()),
    }


def sensibilidade_do_bloco(retornos: pd.DataFrame,
                           blocos: tuple[int, ...] = (3, 6, 12, 24),
                           sorteios: int = 1500) -> pd.DataFrame:
    """O tamanho do bloco decide o resultado?

    Bloco curto se aproxima do sorteio mês a mês e estreita a distribuição por
    destruir a memória da série; bloco longo se aproxima da história original e
    a estreita por falta de variedade. Se o veredito for o mesmo nos quatro, a
    escolha de 12 meses não está carregando a conclusão.
    """
    linhas = []
    for bloco in blocos:
        d = rodar(retornos, com_reposicao=True, bloco=bloco, sorteios=sorteios)
        v = d.premio_pp.to_numpy()
        linhas.append({
            "bloco_meses": bloco,
            "premio_medio_pp": float(v.mean()),
            "p5_pp": float(np.percentile(v, 5)),
            "p95_pp": float(np.percentile(v, 95)),
            "fracao_positiva": float((v > 0).mean()),
        })
    return pd.DataFrame(linhas)


def conferir_invariancia(retornos: pd.DataFrame, sorteios: int = 200,
                         semente: int = 7) -> float:
    """Maior desvio do prêmio sob reordenação pura — tem de ser ~zero.

    É a checagem de que o código respeita a aritmética: média geométrica não
    depende da ordem, então embaralhar não pode mover o prêmio em pontos ao ano.
    Um desvio grande aqui significaria bug no simulador, não achado.
    """
    d = rodar(retornos, com_reposicao=False, sorteios=sorteios, semente=semente)
    return float((d.premio_pp - observado(retornos)["premio_pp"]).abs().max())
