"""Testes dos experimentos de sensibilidade.

O motor Rust não é chamado aqui: o que precisa de teste é a mecânica em volta —
trocar a data de início sem trocar mais nada, e conhecer as pontas da PTAX.
Rodar o motor de verdade é trabalho do `capallo sensitivity`.
"""

import pandas as pd
import pytest
from capallo.analysis.sensitivity import _premios, _toml_com_inicio
from capallo.transform.dataset import build

TOML = """\
[strategy]
name = "Teste"
start = "2006-01-01"
end = "2025-12-31"

[strategy.contribution]
amount = 1000.0
"""


def test_troca_a_data_de_inicio_e_mais_nada(tmp_path):
    """A comparação só é da janela se nenhuma outra regra tiver mudado junto."""
    origem = tmp_path / "orig.toml"
    origem.write_text(TOML)
    destino = _toml_com_inicio(origem, "2012-01-01", tmp_path / "novo.toml")

    antes, depois = origem.read_text().splitlines(), destino.read_text().splitlines()
    diferentes = [(a, b) for a, b in zip(antes, depois) if a != b]
    assert diferentes == [('start = "2006-01-01"', 'start = "2012-01-01"')]
    assert 'end = "2025-12-31"' in destino.read_text()


def test_estrategia_sem_data_de_inicio_falha_em_vez_de_passar_batido(tmp_path):
    """Silêncio aqui produziria dez janelas idênticas com rótulos diferentes."""
    origem = tmp_path / "sem.toml"
    origem.write_text("[strategy]\nname = \"X\"\n")
    with pytest.raises(ValueError, match="start"):
        _toml_com_inicio(origem, "2012-01-01", tmp_path / "novo.toml")


def test_apenas_o_primeiro_start_e_trocado(tmp_path):
    """`[strategy.contribution]` pode ganhar um `start` próprio; ele não é a janela."""
    origem = tmp_path / "dois.toml"
    origem.write_text(TOML + '\nstart = "2009-01-01"\n')
    destino = _toml_com_inicio(origem, "2012-01-01", tmp_path / "novo.toml")
    texto = destino.read_text()
    assert 'start = "2012-01-01"' in texto
    assert 'start = "2009-01-01"' in texto


def test_ponta_de_cambio_desconhecida_falha(tmp_path):
    """Um typo em `fx_side` não pode virar silenciosamente a ponta padrão."""
    with pytest.raises(ValueError, match="fx_side"):
        build(tmp_path, fx_side="venda")


def test_premio_e_a_diferenca_entre_as_duas_pernas(monkeypatch):
    """Sinal e magnitude do prêmio, sem depender de rodar o motor."""
    falso = {
        "capital_allocators": {"retorno_real_aa": 0.0887, "reais_por_real": 3.75},
        "passive_etfs": {"retorno_real_aa": 0.0521, "reais_por_real": 2.49},
    }
    monkeypatch.setattr(
        "capallo.analysis.sensitivity.evaluate", lambda p, c: falso[p.stem]
    )
    from pathlib import Path
    out = _premios({k: Path(f"{k}.csv") for k in falso}, Path("."))
    assert list(out.regiao) == ["Global"]
    assert out.premio_pp.iloc[0] == pytest.approx(3.66, abs=0.01)


def test_regiao_sem_as_duas_pernas_e_omitida(monkeypatch):
    """Meia comparação é pior que nenhuma: sairia como prêmio zero."""
    monkeypatch.setattr(
        "capallo.analysis.sensitivity.evaluate",
        lambda p, c: {"retorno_real_aa": 0.05, "reais_por_real": 2.0},
    )
    from pathlib import Path
    out = _premios({"br_allocators": Path("br_allocators.csv")}, Path("."))
    assert out.empty


def test_spread_da_ptax_encolheu_ao_longo_da_janela():
    """O motivo de o experimento existir: spread constante cancelaria no retorno.

    Se este teste falhar porque o spread virou constante, o experimento da ponta
    da PTAX perde o sentido — e é isso que ele deve dizer, em vez de seguir
    medindo zero e chamando de robustez.
    """
    ptax = pd.read_parquet("data/curated/ptax.parquet")
    usd = ptax[ptax.currency == "USD"].copy()
    usd["spread"] = usd.ask / usd.bid - 1
    por_ano = usd.groupby(usd.date.dt.year).spread.mean()
    assert por_ano.loc[2006] > 10 * por_ano.loc[2025]
