"""Testes dos recortes de crise."""

import pandas as pd
import pytest
from capallo.analysis.crises import CRISES, Crise, janela, regras_congeladas


def _indice(valores, inicio="2020-01"):
    idx = pd.period_range(inicio, periods=len(valores), freq="M")
    return pd.Series(valores, index=idx, dtype=float)


CRISE = Crise("teste", "2020-02", "2020-04", "fixture")


def test_nivel_de_entrada_e_o_do_mes_anterior_a_janela():
    """A queda do primeiro mês da crise é parte da crise.

    Tomando o primeiro mês de dentro como base, a queda de 2020-02 sumiria e a
    crise apareceria como estável.
    """
    r = janela(_indice([100.0, 80.0, 70.0, 90.0]), CRISE)
    assert r["retorno"] == pytest.approx(-0.10)   # 100 → 90
    assert r["queda_max"] == pytest.approx(-0.30)  # 100 → 70


def test_janela_que_comeca_na_primeira_observacao_usa_o_proprio_nivel():
    """Sem mês anterior não há véspera; a base é o primeiro ponto disponível."""
    r = janela(_indice([80.0, 70.0, 90.0], inicio="2020-02"), CRISE)
    assert r["retorno"] == pytest.approx(90 / 80 - 1)


def test_queda_nao_pode_ser_positiva():
    """O CDI nunca fica abaixo do nível de entrada e reportava '+0,1% de queda'."""
    r = janela(_indice([100.0, 101.0, 102.0, 103.0]), CRISE)
    assert r["queda_max"] == 0.0
    assert r["recuperacao_meses"] == 0


def test_recuperacao_conta_do_fim_da_janela_ate_voltar_ao_nivel_de_entrada():
    valores = [100.0, 80.0, 70.0, 75.0, 90.0, 99.0, 101.0]
    r = janela(_indice(valores), CRISE)
    assert r["retorno"] < 0
    # Fim da janela em 2020-04 (índice 3); volta a 100 em 2020-07 (índice 6).
    assert r["recuperacao_meses"] == 3


def test_serie_que_termina_sem_recuperar_devolve_none():
    """None é informação: o investidor ainda não voltou ao nível de entrada."""
    r = janela(_indice([100.0, 80.0, 70.0, 75.0, 78.0]), CRISE)
    assert r["recuperacao_meses"] is None


def test_janela_fora_da_serie_falha_em_vez_de_devolver_vazio():
    with pytest.raises(ValueError, match="fora da série"):
        janela(_indice([100.0, 101.0], inicio="2010-01"), CRISE)


def _escreve(path, nome, aporte=1000.0, fim="2025-12-31"):
    path.write_text(
        f'[strategy]\nname = "{nome}"\nstart = "2006-01-01"\nend = "{fim}"\n'
        f'base_currency = "BRL"\ndividends = "reinvest"\n'
        f'[strategy.contribution]\namount = {aporte}\nfrequency = "monthly"\n'
    )


def test_estrategias_com_as_mesmas_regras_passam(tmp_path):
    _escreve(tmp_path / "a.toml", "A")
    _escreve(tmp_path / "b.toml", "B")
    assert regras_congeladas(tmp_path) == []


def test_aporte_diferente_entre_estrategias_e_denunciado(tmp_path):
    """Sem esta checagem, o recorte de crise compararia carteiras sob regras
    diferentes e nada denunciaria isso."""
    _escreve(tmp_path / "a.toml", "A")
    _escreve(tmp_path / "b.toml", "B", aporte=2000.0)
    assert any("contribution" in p for p in regras_congeladas(tmp_path))


def test_janela_diferente_entre_estrategias_e_denunciada(tmp_path):
    _escreve(tmp_path / "a.toml", "A")
    _escreve(tmp_path / "b.toml", "B", fim="2024-12-31")
    assert any("'end'" in p for p in regras_congeladas(tmp_path))


def test_toda_crise_declara_a_fonte_da_datacao():
    """Janela sem fonte é janela escolhida pelo estudo — o que a regra proíbe."""
    assert CRISES
    for c in CRISES:
        assert c.fonte.strip()
        assert c.inicio < c.fim
        assert "2006-01" <= c.inicio and c.fim <= "2025-12"
