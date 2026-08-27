"""Testes da retenção na fonte sobre a série americana."""

import pandas as pd
import pytest
from capallo.transform.us_net import dividend_yield, net_series


def _serie(adj, px):
    return pd.DataFrame({
        "date": pd.date_range("2020-01-31", periods=len(adj), freq="ME"),
        "close_adj": adj, "close_px": px,
    })


def test_provento_do_mes_e_a_diferenca_entre_ajustado_e_preco():
    """Preço parado e ajustado subindo 2%: o mês pagou 2% de provento."""
    d = dividend_yield(_serie([100.0, 102.0], [100.0, 100.0]))
    assert d.iloc[0] == 0.0          # primeiro mês não tem retorno anterior
    assert d.iloc[1] == pytest.approx(0.02)


def test_papel_sem_dividendo_tem_provento_zero_todo_mes():
    """É a conferência que sustenta o método: Berkshire e Markel não pagam nada.

    As duas séries coincidem casa a casa, e qualquer coisa diferente de zero aqui
    significa que a decomposição está lendo ruído de arredondamento como dividendo.
    """
    d = dividend_yield(_serie([100.0, 110.0, 99.0], [100.0, 110.0, 99.0]))
    assert d.abs().max() == pytest.approx(0.0)


def test_aliquota_zero_reproduz_o_total_return_bruto():
    """A correção não pode mudar nada onde não há imposto."""
    s = _serie([100.0, 102.0, 108.0], [100.0, 100.0, 105.0])
    liquido = net_series(s, withholding=0.0)
    assert liquido.tolist() == pytest.approx(s.close_adj.tolist())


def test_imposto_reduz_apenas_a_parcela_de_provento():
    """Preço parado, 10% de provento, 30% retidos: o líquido sobe 7%."""
    s = _serie([100.0, 110.0], [100.0, 100.0])
    liquido = net_series(s, withholding=0.30)
    assert liquido.iloc[-1] == pytest.approx(107.0)


def test_ganho_de_preco_puro_nao_e_tributado():
    """Imposto de dividendo não pode incidir sobre valorização."""
    s = _serie([100.0, 120.0], [100.0, 120.0])
    assert net_series(s, withholding=0.30).iloc[-1] == pytest.approx(120.0)


def test_papel_que_paga_dividendo_termina_abaixo_do_bruto():
    s = _serie([100.0, 105.0, 112.0], [100.0, 102.0, 108.0])
    liquido = net_series(s, withholding=0.30)
    assert liquido.iloc[-1] < s.close_adj.iloc[-1]


def test_provento_negativo_de_arredondamento_e_limitado_a_zero():
    """A fonte arredonda e o ajustado às vezes rende uma fração a menos que o
    preço. Provento negativo não existe, e deixá-lo passar viraria um crédito
    de imposto."""
    s = _serie([100.0, 99.99999], [100.0, 100.0])
    assert dividend_yield(s).iloc[-1] < 0
    assert net_series(s, withholding=0.30).iloc[-1] == pytest.approx(100.0)
