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


def test_equities_us_validate_detecta_meses_faltando(tmp_path):
    import pandas as pd

    from capallo.ingest.equities import US_LISTED, validate as eq_validate

    meses = pd.date_range("2006-01-01", "2025-12-01", freq="MS")
    frames = []
    for i, t in enumerate(US_LISTED):
        n = len(meses) - (1 if i == 0 else 0)  # o primeiro fica com um mes a menos
        frames.append(
            pd.DataFrame({"ticker": t, "date": meses[:n], "symbol": t,
                          "currency": "USD", "close_adj": 100.0})
        )
    pd.concat(frames).to_parquet(tmp_path / "equities_us.parquet")

    problems = eq_validate(tmp_path)
    assert any("239 meses" in p for p in problems)


def test_equities_us_reais_se_existirem():
    from pathlib import Path

    import pytest

    from capallo.ingest.equities import validate as eq_validate

    curated = Path(__file__).resolve().parents[1] / "data" / "curated"
    if not (curated / "equities_us.parquet").exists():
        pytest.skip("equities_us ainda nao materializado")
    assert eq_validate(curated) == []


def test_b3_aceita_codbdi_de_etf():
    """PIBB11 e classificado como certificado de investimento (14), nao lote padrao."""
    from capallo.ingest.b3 import CODBDI_ACEITOS

    assert CODBDI_ACEITOS == {"02", "14"}


def test_b3_validate_detecta_divergencia_entre_tickers(tmp_path):
    import pandas as pd

    from capallo.ingest.b3 import validate as b3_validate

    dias = pd.bdate_range("2006-01-02", "2025-12-30")
    frames = []
    for i, t in enumerate(["ITSA4", "BRAP4", "PIBB11"]):
        n = len(dias) - (5 if i == 0 else 0)
        frames.append(pd.DataFrame({"date": dias[:n], "ticker": t, "close": 10.0,
                                    "volume": 1.0, "trades": 1}))
    pd.concat(frames).to_parquet(tmp_path / "b3_prices.parquet")
    assert any("diverge" in p for p in b3_validate(tmp_path))


def test_b3_real_se_existir():
    from pathlib import Path

    import pytest

    from capallo.ingest.b3 import validate as b3_validate

    curated = Path(__file__).resolve().parents[1] / "data" / "curated"
    if not (curated / "b3_prices.parquet").exists():
        pytest.skip("b3_prices ainda nao materializado")
    assert b3_validate(curated) == []


def test_b3_events_converte_numero_brasileiro():
    from capallo.ingest.b3_events import _br_number

    assert _br_number("0,13800000000") == 0.138
    assert _br_number("1.234,56") == 1234.56
    assert _br_number("") is None
    assert _br_number(None) is None


def test_b3_events_reconcile_flagra_retorno_implausivel(tmp_path):
    import pandas as pd

    from capallo.ingest.b3_events import reconcile

    dias = pd.bdate_range("2006-01-02", "2025-12-30")
    pd.DataFrame({"date": list(dias) * 2,
                  "ticker": ["ITSA4"] * len(dias) + ["BRAP4"] * len(dias),
                  "close": 10.0, "volume": 1.0, "trades": 1}
                 ).to_parquet(tmp_path / "b3_prices.parquet")
    pd.DataFrame({"ticker": ["ITSA4", "BRAP4"],
                  "ex_date": [pd.Timestamp("2010-01-04")] * 2,
                  "payment_date": [pd.Timestamp("2010-02-04")] * 2,
                  "kind": "DIVIDENDO", "value": 0.1, "stock_type": "PN"}
                 ).to_parquet(tmp_path / "b3_cash_dividends.parquet")
    pd.DataFrame({"ticker": ["ITSA4"], "ex_date": [pd.Timestamp("2010-01-04")],
                  "kind": ["BONIFICACAO"], "factor_pct": [2.0], "asset": [""]}
                 ).to_parquet(tmp_path / "b3_stock_events.parquet")

    w = reconcile(tmp_path)
    # preco constante e um provento minusculo: tem de disparar os dois avisos
    assert any("abaixo do CDI" in x for x in w)
    assert any("eventos em ações" in x for x in w)
