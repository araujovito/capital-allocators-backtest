"""Testes da classificação da série japonesa.

O que está sendo trancado aqui não é o coletor: é a resposta à pergunta *"esta
série já embute dividendo?"*. Errar essa classificação custou vinte anos de
provento no INVE-B, e no Japão custaria o dobro — contagem dupla, na região de
maior prêmio do estudo.
"""

import pandas as pd
from capallo.ingest.kabutan import veredito_da_serie


def _conf(razoes, ticker="8058"):
    return pd.DataFrame({
        "ticker": ticker,
        "exercicio": range(2006, 2006 + len(razoes)),
        "tipo": "year_end_close",
        "publicado": 1000.0,
        "coletado": [1000.0 * r for r in razoes],
        "razao": razoes,
        "fonte": "teste",
    })


def test_serie_na_escala_do_preco_publicado_passa():
    """Ruído de método — média mensal contra média de pregões — não é erro."""
    assert veredito_da_serie(_conf([1.040, 1.017, 1.019, 0.964, 1.005])) == []


def test_serie_ajustada_por_dividendo_e_reprovada():
    """É este o cenário que o teste existe para pegar: contagem dupla do provento.

    Vinte anos a ~3,5% de yield reinvestido derrubam o começo da série para perto
    da metade do preço que a companhia publicou. Nenhuma tolerância de método
    cobre isso, e é essa distância que torna o teste conclusivo onde o teste de
    data-ex não foi.
    """
    problemas = veredito_da_serie(_conf([0.52, 0.51, 0.53, 0.50, 0.52]))
    assert len(problemas) == 1
    assert "preço puro" in problemas[0]


def test_cada_ativo_e_julgado_separadamente():
    """Uma fonte pode acertar um papel e errar o outro; a média conjunta esconderia."""
    conf = pd.concat([_conf([1.00] * 5, "8058"), _conf([0.52] * 5, "8031")])
    problemas = veredito_da_serie(conf)
    assert len(problemas) == 1
    assert problemas[0].startswith("8031")


def test_desvio_na_borda_da_tolerancia():
    """A tolerância é folgada de propósito, mas não é ilimitada."""
    assert veredito_da_serie(_conf([1.05] * 4)) == []
    assert len(veredito_da_serie(_conf([1.07] * 4))) == 1


def test_referencia_manual_cobre_os_dois_ativos_na_ponta_da_janela():
    """O arquivo de referência perde o poder se sair da borda: é lá que o sinal é 2x."""
    ref = pd.read_csv("data/manual/jp_reported_prices.csv", comment="#")
    assert set(ref.ticker.astype(str)) == {"8058", "8031"}
    assert ref.fiscal_year.max() <= 2012, "referência longe da borda perde poder de teste"
    assert set(ref.split_factor) <= {2, 3}
    assert (ref.value_jpy > 0).all()
