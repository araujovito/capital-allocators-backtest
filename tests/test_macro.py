"""Testes do coletor macro que nao dependem de rede."""

from datetime import date

import pandas as pd
import pytest

from capallo.ingest.bacen import PTAX_CURRENCIES, SGS_SERIES
from capallo.ingest.macro import DEFAULT_START, validate


def test_series_necessarias_mapeadas():
    assert {"CDI", "IPCA"} <= set(SGS_SERIES)
    assert set(PTAX_CURRENCIES) == {"USD", "EUR", "JPY", "SEK"}


def test_janela_comeca_antes_do_estudo():
    """O primeiro reajuste do aporte precisa do IPCA do periodo anterior."""
    assert DEFAULT_START < date(2006, 1, 1)


def test_validate_detecta_ipca_incompleto(tmp_path):
    meses = pd.date_range("2006-01-01", "2025-11-01", freq="MS")  # falta dez/2025
    pd.DataFrame({"date": meses, "value": 0.5}).to_parquet(tmp_path / "ipca.parquet")
    pd.DataFrame({"date": meses, "value": 0.04}).to_parquet(tmp_path / "cdi.parquet")
    pd.DataFrame(
        {"date": meses, "currency": "USD", "bid": 2.0, "ask": 2.01}
    ).to_parquet(tmp_path / "ptax.parquet")

    problems = validate(tmp_path)
    assert any("IPCA" in p and "239" in p for p in problems)
    assert any("moedas ausentes" in p for p in problems)


def test_validate_detecta_venda_abaixo_da_compra(tmp_path):
    meses = pd.date_range("2006-01-01", "2025-12-01", freq="MS")
    pd.DataFrame({"date": meses, "value": 0.5}).to_parquet(tmp_path / "ipca.parquet")
    pd.DataFrame({"date": meses, "value": 0.04}).to_parquet(tmp_path / "cdi.parquet")
    fx = pd.concat(
        [
            pd.DataFrame({"date": meses, "currency": c, "bid": 2.0, "ask": 2.01})
            for c in PTAX_CURRENCIES
        ]
    )
    fx.loc[fx.index[0], "ask"] = 1.0
    fx.to_parquet(tmp_path / "ptax.parquet")

    assert any("venda abaixo da compra" in p for p in validate(tmp_path))


@pytest.mark.parametrize("path", ["cdi.parquet", "ipca.parquet", "ptax.parquet"])
def test_curated_real_se_existir(path):
    """Se o fetch-macro ja rodou, os dados reais precisam passar na validacao."""
    from pathlib import Path

    curated = Path(__file__).resolve().parents[1] / "data" / "curated"
    if not (curated / path).exists():
        pytest.skip("data/curated ainda nao materializado")
    assert validate(curated) == []
