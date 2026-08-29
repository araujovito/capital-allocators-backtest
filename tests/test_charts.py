"""Testes da camada de gráficos.

Um gráfico não se prova em teste: quem julga se ele comunica é quem olha. O que
dá para trancar aqui é o que **silenciosamente** apodrece — a paleta perdendo um
slot, o rótulo saindo em formato americano, a métrica desenhada divergindo da
métrica tabelada, e a lista de allocators saindo de sincronia com o universo.
"""

import pandas as pd
import pytest
from capallo.analysis.charts import (
    ALLOCATORS,
    CLARO,
    ESCURO,
    FIGURAS,
    ORDEM_REGIOES,
    REGIOES,
    _num,
    janelas_moveis,
    poder_de_compra,
)
from capallo.analysis.scoreboard import evaluate
from capallo.universe import CAPITAL_ALLOCATORS


def test_numero_sai_no_formato_brasileiro():
    """O estudo é escrito em português; `2.05x` seria erro de formato, não estilo."""
    assert _num(2.05, 2, "x") == "2,05x"
    assert _num(-1.5, 1) == "-1,5"
    assert _num(100.0, 0, "%") == "100%"
    assert _num(1234.5, 1) == "1 234,5"


def test_os_dois_temas_tem_a_mesma_quantidade_de_slots():
    """O tema escuro é a mesma paleta re-escalonada, não outra paleta."""
    assert len(CLARO.series) == len(ESCURO.series) == 5
    assert len(set(CLARO.series)) == len(CLARO.series)
    assert len(set(ESCURO.series)) == len(ESCURO.series)
    assert CLARO.surface != ESCURO.surface


def test_a_lista_de_allocators_acompanha_o_universo():
    """Se o universo mudasse, o halter pintaria um allocator com a cor de ETF."""
    assert ALLOCATORS == {a.ticker for a in CAPITAL_ALLOCATORS}


def test_as_regioes_das_figuras_sao_as_mesmas_em_toda_parte():
    """Cor segue a entidade: uma região não pode trocar de slot entre figuras."""
    assert len(REGIOES) == 4
    assert set(ORDEM_REGIOES) - {"Global"} == {"Brasil", "EUA", "Europa", "Japão"}
    assert ORDEM_REGIOES[-1] == "Global"


def test_toda_figura_declarada_tem_um_proposito_escrito():
    """`FIGURAS` é o que o README consome; entrada muda sem legenda seria silêncio."""
    assert len(FIGURAS) == 4
    assert all(v and not v.endswith(".") for v in FIGURAS.values())


def test_a_curva_desenhada_termina_no_numero_da_tabela(tmp_path):
    """A figura e o placar do README têm de contar a mesma coisa.

    A curva começa perto de 1,00x — no primeiro mês o investidor só tem o que
    aportou — e termina exatamente no `reais_por_real` que o placar publica. Se
    divergirem, uma das duas está deflacionando errado.
    """
    from pathlib import Path

    res, cur = Path("data/results/capital_allocators.csv"), Path("data/curated")
    curva = poder_de_compra(res, cur)
    assert curva.iloc[0] == pytest.approx(1.0, abs=0.05)
    assert float(curva.iloc[-1]) == pytest.approx(
        evaluate(res, cur)["reais_por_real"], rel=1e-9
    )


def test_gera_os_dois_temas_em_arquivos_separados(tmp_path):
    """Fumaça: a figura renderiza de ponta a ponta e sai nos dois modos."""
    from pathlib import Path

    saidas = janelas_moveis(Path("data/results"), tmp_path)
    assert [p.name for p in saidas] == ["janelas-moveis-light.png",
                                        "janelas-moveis-dark.png"]
    assert all(p.stat().st_size > 5_000 for p in saidas)


def test_win_rate_alimenta_a_matriz_com_percentuais_plausiveis():
    """Uma fração virando percentual duas vezes daria 0,49% em vez de 49%."""
    from pathlib import Path

    from capallo.analysis.scoreboard import win_rate

    v = win_rate(Path("data/results/eu_allocators.csv"),
                 Path("data/results/eu_etf.csv"), 10) * 100
    assert 0 <= v <= 100
    assert v > 50, "a Europa é a região em que a gestão ativa mais venceu"


def test_a_serie_do_grafico_e_uma_serie_mensal_continua():
    """Buraco no meio viraria linha reta atravessando anos, sem aviso."""
    from pathlib import Path

    curva = poder_de_compra(Path("data/results/cdi.csv"), Path("data/curated"))
    assert isinstance(curva.index, pd.PeriodIndex)
    assert len(curva) == 240
    assert curva.index.is_monotonic_increasing
