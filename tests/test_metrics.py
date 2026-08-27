"""Testes das metricas, todos com serie sintetica de resultado conhecido.

Dado real da plausibilidade, nao correcao: um max drawdown errado em tres pontos
percentuais nao destoa de nada. Aqui a resposta certa e sabida de antemao.
"""

import numpy as np
import pandas as pd
import pytest

from capallo.analysis import metrics as m


def serie(valores, inicio="2006-01"):
    idx = pd.period_range(inicio, periods=len(valores), freq="M")
    return pd.Series([float(v) for v in valores], index=idx)


def test_max_drawdown_de_queda_conhecida():
    # 100 -> 60 e uma queda de 40%
    w = serie([100, 80, 60, 70, 90])
    assert m.max_drawdown(w) == pytest.approx(-0.40)


def test_sem_queda_o_drawdown_e_zero():
    assert m.max_drawdown(serie([10, 20, 30, 40])) == pytest.approx(0.0)


def test_tempo_de_recuperacao_conta_do_topo():
    # topo no indice 0, fundo no 2, recupera no 4: quatro meses
    w = serie([100, 80, 60, 80, 100])
    assert m.recovery_months(w) == 4


def test_serie_que_nao_recupera_devolve_none():
    """Nao recuperar e informacao, nao ausencia dela."""
    assert m.recovery_months(serie([100, 50, 60, 70])) is None


def test_aporte_nao_e_confundido_com_retorno():
    # patrimonio vai de 100 a 200, mas 100 foi aporte: retorno zero
    w = serie([100, 200])
    c = serie([0, 100])
    r = m.monthly_returns(w, c)
    assert r.iloc[0] == pytest.approx(0.0)

    # sem informar aporte, a mesma serie aparenta +100%
    assert m.monthly_returns(w).iloc[0] == pytest.approx(1.0)


def test_retorno_anualizado_de_dobra_em_dois_anos():
    # 24 meses de retorno constante que dobram o capital
    taxa = 2 ** (1 / 24) - 1
    r = pd.Series([taxa] * 24, index=pd.period_range("2006-01", periods=24, freq="M"))
    assert m.annualized_return(r) == pytest.approx(2 ** 0.5 - 1, rel=1e-9)


def test_volatilidade_de_serie_constante_e_zero():
    r = pd.Series([0.01] * 12, index=pd.period_range("2006-01", periods=12, freq="M"))
    assert m.volatility(r) == pytest.approx(0.0)


def test_sharpe_zero_quando_retorno_iguala_o_livre_de_risco():
    """Sem excesso e sem risco o Sharpe e zero, nao indefinido."""
    idx = pd.period_range("2006-01", periods=12, freq="M")
    r = pd.Series([0.01] * 12, index=idx)
    rf = pd.Series([0.01] * 12, index=idx)
    assert m.sharpe(r, rf) == 0.0


def test_sortino_ignora_oscilacao_positiva():
    """Duas series com a mesma media: a que so oscila para cima tem Sortino melhor."""
    idx = pd.period_range("2006-01", periods=12, freq="M")
    rf = pd.Series([0.0] * 12, index=idx)
    so_cima = pd.Series([0.02, 0.0] * 6, index=idx)
    com_queda = pd.Series([0.03, -0.01] * 6, index=idx)
    assert so_cima.mean() == pytest.approx(com_queda.mean())
    assert m.sortino(so_cima, rf) > m.sortino(com_queda, rf)


def test_sortino_sem_mes_negativo_e_infinito():
    """Sem downside o risco medido e zero: infinito diz isso, NaN diria 'nao sei'."""
    idx = pd.period_range("2006-01", periods=12, freq="M")
    rf = pd.Series([0.0] * 12, index=idx)
    assert m.sortino(pd.Series([0.01] * 12, index=idx), rf) == float("inf")


def test_volatilidade_penaliza_igual_para_cima_e_para_baixo():
    """Contraste com o Sortino: o desvio-padrao nao distingue direcao."""
    idx = pd.period_range("2006-01", periods=12, freq="M")
    so_cima = pd.Series([0.02, 0.0] * 6, index=idx)
    com_queda = pd.Series([0.02, 0.0] * 6, index=idx) - 0.01
    assert m.volatility(so_cima) == pytest.approx(m.volatility(com_queda))


def test_janela_movel_de_um_ano():
    # 12 meses de retorno constante que dobram o capital
    taxa = 2 ** (1 / 12) - 1
    r = pd.Series([taxa] * 12, index=pd.period_range("2006-01", periods=12, freq="M"))
    janelas = m.rolling_window_returns(r, 1)
    assert len(janelas) == 1
    assert janelas.iloc[0] == pytest.approx(1.0)


def test_janela_maior_que_a_serie_devolve_vazio():
    assert m.rolling_window_returns(serie([0.01, 0.01, 0.01]), 5).empty


