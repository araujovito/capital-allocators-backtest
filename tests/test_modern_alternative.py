"""Testes do experimento Modern Alternative.

O contrafactual é o lugar do estudo onde é mais fácil enganar-se a favor da
própria tese: basta escolher o produto moderno errado, ou dar a ele uma taxa
generosa. As guardas aqui são sobre isso — e sobre a §7, que proíbe misturar
resultados de tipos de experimento diferentes.
"""

from pathlib import Path

import pandas as pd
import pytest
import tomllib
from capallo.analysis.modern_alternative import (
    ATIVA,
    MODERNA,
    REFERENCIAS,
    comparar,
    premio_sobre_a_alternativa_moderna,
)
from capallo.transform.build_indices import TER_MODERN, build
from capallo.universe import BY_TICKER, INDICES, MODERN_ALTERNATIVE

CURATED, RESULTS, STRATEGIES = Path("data/curated"), Path("data/results"), Path("strategies")


def test_o_produto_moderno_carrega_a_mesma_retencao_de_todo_ativo_estrangeiro():
    """Alíquota mais leve que a das outras pernas facilitaria o contrafactual."""
    assert len(MODERN_ALTERNATIVE) == 1
    acwi = MODERN_ALTERNATIVE[0]
    assert acwi.ticker == "ACWI"
    assert acwi.withholding_tax == BY_TICKER["IVV"].withholding_tax == 0.30


def test_o_produto_moderno_paga_taxa_e_os_indices_nao():
    """Índice é piso teórico e não cobra; produto é comprável e cobra.

    Trocar isso — dar taxa ao índice ou isentar o produto — inverteria o sentido
    dos dois experimentos de uma vez.
    """
    df = pd.read_parquet(CURATED / "indices.parquet")
    assert set(df[df.grupo == "modern"].ticker) == {"ACWI"}
    assert (df[df.grupo == "modern"].ter > 0).all()
    assert (df[df.grupo == "index"].ter == 0).all()
    assert set(df[df.grupo == "index"].ticker) == {a.ticker for a in INDICES}


def test_a_taxa_derruba_o_retorno_e_nao_o_contrario():
    """Sinal trocado no expoente faria a taxa virar bônus, e nada acusaria."""
    df = build(CURATED, ter_modern=0.02)
    g = df[df.ticker == "ACWI"].sort_values("date")
    caro = float(g.close_net.iloc[-1] / g.close_net.iloc[0])
    barato_df = build(CURATED, ter_modern=TER_MODERN)
    b = barato_df[barato_df.ticker == "ACWI"].sort_values("date")
    barato = float(b.close_net.iloc[-1] / b.close_net.iloc[0])
    assert caro < barato


def test_a_taxa_base_esta_na_faixa_declarada_dos_produtos_reais():
    """Premissa declarada; um valor fora da faixa deixaria de ser conservador."""
    assert 0.0006 <= TER_MODERN <= 0.0050


def test_a_estrategia_moderna_so_difere_da_passiva_no_ativo_e_no_rebalanceamento():
    """Janela e aporte diferentes fariam a diferença medir período, não produto."""
    def regras(nome):
        s = tomllib.loads((STRATEGIES / f"{nome}.toml").read_text())["strategy"]
        return {k: s[k] for k in ("start", "end", "base_currency", "dividends")} | s["contribution"]

    assert regras("modern_alternative") == regras("passive_etfs")
    pesos = tomllib.loads(
        (STRATEGIES / "modern_alternative.toml").read_text()
    )["strategy"]["weights"]
    assert [w["ticker"] for w in pesos] == ["ACWI"]


def test_cada_referencia_declara_de_que_experimento_veio():
    """A §7 proíbe misturar resultados; o rótulo é o que impede a mistura."""
    tipos = {tipo for _, _, tipo in REFERENCIAS}
    assert "Modern Alternative (§7)" in tipos
    assert "Historical Reality" in tipos
    assert "Index Benchmark (§7)" in tipos
    assert all(r.experimento for _, r in comparar(RESULTS, CURATED).iterrows())


def test_o_contrafactual_moderno_e_mais_duro_que_o_etf_de_2006():
    """Se não fosse, o experimento não estaria testando nada novo.

    O ACWI é ponderado por capitalização, então carregou os Estados Unidos na
    proporção em que o mercado os carregou — justamente o que a perna passiva de
    pesos iguais subponderou no período em que os EUA ganharam.
    """
    t = comparar(RESULTS, CURATED).set_index("estrategia")
    assert t.loc["Modern Alternative — ACWI global", "real_aa"] > \
           t.loc["ETFs de 2006, pesos iguais", "real_aa"]


def test_o_premio_e_medido_contra_a_alternativa_moderna_e_nao_contra_o_etf():
    from capallo.analysis.scoreboard import evaluate

    p = premio_sobre_a_alternativa_moderna(RESULTS, CURATED)
    a = evaluate(RESULTS / f"{ATIVA}.csv", CURATED)["retorno_real_aa"]
    b = evaluate(RESULTS / f"{MODERNA}.csv", CURATED)["retorno_real_aa"]
    assert p["premio_pp"] == pytest.approx((a - b) * 100)
    assert set(p["vitorias"]) == {1, 3, 5, 10}
