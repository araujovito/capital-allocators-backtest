"""Testes do total return de Europa e Japão."""

import pandas as pd
import pytest
from capallo.transform.build_intl import accumulate, payouts_gbl, payouts_jp


def _px(dates, close, ticker="X"):
    return pd.DataFrame({"date": pd.to_datetime(dates), "ticker": ticker, "close": close})


def _pay(ticker, ex, value):
    return pd.DataFrame({"ticker": ticker, "ex_date": pd.to_datetime(ex), "value": value})


def test_dividendo_do_exercicio_vai_para_maio_do_ano_seguinte():
    """A Assembleia que aprova o exercício N acontece em maio de N+1."""
    d = pd.DataFrame({"ticker": ["GBLB"], "fiscal_year": [2015], "gross_dividend": [2.86]})
    out = payouts_gbl(d)
    assert list(out.ex_date) == [pd.Timestamp("2016-05-01")]
    assert out.value.iloc[0] == pytest.approx(2.86)


def test_dividendo_japones_parte_ao_meio_entre_as_duas_datas_de_registro():
    """Interina em setembro do ano anterior, final no fecho do exercício."""
    d = pd.DataFrame({"ticker": ["8058"], "fiscal_year": [2020], "dps_jpy": [44.0]})
    out = payouts_jp(d).sort_values("ex_date").reset_index(drop=True)
    assert list(out.ex_date) == [pd.Timestamp("2019-09-30"), pd.Timestamp("2020-03-31")]
    assert list(out.value) == [22.0, 22.0]
    assert out.value.sum() == pytest.approx(44.0)


def test_provento_entra_liquido_de_retencao():
    """10 de dividendo sobre preço 100, com 15% retidos, compra 8,5% de unidade."""
    px = _px(["2020-01-31", "2020-02-29"], [100.0, 100.0])
    out = accumulate("X", px, _pay("X", ["2020-01-31"], [10.0]), withholding=0.15)
    assert out.units.iloc[-1] == pytest.approx(1.085)
    assert out.tr_index.iloc[-1] == pytest.approx(108.5)


def test_provento_anterior_ao_inicio_da_serie_e_descartado():
    """O investidor do estudo não detinha a ação — o provento não é dele.

    É o mesmo erro que dobrava a quantidade inicial de BRAP4 no lado brasileiro.
    """
    px = _px(["2006-01-31", "2006-02-28"], [100.0, 100.0])
    out = accumulate("X", px, _pay("X", ["2005-09-30"], [50.0]), withholding=0.0)
    assert out.units.iloc[-1] == pytest.approx(1.0)


def test_data_ex_cai_na_primeira_observacao_em_ou_depois_dela():
    """1º de maio é feriado na Bélgica: o provento cai no pregão seguinte."""
    px = _px(["2016-04-29", "2016-05-02", "2016-05-03"], [100.0, 100.0, 100.0])
    out = accumulate("X", px, _pay("X", ["2016-05-01"], [10.0]), withholding=0.0)
    assert out.units.tolist() == pytest.approx([1.0, 1.1, 1.1])


def test_provento_posterior_ao_fim_da_serie_nao_quebra_a_coleta():
    px = _px(["2025-11-30", "2025-12-31"], [100.0, 100.0])
    out = accumulate("X", px, _pay("X", ["2026-03-31"], [10.0]), withholding=0.0)
    assert out.units.iloc[-1] == pytest.approx(1.0)


def test_proventos_na_mesma_data_somam():
    """Duas parcelas japonesas podem cair na mesma observação mensal."""
    px = _px(["2020-02-29", "2020-03-31"], [100.0, 100.0])
    out = accumulate("X", px, _pay("X", ["2020-03-01", "2020-03-31"], [5.0, 5.0]), 0.0)
    assert out.units.tolist() == pytest.approx([1.0, 1.1])


def test_ticker_sem_preco_falha_em_vez_de_devolver_vazio():
    with pytest.raises(ValueError, match="sem preços"):
        accumulate("Y", _px(["2020-01-31"], [100.0]), _pay("Y", [], []), 0.0)
