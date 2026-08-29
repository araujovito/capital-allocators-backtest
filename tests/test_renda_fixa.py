"""Testes da perna de renda fixa.

O que precisa de guarda: a convenção de compra e venda do Tesouro Direto — que é
o inverso da PTAX e, trocada, faria o título render o que custa —, a mecânica da
rolagem, e a separação entre retorno ponderado por tempo e por dinheiro, que é o
achado desta perna.
"""

from pathlib import Path

import pandas as pd
import pytest
import tomllib
from capallo.analysis.renda_fixa import (
    PERIODOS,
    inversoes,
    sequencia,
    tempo_contra_dinheiro,
)
from capallo.ingest.tesouro import TITULO
from capallo.transform.build_tesouro import REGRAS, build_index, comparar_regras
from capallo.universe import BY_TICKER, RENDA_FIXA

CURATED, RESULTS, STRATEGIES = Path("data/curated"), Path("data/results"), Path("strategies")


def test_o_titulo_coletado_e_o_zero_cupom():
    """Com juros semestrais exigiria modelar reinvestimento de cupom por 20 anos."""
    assert TITULO == "Tesouro IPCA+"
    assert "Semestrais" not in TITULO


def test_compra_e_sempre_mais_cara_que_venda():
    """A convenção do Tesouro é o inverso da PTAX; trocada, o spread vira lucro."""
    df = pd.read_parquet(CURATED / "tesouro_ipca.parquet")
    assert (df.pu_compra >= df.pu_venda).all()
    assert (df.pu_compra / df.pu_venda - 1).mean() > 0


def test_a_serie_cobre_todos_os_meses_da_janela():
    df = pd.read_parquet(CURATED / "tesouro_ipca.parquet")
    meses = set(df.date.dt.to_period("M"))
    assert all(m in meses for m in pd.period_range("2006-01", "2025-12", freq="M"))


def test_a_rolagem_custa_e_nao_rende():
    """Comprar ao preço de compra e marcar ao de venda tem de reduzir o nível."""
    df = pd.read_parquet(CURATED / "tesouro_ipca.parquet")
    _, rolagens = build_index(df, "mais_longo")
    assert len(rolagens) == 3
    assert all(r.custo_pct > 0 for r in rolagens)


def test_regra_desconhecida_falha_em_vez_de_cair_no_padrao():
    df = pd.read_parquet(CURATED / "tesouro_ipca.parquet")
    with pytest.raises(ValueError, match="regra"):
        build_index(df, "a_mais_curta")


def test_carregar_ate_o_vencimento_rola_menos_e_gasta_menos():
    """As duas regras existem porque a escolha muda o resultado — e isso é medido."""
    c = comparar_regras(CURATED).set_index("regra")
    assert set(c.index) == set(REGRAS)
    assert c.loc["ate_o_vencimento", "rolagens"] < c.loc["mais_longo", "rolagens"]
    assert c.loc["ate_o_vencimento", "custo_de_rolagem_pp"] < \
           c.loc["mais_longo", "custo_de_rolagem_pp"]


def test_o_indice_troca_de_titulo_ao_menos_uma_vez():
    """Vinte anos sem rolagem significaria que o vencimento de 2024 foi ignorado."""
    tr = pd.read_parquet(CURATED / "tesouro_total_return.parquet")
    assert tr.maturity.nunique() >= 2
    assert len(tr) == 241


def test_a_renda_fixa_e_regua_e_nao_ativo_do_universo():
    """Entrar nas carteiras seria acréscimo pós-resultado ao universo congelado."""
    assert len(RENDA_FIXA) == 1
    assert RENDA_FIXA[0].ticker == "IPCAP"
    for nome in ("capital_allocators", "passive_etfs", "passive_indices"):
        pesos = tomllib.loads(
            (STRATEGIES / f"{nome}.toml").read_text())["strategy"]["weights"]
        assert "IPCAP" not in [w["ticker"] for w in pesos]
    assert BY_TICKER["IPCAP"].withholding_tax == BY_TICKER["CDI"].withholding_tax \
        if "CDI" in BY_TICKER else BY_TICKER["IPCAP"].withholding_tax == 0.0


def test_o_titulo_longo_inverte_entre_tempo_e_dinheiro():
    """O achado desta perna: retorno alto e resultado ruim convivendo.

    Se esta inversão sumir, ou a série mudou ou a métrica mudou — e nos dois casos
    o texto do README passa a mentir.
    """
    t = tempo_contra_dinheiro(RESULTS, CURATED).set_index("estrategia")
    assert t.loc["tesouro_ipca", "real_aa"] > t.loc["cdi", "real_aa"]
    assert t.loc["tesouro_ipca", "reais_por_real"] < t.loc["cdi", "reais_por_real"]
    assert any(f.startswith("tesouro_ipca") for f in
               inversoes(tempo_contra_dinheiro(RESULTS, CURATED)))


def test_a_sequencia_explica_a_inversao():
    """O título brilha no terço em que o investidor tinha pouco dinheiro."""
    s = sequencia(RESULTS, CURATED).set_index("estrategia")
    cols = [f"{a[:4]}-{b[:4]}" for a, b in PERIODOS]
    assert s.loc["tesouro_ipca", cols[0]] > s.loc["tesouro_ipca", cols[-1]]
    # E os allocators são a imagem espelhada — é isso que torna a ressalva simétrica.
    assert s.loc["capital_allocators", cols[0]] < s.loc["capital_allocators", cols[-1]]