def test_janela_movel_nao_confunde_aporte_com_retorno():
    """Patrimonio que so cresce por aporte tem retorno zero em qualquer janela.

    Calcular a janela sobre o patrimonio daria numeros absurdos: no comeco o
    aporte e enorme diante da base acumulada.
    """
    w = serie([1000 * (i + 1) for i in range(13)])   # +1000 por mes, sem render
    c = serie([1000] * 13)
    r = m.monthly_returns(w, c)
    janelas = m.rolling_window_returns(r, 1)
    assert len(janelas) == 1
    assert janelas.iloc[0] == pytest.approx(0.0, abs=1e-12)

    # sobre o patrimonio, a mesma serie aparentaria +1.200%
    ingenuo = (w.iloc[12] / w.iloc[0]) - 1
    assert ingenuo == pytest.approx(12.0)


def test_sortino_usa_downside_deviation_e_nao_desvio_dos_negativos():
    """Quedas de tamanho constante tem desvio-padrao zero entre si, mas sao risco.

    Implementar Sortino como desvio-padrao do subconjunto negativo faria esta
    serie parecer livre de risco de baixa.
    """
    idx = pd.period_range("2006-01", periods=12, freq="M")
    rf = pd.Series([0.0] * 12, index=idx)
    quedas_iguais = pd.Series([0.03, -0.01] * 6, index=idx)
    assert np.isfinite(m.sortino(quedas_iguais, rf))
    assert m.sortino(quedas_iguais, rf) > 0


def test_sharpe_de_estrategia_contra_ela_mesma_e_zero():
    """Excesso 0/0 nao pode virar um numero de aparencia plausivel.

    Com arredondamento de dataset o excesso fica em ~1e-11 em vez de zero, e a
    divisao pela media de ~1e-12 devolvia Sharpe -0,10.
    """
    idx = pd.period_range("2006-01", periods=24, freq="M")
    rng = np.random.default_rng(7)
    cdi = pd.Series(rng.uniform(0.004, 0.012, 24), index=idx)
    ruido = pd.Series(rng.normal(0, 1e-11, 24), index=idx)
    assert m.sharpe(cdi + ruido, cdi) == 0.0
    assert m.sortino(cdi + ruido, cdi) == 0.0


def test_normalize_table_expande_rowspan():
    """Sem expandir rowspan, as colunas deslizam e o valor lido e o da coluna vizinha."""
    from lxml import html as LH

    from capallo.ingest.irbank import normalize_table

    doc = LH.fromstring("""
      <table>
        <tr><th>ano</th><th>meio</th><th>fim</th><th>ajustado</th></tr>
        <tr><td rowspan="2">2010</td><td>17</td><td>21</td><td>12.67</td></tr>
        <tr><td>26</td><td>39</td><td>21.67</td></tr>
      </table>""")
    grid = normalize_table(doc.xpath("//table")[0])
    assert grid[0] == ["ano", "meio", "fim", "ajustado"]
    assert grid[1] == ["2010", "17", "21", "12.67"]
    # a segunda linha herda o ano e mantem o alinhamento das demais colunas
    assert grid[2] == ["2010", "26", "39", "21.67"]


def test_gbl_extrai_dez_anos_em_ordem_decrescente(tmp_path, monkeypatch):
    """A tabela do relatorio lista os anos do mais recente para o mais antigo."""
    import pandas as pd

    from capallo.ingest import gbl_reports as g

    class FakePage:
        def extract_text(self):
            return ("Consolidated result 1 2 3\n"
                    "Gross dividend (in EUR) 2.86 2.79 2.72 2.65 2.60 2.54 2.42 2.30 2.09 1.90\n")

    class FakeReader:
        def __init__(self, _path):
            self.pages = [FakePage()]

    monkeypatch.setattr(g, "PdfReader", FakeReader)
    df = g.extract(tmp_path / "x.pdf", 2015)
    assert list(df.fiscal_year) == list(range(2015, 2005, -1))
    assert df[df.fiscal_year == 2006].gross_dividend.iloc[0] == pytest.approx(1.90)
    assert df[df.fiscal_year == 2015].gross_dividend.iloc[0] == pytest.approx(2.86)


def test_gbl_validate_flagra_desalinhamento(tmp_path):
    """Salto acima de 3x entre anos consecutivos denuncia coluna errada."""
    import pandas as pd

    from capallo.ingest.gbl_reports import validate

    anos = list(range(2006, 2026))
    valores = [2.0] * 20
    valores[10] = 20.0
    pd.DataFrame({"ticker": "GBLB", "fiscal_year": anos, "gross_dividend": valores}
                 ).to_parquet(tmp_path / "be_dividends.parquet")
    assert any("implausível" in p for p in validate(tmp_path))
