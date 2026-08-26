"""Testes do total return brasileiro."""

import pandas as pd
import pytest

from capallo.transform.total_return import WITHHOLDING, build_series, next_session


def _px(dates, price=100.0, ticker="X"):
    return pd.DataFrame({"date": dates, "ticker": ticker, "close": price,
                         "volume": 1.0, "trades": 1})


def _sem_cash():
    return pd.DataFrame({"ticker": [], "ex_date": pd.to_datetime([]),
                         "payment_date": pd.to_datetime([]), "kind": [],
                         "value": [], "stock_type": []})


def _sem_stock():
    return pd.DataFrame({"ticker": [], "ex_date": pd.to_datetime([]), "kind": [],
                         "factor_pct": [], "asset": []})


def test_next_session_ignora_data_anterior_a_serie():
    """Evento de antes do inicio da serie nao pode cair no primeiro pregao."""
    s = pd.DatetimeIndex(pd.bdate_range("2006-01-02", periods=5))
    assert next_session(pd.Timestamp("2005-04-29"), s) is None
    assert next_session(pd.Timestamp("2006-01-03"), s) == pd.Timestamp("2006-01-04")


def test_evento_anterior_a_janela_nao_altera_unidades():
    dias = pd.bdate_range("2006-01-02", periods=5)
    stock = pd.DataFrame({"ticker": ["X"], "ex_date": [pd.Timestamp("2005-04-29")],
                          "kind": ["DESDOBRAMENTO"], "factor_pct": [100.0], "asset": [""]})
    out = build_series("X", _px(dias), _sem_cash(), stock)
    assert out.units.iloc[-1] == pytest.approx(1.0)


def test_evento_duplicado_por_classe_conta_uma_vez():
    """A B3 publica o mesmo evento para ON e PN; aplicar os dois dobrava o split."""
    dias = pd.bdate_range("2006-01-02", periods=5)
    ex = pd.Timestamp("2006-01-03")
    stock = pd.DataFrame({"ticker": ["X", "X"], "ex_date": [ex, ex],
                          "kind": ["DESDOBRAMENTO"] * 2, "factor_pct": [100.0, 100.0],
                          "asset": ["ISIN_ON", "ISIN_PN"]})
    out = build_series("X", _px(dias), _sem_cash(), stock)
    assert out.units.iloc[-1] == pytest.approx(2.0)


def test_jcp_sofre_retencao_e_dividendo_nao():
    assert WITHHOLDING["JRS CAP PROPRIO"] == 0.15
    assert WITHHOLDING["DIVIDENDO"] == 0.00

    dias = pd.bdate_range("2006-01-02", periods=5)
    ex = pd.Timestamp("2006-01-03")
    def series(kind):
        cash = pd.DataFrame({"ticker": ["X"], "ex_date": [ex],
                             "payment_date": [ex], "kind": [kind],
                             "value": [10.0], "stock_type": ["PN"]})
        return build_series("X", _px(dias), cash, _sem_stock()).units.iloc[-1]

    # preco 100, provento 10: dividendo isento soma 10%, JCP liquido soma 8,5%
    assert series("DIVIDENDO") == pytest.approx(1.10)
    assert series("JRS CAP PROPRIO") == pytest.approx(1.085)


def test_provento_em_especie_entra_como_caixa_reinvestido():
    dias = pd.bdate_range("2006-01-02", periods=5)
    in_kind = pd.DataFrame({"ticker": ["X"], "ex_date": [pd.Timestamp("2006-01-03")],
                            "value_per_share": [25.0]})
    out = build_series("X", _px(dias), _sem_cash(), _sem_stock(), in_kind)
    assert out.units.iloc[-1] == pytest.approx(1.25)


def test_serie_real_valida_se_existir():
    from pathlib import Path

    from capallo.transform.build_br import validate

    curated = Path(__file__).resolve().parents[1] / "data" / "curated"
    if not (curated / "br_total_return.parquet").exists():
        pytest.skip("br_total_return ainda nao materializado")
    assert validate(curated) == []
