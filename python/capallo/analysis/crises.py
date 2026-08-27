"""Comportamento das estratégias em recortes de crise.

`docs/methodology.md`, seção 6: as regras **não mudam** durante crises; apenas se
observa. Este módulo observa — e começa verificando que a promessa foi cumprida.

## As janelas são datadas por terceiros

Escolher o início e o fim de uma crise depois de ver o resultado é escolher o
resultado. Por isso nenhuma janela aqui foi datada pelo estudo: todas vêm de
cronologia publicada por quem tem mandato para datá-la — o NBER nos Estados
Unidos, o CODACE/FGV no Brasil, o CEPR na área do euro. Onde não existe árbitro
oficial, a janela é o intervalo entre eventos com data pública e inequívoca, e a
fonte fica registrada em `fonte` ao lado da janela.

## Retorno de janela é medido sobre retorno, não sobre patrimônio

Num estudo de aportes mensais o patrimônio cresce porque o investidor deposita.
Dentro de uma crise isso inverte a leitura: quem aporta durante a queda pode
terminar com mais dinheiro do que começou e parecer que não caiu. As janelas são
calculadas sobre o índice de retorno de `metrics.return_index`, que já expurga o
aporte.

## Em termos reais, e a partir do nível de véspera

Duas escolhas que mudam o número. O retorno da janela é **real**: no recorte da
recessão brasileira a inflação acumulou 22%, e uma carteira nominalmente positiva
pode ter destruído poder de compra. E o nível de entrada é o do mês **anterior**
ao início da janela: tomar o primeiro mês de dentro como base já engoliria a queda
desse mês, que é justamente a que se quer medir.

## O drawdown da janela não é o drawdown da série

`max_drawdown` global mede a pior queda desde qualquer topo. Aqui a pergunta é
outra: quanto se perdeu **dentro** daquele intervalo, a partir do nível de
entrada. As duas coincidem quando a crise contém o pior momento da série, e
divergem quando não contém — e é a segunda que responde "como foi atravessar
2011".
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from capallo.analysis import metrics as m
from capallo.analysis.scoreboard import _deflator, _load_result


@dataclass(frozen=True)
class Crise:
    nome: str
    inicio: str
    fim: str
    fonte: str


#: Datadas por terceiros, antes de olhar qualquer resultado.
CRISES: tuple[Crise, ...] = (
    Crise("Crise financeira global", "2007-12", "2009-06",
          "NBER: recessão americana de dez/2007 a jun/2009"),
    Crise("Crise da dívida do euro", "2011-08", "2013-02",
          "CEPR: recessão da área do euro de 3T2011 a 1T2013"),
    Crise("Recessão brasileira", "2014-04", "2016-12",
          "CODACE/FGV: recessão brasileira de 2T2014 a 4T2016"),
    Crise("COVID-19", "2020-02", "2020-04",
          "NBER: recessão americana de fev/2020 a abr/2020"),
    Crise("Aperto monetário global", "2022-01", "2022-12",
          "ano-calendário de 2022, em que Fed, BCE e Copom subiram juros"),
)

#: Parâmetros que a metodologia congela antes do backtest. Se algum diferir entre
#: estratégias, a comparação entre elas deixa de ser sobre a carteira.
CAMPOS_CONGELADOS = ("start", "end", "base_currency", "dividends")


def regras_congeladas(strategies: Path) -> list[str]:
    """Confere que as estratégias diferem **só** na composição da carteira.

    A afirmação "as regras não mudam durante a crise" não vale como texto: se um
    arquivo de estratégia tivesse outra janela ou outra regra de aporte, o recorte
    de crise compararia carteiras diferentes em condições diferentes, e nada aqui
    denunciaria isso. Esta função é a checagem que sustenta a frase.
    """
    import tomllib

    base: dict[str, object] = {}
    problemas = []
    for path in sorted(strategies.glob("*.toml")):
        with path.open("rb") as fh:
            s = tomllib.load(fh)["strategy"]
        atual = {k: s.get(k) for k in CAMPOS_CONGELADOS}
        atual["contribution"] = s.get("contribution")
        if not base:
            base, origem = atual, path.name
            continue
        for chave, valor in atual.items():
            if valor != base[chave]:
                problemas.append(
                    f"{path.name}: '{chave}' difere de {origem} ({valor} vs {base[chave]})"
                )
    return problemas


def _indice(results: Path, curated: Path, strategy: str) -> pd.Series:
    """Índice de retorno **real**, com o aporte expurgado e a inflação descontada."""
    df = _load_result(results / f"{strategy}.csv")
    nominal = m.monthly_returns(df.value, df.contribution)
    ipca = (1 / _deflator(curated)).pct_change().reindex(nominal.index)
    return m.return_index(((1 + nominal) / (1 + ipca) - 1).dropna())


def janela(indice: pd.Series, crise: Crise) -> dict:
    """Retorno, queda e recuperação de uma estratégia dentro de uma crise.

    `recuperacao_meses` conta do fim da janela até o índice voltar ao nível de
    **entrada** na crise, e olha a série inteira depois disso — a recuperação é um
    fato posterior à crise, não um fato dentro dela. ``None`` significa que a série
    termina sem recuperar, que é informação e não ausência dela.
    """
    dentro = indice.loc[crise.inicio:crise.fim]
    if dentro.empty:
        raise ValueError(f"janela {crise.nome} fora da série")
    # Nível de véspera: a queda do primeiro mês da crise é parte da crise.
    pos = indice.index.get_loc(dentro.index[0])
    entrada = float(indice.iloc[pos - 1] if pos > 0 else dentro.iloc[0])
    retorno = float(dentro.iloc[-1]) / entrada - 1.0
    # Queda a partir do nível de entrada, não a partir de topo anterior à janela.
    # Limitada a zero: uma estratégia que nunca ficou abaixo do nível de entrada
    # não teve queda, e o CDI reportaria "+0,1% de queda" sem esse limite.
    queda = min(0.0, float(dentro.min()) / entrada - 1.0)

    depois = indice.loc[crise.fim:]
    recuperados = depois[depois >= entrada]
    recuperacao = None
    if retorno < 0 and not recuperados.empty:
        fim_pos = indice.index.get_loc(dentro.index[-1])
        recuperacao = int(indice.index.get_loc(recuperados.index[0]) - fim_pos)
    elif retorno >= 0:
        recuperacao = 0
    return {"retorno": retorno, "queda_max": queda, "recuperacao_meses": recuperacao}


def tabela(results: Path, curated: Path, strategies: tuple[str, ...]) -> pd.DataFrame:
    """Uma linha por crise e estratégia."""
    indices = {s: _indice(results, curated, s) for s in strategies}
    linhas = []
    for crise in CRISES:
        for s in strategies:
            linhas.append({"crise": crise.nome, "estrategia": s, **janela(indices[s], crise)})
    return pd.DataFrame(linhas)


#: Pares comparáveis, na mesma ordem do módulo de decomposição.
PARES: tuple[tuple[str, str, str], ...] = (
    ("Brasil", "br_allocators", "br_etf"),
    ("EUA", "us_allocators", "us_etf"),
    ("Europa", "eu_allocators", "eu_etf"),
    ("Japão", "jp_allocators", "jp_etf"),
    ("Global", "capital_allocators", "passive_etfs"),
)


def confronto(results: Path, curated: Path) -> pd.DataFrame:
    """Allocator contra o ETF da mesma região, crise a crise.

    A pergunta que o placar de vinte anos não responde: a gestão ativa protegeu na
    queda, ou só acumulou vantagem na alta? São coisas diferentes, e um investidor
    que abandona a estratégia no fundo do poço só vive a primeira.
    """
    linhas = []
    for crise in CRISES:
        for regiao, a, b in PARES:
            ja = janela(_indice(results, curated, a), crise)
            jb = janela(_indice(results, curated, b), crise)
            linhas.append({
                "crise": crise.nome,
                "regiao": regiao,
                "alloc": ja["retorno"],
                "etf": jb["retorno"],
                "diferenca_pp": (ja["retorno"] - jb["retorno"]) * 100,
                "protegeu": ja["retorno"] > jb["retorno"],
            })
    return pd.DataFrame(linhas)


def placar_de_protecao(results: Path, curated: Path) -> pd.DataFrame:
    """Em quantas crises o allocator caiu menos que o ETF, por região."""
    c = confronto(results, curated)
    return (c.groupby("regiao", sort=False)
             .agg(crises=("protegeu", "size"), venceu=("protegeu", "sum"),
                  media_pp=("diferenca_pp", "mean"))
             .reset_index())


def validate(results: Path, curated: Path, strategies: Path) -> list[str]:
    problemas = list(regras_congeladas(strategies))
    idx = _indice(results, curated, "capital_allocators")
    for crise in CRISES:
        if idx.loc[crise.inicio:crise.fim].empty:
            problemas.append(f"{crise.nome}: janela fora da série do estudo")
    return problemas
