"""Testes do coletor de proventos japoneses.

Os três erros que este coletor precisa impedir são erros silenciosos: linha de
outra tabela com contagem parecida, coluna deslocada, e fator de desdobramento
aplicado no sentido errado. Nenhum deles aparece como exceção — todos aparecem
como um número plausível.
"""

import pandas as pd
import pytest
from capallo.ingest.jp_reports import (
    SOURCES,
    _values,
    conferir_sobreposicao,
    split_factor,
)


def test_rotulo_precisa_terminar_no_rotulo():
    """`Dividend` não pode casar com `Dividend income`, que fica na mesma página."""
    assert _values("Dividend 42.5 52.5 70 85 100 0.69", "Dividend") == [42.5, 52.5, 70, 85, 100, 0.69]
    assert _values("Dividend income 63.9 85.7 16.7", "Dividend") is None
    assert _values("Dividend payout ratio 42.7% 18.7%", "Dividend") is None


def test_prefixo_de_nota_e_unidade_nao_vira_numero():
    """`*4` e `(yen, US dollars)` precedem a primeira coluna e não são dados."""
    linha = "Cash dividends per share (yen, US dollars)*4 23.33 16.67 26.67"
    assert _values(linha, "Cash dividends per share") == [23.33, 16.67, 26.67]


def test_pontilhado_de_sumario_nao_vira_numero():
    linha = "Cash dividends per share (yen, U.S. dollar) . . . . . 35.00 46.00"
    assert _values(linha, "Cash dividends per share") == [35.00, 46.00]


def test_separador_de_milhar_nao_quebra_o_numero():
    assert _values("Cash Dividends 1,234 56", "Cash Dividends") == [1234.0, 56.0]


def _amostra(antes: dict[int, float], depois: dict[int, float]) -> pd.DataFrame:
    linhas = [{"ticker": "8058", "fiscal_year": a, "dps": v, "source": "antes.pdf",
               "post_split": False} for a, v in antes.items()]
    linhas += [{"ticker": "8058", "fiscal_year": a, "dps": v, "source": "depois.pdf",
                "post_split": True} for a, v in depois.items()]
    return pd.DataFrame(linhas)


def test_split_medido_bate_com_o_declarado():
    df = _amostra({2019: 125.0, 2020: 132.0}, {2019: 41.67, 2020: 44.00})
    assert split_factor(df, "8058") == 3.0


def test_split_divergente_do_declarado_interrompe_a_coleta():
    """Se a sobreposição indicasse 2:1 onde a nota declara 3:1, o dado está errado."""
    df = _amostra({2019: 125.0, 2020: 132.0}, {2019: 62.5, 2020: 66.0})
    with pytest.raises(ValueError, match="contradiz"):
        split_factor(df, "8058")


def test_sem_sobreposicao_nao_ha_fator():
    df = _amostra({2019: 125.0}, {2021: 44.67})
    with pytest.raises(LookupError):
        split_factor(df, "8058")


def test_sobreposicao_discordante_e_reportada():
    """Coluna deslocada em um documento aparece como divergência no ano comum."""
    df = pd.DataFrame([
        {"ticker": "8031", "fiscal_year": 2019, "dps_ajustado": 40.0, "source": "a.pdf"},
        {"ticker": "8031", "fiscal_year": 2019, "dps_ajustado": 27.5, "source": "b.pdf"},
    ])
    assert conferir_sobreposicao(df) == ["8031 2019: a.pdf=40, b.pdf=27.5"]
    assert conferir_sobreposicao(df.head(1)) == []


def test_anos_repetidos_na_fonte_sao_declarados_e_nao_deduzidos():
    """A Mitsubishi repete 2013 na transição de US GAAP para IFRS.

    Um intervalo `range(2011, 2022)` leria 2014 na coluna que é 2013 e deslocaria
    toda a metade direita da tabela — daí `years` ser lista explícita.
    """
    src = next(s for s in SOURCES if s.filename == "mc_ar2020.pdf")
    assert src.years.count(2013) == 2
    assert len(src.years) == 11
