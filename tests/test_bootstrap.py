"""Testes do bootstrap.

Um bootstrap mal feito produz números com aparência de rigor e conteúdo de ruído.
As três armadilhas que estas guardas cobrem: reamostrar as pernas em separado
(destrói a correlação e alarga o prêmio por artefato), embaralhar de um jeito que
não é permutação (duplica meses e move o que não pode se mover), e sortear mês a
mês em vez de blocos (fabrica uma série sem 2008 como evento).
"""

from pathlib import Path

import capallo.analysis.bootstrap as bs
import numpy as np
import pandas as pd
import pytest
from capallo.analysis.scoreboard import evaluate

RESULTS, CURATED = Path("data/results"), Path("data/curated")


def _rng():
    return np.random.default_rng(0)


def test_embaralhar_e_uma_permutacao_exata():
    """A primeira versão errou aqui: blocos circulares não ladrilham 239 meses."""
    for n in (239, 240, 100):
        idx = bs._indices_em_blocos(n, 12, _rng(), com_reposicao=False)
        assert len(idx) == n
        assert sorted(idx) == list(range(n)), n


def test_reamostrar_com_reposicao_repete_e_omite_meses():
    """É o ponto do teste 2: a amostra tem de poder ser outra."""
    n = 239
    idx = bs._indices_em_blocos(n, 12, _rng(), com_reposicao=True)
    assert len(idx) == n
    assert len(set(idx)) < n


def test_os_blocos_sao_contiguos():
    """Sortear mês a mês fabricaria uma série sem 2008 e sem 2020 como eventos."""
    idx = bs._indices_em_blocos(239, 12, _rng(), com_reposicao=True)
    saltos = np.diff(idx)
    # Dentro de um bloco o passo é 1; só nas emendas ele muda.
    assert (saltos == 1).mean() > 0.85


def test_o_premio_nao_se_move_ao_reordenar():
    """Média geométrica não depende da ordem — aritmética, não achado empírico.

    Este teste existe para provar que o código respeita isso. Se falhar, o
    simulador está com bug e nenhum número do módulo vale.
    """
    r = bs.retornos_reais(RESULTS, CURATED)
    assert bs.conferir_invariancia(r, sorteios=60) < 1e-9


def test_o_simulador_reproduz_o_resultado_do_motor():
    """Se o simulador não reproduz a história, a distribuição em volta é fantasia."""
    r = bs.retornos_reais(RESULTS, CURATED)
    for nome in ("capital_allocators", "passive_etfs", "cdi"):
        multiplo, aa = bs.simular(r[nome].to_numpy())
        d = evaluate(RESULTS / f"{nome}.csv", CURATED)
        assert aa == pytest.approx(d["retorno_real_aa"], abs=5e-5), nome
        assert multiplo == pytest.approx(d["reais_por_real"], rel=0.01), nome


def test_todas_as_pernas_usam_os_mesmos_indices():
    """A guarda central: reamostrar cada perna por conta destrói a correlação.

    Com os mesmos índices, um sorteio degenerado — o mesmo bloco repetido — tem de
    devolver, para as duas pernas, exatamente o retorno daquele bloco.
    """
    r = bs.retornos_reais(RESULTS, CURATED)
    idx = np.tile(np.arange(12), 20)[: len(r)]
    a = bs.simular(r.capital_allocators.to_numpy()[idx])[1]
    e = bs.simular(r.passive_etfs.to_numpy()[idx])[1]
    esperado_a = bs.simular(np.tile(r.capital_allocators.to_numpy()[:12], 20)[: len(r)])[1]
    assert a == pytest.approx(esperado_a)
    assert a != e


def test_as_pernas_compartilham_o_calendario():
    r = bs.retornos_reais(RESULTS, CURATED)
    assert isinstance(r.index, pd.PeriodIndex)
    assert r.notna().to_numpy().all()
    assert set(bs.PERNAS) <= set(r.columns)


def test_o_sorteio_e_reprodutivel():
    """Sem semente fixa, o número do README mudaria a cada execução."""
    r = bs.retornos_reais(RESULTS, CURATED)
    a = bs.rodar(r, com_reposicao=True, sorteios=40)
    b = bs.rodar(r, com_reposicao=True, sorteios=40)
    assert a.premio_pp.equals(b.premio_pp)


def test_o_premio_sobrevive_a_grande_maioria_das_historias():
    """O achado. Se cair muito abaixo disso, o README passa a mentir."""
    r = bs.retornos_reais(RESULTS, CURATED)
    d = bs.rodar(r, com_reposicao=True, sorteios=800)
    assert (d.premio_pp > 0).mean() > 0.95


def test_o_multiplo_observado_esta_na_cauda_alta_da_reordenacao():
    """A ressalva. O placar de 3,75x teve sequência favorável, e isso fica dito."""
    r = bs.retornos_reais(RESULTS, CURATED)
    obs = bs.observado(r)
    d = bs.rodar(r, com_reposicao=False, sorteios=800)
    pct = (d["capital_allocators__multiplo"] < obs["alloc_multiplo"]).mean()
    assert pct > 0.85
    # Mas a razão entre os múltiplos fica no meio: a sequência ajudou as duas pernas.
    assert abs(d.razao_multiplo.median() - obs["razao_multiplo"]) < 0.05
