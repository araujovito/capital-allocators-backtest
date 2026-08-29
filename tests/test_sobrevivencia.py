"""Testes do universo sem viés e do teste de sobrevivência.

Este módulo é o único do projeto cujo resultado principal é **uma limitação**. As
guardas existem para impedir que a limitação seja apagada por engano: se alguém
publicar "33% sobreviveram" como taxa de mortalidade, o número estará errado, e é
o teste que tem de dizer isso.
"""

from pathlib import Path

import pandas as pd
import pytest
from capallo.analysis.sobrevivencia import (
    RENOMEADAS_OU_FUNDIDAS,
    permanencia,
    por_que_nao_fecha,
    sumiram,
)
from capallo.ingest.b3_universo import (
    MES_BASE,
    MES_FIM,
    universo_investavel,
    validate,
)

CURATED = Path("data/curated")


@pytest.fixture(scope="module")
def painel():
    return pd.read_parquet(CURATED / "b3_universo.parquet")


def test_o_universo_contem_os_ativos_do_estudo(painel):
    """Se o parser divergisse de `ingest.b3`, o universo não seria comparável."""
    assert {"ITSA4", "BRAP4", "PIBB11"} <= set(painel.ticker)
    assert validate(CURATED) == []


def test_o_universo_e_muito_maior_que_o_estudo(painel):
    """O ponto do módulo: o estudo escolheu 2 nomes de uma lista de dezenas."""
    inv = universo_investavel(painel)
    assert len(inv) > 50
    assert {"ITAUSA", "BRADESPAR"} <= set(inv.nome)


def test_uma_classe_por_empresa(painel):
    """ON e PN da mesma companhia são a mesma aposta; contar as duas infla."""
    inv = universo_investavel(painel)
    assert inv.nome.is_unique


def test_o_corte_de_liquidez_morde(painel):
    """Sem corte, o universo enche de papel que negociou uma vez no mês."""
    largo = universo_investavel(painel, volume_minimo=0.0)
    estreito = universo_investavel(painel, volume_minimo=1e6)
    assert len(estreito) < len(largo)


def test_permanencia_nao_e_sobrevivencia(painel):
    """A guarda central deste módulo.

    Contar desaparecimento de ticker como morte superestima a mortalidade — e a
    prova é que empresas comprovadamente vivas estão entre as que somem. Se este
    teste falhar, ou o painel mudou, ou alguém apagou os contraexemplos.
    """
    fora = sumiram(painel)
    identificadas = fora[fora.nao_morreu.notna()]
    assert len(identificadas) >= 8
    assert {"AMBEV", "VALE R DOCE", "ITAUBANCO"} <= set(identificadas.nome)


def test_permanencia_por_nome_supera_a_por_ticker(painel):
    """Nome é identidade melhor que ticker, e ainda assim insuficiente."""
    p = permanencia(painel)
    assert p["mesmo_nome"] >= p["mesmo_ticker"]
    assert p["mesmo_nome"] < p["empresas_no_inicio"]
    assert p["sumiram_por_nome"] == p["empresas_no_inicio"] - p["mesmo_nome"]


def test_os_contraexemplos_estao_no_universo_inicial(painel):
    """Contraexemplo que não estivesse no universo não provaria nada."""
    inv = set(universo_investavel(painel).nome)
    assert set(RENOMEADAS_OU_FUNDIDAS) <= inv


def test_as_razoes_de_nao_fechar_estao_escritas(painel):
    """A limitação é o resultado; apagá-la sem querer é o risco a trancar."""
    razoes = por_que_nao_fecha(painel)
    assert len(razoes) >= 4
    assert any("mapa de entidades" in r for r in razoes)
    assert any("preço bruto" in r for r in razoes)


def test_os_meses_de_referencia_existem(painel):
    assert MES_BASE in set(painel.mes)
    assert MES_FIM in set(painel.mes)
