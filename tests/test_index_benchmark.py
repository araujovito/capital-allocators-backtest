"""Testes do experimento Index Benchmark.

O que precisa de guarda aqui não é a aritmética do prêmio — é o conjunto de
premissas que fazem a comparação significar alguma coisa: alíquota igual dos dois
lados, série de índice classificada e não suposta, e os dois tipos de experimento
não se misturando.
"""

from pathlib import Path

import pandas as pd
import pytest
import tomllib
from capallo.analysis.index_benchmark import TRIOS, comparar, veredito
from capallo.ingest.indices import MSCI_CODES, _mensal
from capallo.universe import BY_TICKER, INDICE_DO_ETF, INDICES, PASSIVE_ETFS

CURATED, RESULTS, STRATEGIES = Path("data/curated"), Path("data/results"), Path("strategies")


def test_indice_e_etf_da_mesma_regiao_carregam_a_mesma_aliquota():
    """A comparação mede custo de produto; alíquota diferente mediria imposto."""
    for etf, indice in INDICE_DO_ETF.items():
        assert BY_TICKER[etf].withholding_tax == BY_TICKER[indice].withholding_tax, etf


def test_ha_um_indice_para_cada_etf_e_da_mesma_regiao():
    assert len(INDICES) == len(PASSIVE_ETFS) == 4
    for etf, indice in INDICE_DO_ETF.items():
        assert BY_TICKER[etf].region == BY_TICKER[indice].region
        assert BY_TICKER[etf].exposure_currency == BY_TICKER[indice].exposure_currency


def test_as_estrategias_de_indice_nao_contem_nenhum_etf():
    """Um ticker de ETF sobrevivendo num TOML de índice mediria o produto de novo."""
    tickers_etf = {a.ticker for a in PASSIVE_ETFS}
    for nome in ("br_index", "us_index", "eu_index", "jp_index", "passive_indices"):
        texto = (STRATEGIES / f"{nome}.toml").read_text()
        assert not (tickers_etf & set(_tickers(texto))), nome
        assert set(_tickers(texto)) <= {a.ticker for a in INDICES}, nome


def test_cada_indice_so_difere_do_seu_etf_no_ticker():
    """Se qualquer outra regra divergisse, a diferença mediria isso, e não o custo.

    A comparação é par a par — `br_index` contra `br_etf` — porque as estratégias
    regionais e a global têm regras de rebalanceamento diferentes entre si, e
    comparar todas contra a global acusaria uma divergência que não existe.
    """
    pares = (("br_index", "br_etf"), ("us_index", "us_etf"), ("eu_index", "eu_etf"),
             ("jp_index", "jp_etf"), ("passive_indices", "passive_etfs"))
    for indice, etf in pares:
        a, b = _regras(indice), _regras(etf)
        assert a == b, f"{indice} difere de {etf} em {_diferencas(a, b)}"


def _carregar(nome: str) -> dict:
    return tomllib.loads((STRATEGIES / f"{nome}.toml").read_text())["strategy"]


def _tickers(texto: str) -> list[str]:
    return [l.split("=")[1].strip().strip('"')
            for l in texto.splitlines() if l.strip().startswith("ticker")]


def _regras(nome: str) -> dict:
    """Tudo o que a estratégia declara, menos o nome e a lista de ativos."""
    s = _carregar(nome)
    return {k: v for k, v in s.items() if k not in ("name", "weights")}


def _diferencas(a: dict, b: dict) -> dict:
    return {k: (a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k)}


def test_a_variante_bruta_do_indice_supera_a_de_preco():
    """Bruto reinveste dividendo e preço não; trocadas, o sinal se inverteria."""
    df = pd.read_parquet(CURATED / "indices.parquet")
    for ticker in MSCI_CODES:
        g = df[df.ticker == ticker]
        assert _mensal(g, "close_adj").iloc[-1] / _mensal(g, "close_adj").iloc[0] > \
               _mensal(g, "close_px").iloc[-1] / _mensal(g, "close_px").iloc[0], ticker


def test_o_indice_brasileiro_nao_leva_retencao_e_os_outros_levam():
    """§4 congelou Brasil em zero; inventar simetria seria pior que a assimetria."""
    df = pd.read_parquet(CURATED / "indices.parquet")
    for ticker, g in df.groupby("ticker"):
        g = g.sort_values("date")
        igual = float(g.close_net.iloc[-1]) == pytest.approx(float(g.close_adj.iloc[-1]))
        assert igual == (BY_TICKER[ticker].withholding_tax == 0), ticker


def test_custo_do_produto_e_exatamente_o_encolhimento_do_premio():
    """A identidade que dá sentido à tabela: prêmio_ETF − prêmio_índice = custo."""
    t = comparar(RESULTS, CURATED)
    assert (t.premio_vs_etf_pp - t.premio_vs_indice_pp).sub(
        t.custo_do_produto_pp).abs().max() < 1e-9


def test_o_veredito_aponta_a_inversao_americana():
    """A descoberta do experimento não pode sumir numa mudança de formatação."""
    t = comparar(RESULTS, CURATED)
    eua = t[t.regiao == "EUA"].iloc[0]
    assert eua.premio_vs_etf_pp > 0 > eua.premio_vs_indice_pp
    assert any(f.startswith("EUA") for f in veredito(t))


def test_a_perna_ativa_e_a_mesma_nas_duas_comparacoes():
    """O experimento troca só a referência; trocar os dois lados não mediria nada."""
    assert len(TRIOS) == 5
    t = comparar(RESULTS, CURATED)
    from capallo.analysis.scoreboard import evaluate
    for regiao, alloc, _, _ in TRIOS:
        esperado = evaluate(RESULTS / f"{alloc}.csv", CURATED)["retorno_real_aa"]
        assert float(t[t.regiao == regiao].alloc_aa.iloc[0]) == pytest.approx(esperado)
