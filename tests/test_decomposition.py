"""Testes da decomposição de retorno e do Allocator Premium."""

import pandas as pd
import pytest
from capallo.analysis.decomposition import (
    VOL_MINIMA_PP,
    _fx_mensal,
    _veredito,
    by_asset,
)


@pytest.fixture
def curated(tmp_path):
    """IPCA e PTAX mínimos: dois meses, inflação de 10%, moedas que dobram."""
    d = tmp_path / "curated"
    d.mkdir()
    meses = pd.to_datetime(["2006-01-01", "2025-12-01"])
    pd.DataFrame({"date": meses, "value": [0.0, 10.0]}).to_parquet(d / "ipca.parquet")
    linhas = []
    for moeda, (a, b) in {"USD": (2.0, 4.0), "EUR": (2.5, 5.0), "JPY": (0.02, 0.04),
                          "SEK": (0.3, 0.6)}.items():
        linhas += [{"date": meses[0], "currency": moeda, "bid": a, "ask": a},
                   {"date": meses[1], "currency": moeda, "bid": b, "ask": b}]
    pd.DataFrame(linhas).to_parquet(d / "ptax.parquet")
    return d


def _panel(tmp_path, linhas):
    e = tmp_path / "engine"
    e.mkdir(exist_ok=True)
    pd.DataFrame(linhas).to_csv(e / "panel.csv", index=False)
    return e


def test_identidade_ativo_vezes_cambio_reproduz_o_retorno_em_brl(curated, tmp_path):
    engine = _panel(tmp_path, [
        {"month": "2006-01", "ticker": "ITSA4", "currency": "BRL",
         "tr_local": 10.0, "fx": 1.0, "tr_brl": 10.0},
        {"month": "2025-12", "ticker": "ITSA4", "currency": "BRL",
         "tr_local": 30.0, "fx": 1.0, "tr_brl": 30.0},
    ])
    r = by_asset(curated, engine).iloc[0]
    assert r.local * r.cambio == pytest.approx(r.nominal_brl)
    assert r.cambio == pytest.approx(1.0)
    assert r.nominal_brl == pytest.approx(3.0)
    # Inflação de 10% no período come parte do retorno nominal.
    assert r.real_brl == pytest.approx(3.0 / 1.1)


def test_wrapper_em_dolar_e_transparente(curated, tmp_path):
    """O EWJ liquida em dólar, mas o câmbio atribuído é o do iene.

    Sem isso, a perna passiva apareceria como aposta em dólar contra uma perna
    ativa em iene, carregando as duas a mesma economia subjacente.
    """
    engine = _panel(tmp_path, [
        {"month": "2006-01", "ticker": "EWJ", "currency": "USD",
         "tr_local": 10.0, "fx": 2.0, "tr_brl": 20.0},
        {"month": "2025-12", "ticker": "EWJ", "currency": "USD",
         "tr_local": 20.0, "fx": 4.0, "tr_brl": 80.0},
    ])
    r = by_asset(curated, engine).iloc[0]
    assert r.moeda_negociacao == "USD"
    assert r.moeda_exposicao == "JPY"
    # Iene dobrou (0,02 → 0,04), não o dólar; o retorno local sai por diferença.
    assert r.cambio == pytest.approx(2.0)
    assert r.local == pytest.approx(2.0)
    assert r.local * r.cambio == pytest.approx(r.nominal_brl)


def test_fx_de_ativo_em_real_e_sempre_um(curated):
    fx = _fx_mensal(curated, "BRL", pd.Index(["2006-01", "2025-12"]))
    assert fx.tolist() == [1.0, 1.0]


def test_moeda_sem_ptax_falha_em_vez_de_seguir(curated):
    with pytest.raises(ValueError, match="PTAX não cobre"):
        _fx_mensal(curated, "CHF", pd.Index(["2006-01"]))


def test_veredito_separa_dominancia_de_premio_com_risco():
    assert "dominância" in _veredito(0.02, -0.06, material=True)
    assert _veredito(0.02, 0.06, material=True) == "prêmio com risco extra"
    assert _veredito(-0.02, -0.06, material=True) == "menos retorno, mas menos risco"
    assert _veredito(-0.02, 0.06, material=True) == "menos retorno e mais risco"


def test_diferenca_de_volatilidade_irrelevante_vira_empate_de_risco():
    """Nos EUA a diferença é de 0,005 p.p.: chamar isso de "mais risco" lê ruído.

    Foi o caso que produzia "prêmio por unidade de risco" de −26,6, dividindo um
    prêmio pequeno por uma diferença de volatilidade que é zero na prática.
    """
    assert _veredito(-0.0013, 0.00005, material=False) == "mesmo risco: sem prêmio"
    assert _veredito(0.0645, -0.0005, material=False) == "mesmo risco: prêmio"
    assert VOL_MINIMA_PP > 0
