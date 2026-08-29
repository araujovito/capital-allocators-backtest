"""Camada de gráficos: as quatro figuras que o estudo precisa mostrar.

A arquitetura no README sempre prometeu "Python (estatística, gráficos)" e a
segunda metade não existia. Este módulo fecha isso — e as regras que ele segue
estão aqui em cima porque um gráfico é lido por gente, não executado por máquina:
o que decide se ele funciona não aparece em teste nenhum.

## O que cada figura tem de fazer

Cada uma existe por uma **pergunta**, não por um dado disponível:

1. `crescimento` — *a gestão ativa venceu?* Quatro painéis, um por região, porque
   a resposta muda de região para região e essa é a descoberta do estudo. Um único
   painel com nove linhas esconderia exatamente o que há para ver.
2. `janelas_de_inicio` — *o resultado depende de ter começado em 2006?* Prêmio por
   ano de entrada, com a linha do zero como referência.
3. `decomposicao` — *de onde veio o retorno?* Halteres do retorno em moeda local
   até o retorno real em real: a distância é o que câmbio e inflação fizeram.
4. `janelas_moveis` — *com que frequência a gestão ativa venceu?* Mapa divergente
   em torno de 50%, que é o ponto em que "venceu" e "perdeu" se equilibram.

## Regras seguidas, e por quê

- **Paleta validada, não escolhida a olho.** As cores vêm da paleta de referência
  e foram passadas pelo validador de daltonismo nos dois modos, com todos os pares
  em jogo onde o gráfico exige (ΔE CVD 9,2 claro / 9,4 escuro, contra piso 8).
- **Nunca dois eixos y.** Onde há duas grandezas, há dois painéis.
- **Cor segue a entidade.** Allocators são sempre o slot 1, ETFs sempre o slot 2,
  CDI sempre o slot 3 — em toda figura, em todo painel.
- **Divergente só onde há polaridade real** (acima/abaixo de 50%, acima/abaixo de
  zero), com cinza no meio. Magnitude sem polaridade não ganha duas cores.
- **Rótulo direto é seletivo.** Ponta da linha e extremos; o resto fica no eixo e
  nas tabelas do README, que continuam sendo a leitura acessível dos mesmos números.
- **Texto nunca veste a cor da série.** Três cores da paleta clara ficam abaixo de
  3:1 contra o fundo — legíveis como marca, ilegíveis como texto. A identidade vem
  do traço colorido ao lado do rótulo.
- **Dois temas, escolhidos, não invertidos.** O tema escuro usa os passos próprios
  da paleta para fundo escuro. O README embute os dois com `<picture>`, então a
  figura acompanha o tema do GitHub de quem está lendo.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from capallo.analysis.scoreboard import _deflator, _load_result


@dataclass(frozen=True)
class Tema:
    """Tokens de um modo. Os dois modos são escolhidos, não um a inversão do outro."""

    nome: str
    surface: str
    ink: str
    ink2: str
    muted: str
    grid: str
    axis: str
    series: tuple[str, ...]
    div_pos: str
    div_neg: str
    div_mid: str


CLARO = Tema(
    nome="light", surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781",
    grid="#e1e0d9", axis="#c3c2b7",
    series=("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"),
    div_pos="#2a78d6", div_neg="#e34948", div_mid="#f0efec",
)
ESCURO = Tema(
    nome="dark", surface="#1a1a19", ink="#ffffff", ink2="#c3c2b7", muted="#898781",
    grid="#2c2c2a", axis="#383835",
    series=("#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"),
    div_pos="#3987e5", div_neg="#e66767", div_mid="#383835",
)
TEMAS = (CLARO, ESCURO)

#: Papel → slot fixo. Cor segue a entidade, nunca a ordem em que ela apareceu.
ALLOC, ETF, CDI = 0, 1, 2

REGIOES = (
    ("Brasil", "br_allocators", "br_etf"),
    ("Estados Unidos", "us_allocators", "us_etf"),
    ("Europa", "eu_allocators", "eu_etf"),
    ("Japão", "jp_allocators", "jp_etf"),
)

FIGSIZE = (10.0, 6.4)
DPI = 160


def _base(t: Tema, fig, eixos) -> None:
    """Cromo recessivo: grade fina e sólida, sem moldura, texto em token de texto."""
    fig.patch.set_facecolor(t.surface)
    for ax in eixos:
        ax.set_facecolor(t.surface)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
        for lado in ("left", "bottom"):
            ax.spines[lado].set_color(t.axis)
            ax.spines[lado].set_linewidth(1.0)
        ax.tick_params(colors=t.muted, labelsize=9, length=0)
        ax.grid(True, axis="y", color=t.grid, linewidth=1.0, linestyle="-")
        ax.set_axisbelow(True)


def _num(v: float, casas: int = 2, sufixo: str = "") -> str:
    """Número no formato brasileiro: vírgula decimal."""
    return f"{v:,.{casas}f}".replace(",", "\u00a0").replace(".", ",") + sufixo


def _salvar(fig, out_dir: Path, nome: str, t: Tema) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    caminho = out_dir / f"{nome}-{t.nome}.png"
    fig.savefig(caminho, dpi=DPI, facecolor=fig.get_facecolor(), bbox_inches="tight",
                pad_inches=0.3)
    plt.close(fig)
    return caminho


def poder_de_compra(path: Path, curated: Path) -> pd.Series:
    """Reais de poder de compra acumulados por real de poder de compra aportado.

    É a métrica-síntese da §8 da metodologia, mês a mês em vez de só no fim. Tanto
    o patrimônio quanto o aportado são trazidos para o poder de compra do fim da
    série, então a razão não carrega inflação em lado nenhum.
    """
    df = _load_result(path)
    d = _deflator(curated).reindex(df.index)
    return (df.value * d) / (df.contribution * d).cumsum()


def crescimento(resultados: Path, curated: Path, out_dir: Path) -> list[Path]:
    """Quatro painéis: allocators, ETF e CDI de cada região, no mesmo eixo.

    Painéis em vez de um gráfico só porque a descoberta do estudo é justamente que
    a resposta **não é a mesma nas quatro regiões**. Nove linhas num eixo só
    mostrariam um emaranhado com a conclusão média — que é a conclusão errada.

    O eixo é compartilhado entre os painéis de propósito: comparar regiões só
    significa alguma coisa se a escala for a mesma.
    """
    series = {}
    for _, alloc, etf in REGIOES:
        series[alloc] = poder_de_compra(resultados / f"{alloc}.csv", curated)
        series[etf] = poder_de_compra(resultados / f"{etf}.csv", curated)
    series["cdi"] = poder_de_compra(resultados / "cdi.csv", curated)
    topo = max(float(s.max()) for s in series.values())

    saidas = []
    for t in TEMAS:
        fig, axes = plt.subplots(2, 2, figsize=FIGSIZE, sharex=True, sharey=True)
        _base(t, fig, axes.ravel())

        for ax, (regiao, alloc, etf) in zip(axes.ravel(), REGIOES):
            x = series[alloc].index.to_timestamp()
            for chave, slot in ((alloc, ALLOC), (etf, ETF), ("cdi", CDI)):
                ax.plot(x, series[chave].to_numpy(), color=t.series[slot],
                        linewidth=2.0, solid_joinstyle="round", solid_capstyle="round")
            # Linha do 1,0: abaixo dela o investidor perdeu poder de compra.
            ax.axhline(1.0, color=t.axis, linewidth=1.0)
            ax.set_title(regiao, color=t.ink, fontsize=11, loc="left", pad=8)
            ax.set_ylim(0, topo * 1.08)
            # Margem à direita reservada para o rótulo: assim ele fica **fora** da
            # linha em vez de por cima dela.
            ax.set_xlim(x[0], x[-1] + (x[-1] - x[0]) * 0.16)
            # A margem do rótulo não pode virar marca de ano: o eixo pararia em
            # 2028, sugerindo dado que não existe.
            ax.set_xticks([pd.Timestamp(f"{a}-01-01") for a in range(2008, 2025, 4)])

            # Rótulo direto só nas duas pontas que a região compara — o CDI é o
            # mesmo nos quatro painéis e fica para a legenda. Quando as duas pontas
            # chegam juntas, empilhar os rótulos os desgruda das linhas; o
            # deslocamento por ordem de valor mantém cada um do seu lado.
            pontas = sorted(((float(series[c].iloc[-1]), c, s)
                             for c, s in ((alloc, ALLOC), (etf, ETF))), reverse=True)
            for i, (v, _chave, slot) in enumerate(pontas):
                ax.annotate(_num(v, 2, "x"), xy=(x[-1], v), xytext=(9, 4 if i == 0 else -11),
                            textcoords="offset points", ha="left", fontsize=9,
                            color=t.ink2, fontweight="bold")
                ax.plot([x[-1]], [v], marker="o", markersize=5, color=t.series[slot],
                        markeredgecolor=t.surface, markeredgewidth=2.0, zorder=5)

        handles = [
            plt.Line2D([], [], color=t.series[ALLOC], linewidth=2.0),
            plt.Line2D([], [], color=t.series[ETF], linewidth=2.0),
            plt.Line2D([], [], color=t.series[CDI], linewidth=2.0),
        ]
        leg = fig.legend(handles, ["Capital Allocators", "ETF da região", "CDI"],
                         loc="lower center", ncol=3, frameon=False, fontsize=10,
                         bbox_to_anchor=(0.5, -0.04))
        for texto in leg.get_texts():
            texto.set_color(t.ink2)

        fig.suptitle("Reais de poder de compra por real aportado, 2006-2025",
                     color=t.ink, fontsize=13, x=0.02, ha="left", y=1.02)
        fig.text(0.02, 0.975,
                 "aportes mensais corrigidos pelo IPCA · a linha fina marca 1,00x, "
                 "onde o poder de compra apenas se preserva",
                 color=t.muted, fontsize=9.5, ha="left")
        fig.tight_layout()
        saidas.append(_salvar(fig, out_dir, "crescimento", t))
    return saidas


#: Ordem fixa das regiões nas figuras que comparam todas. Cor segue a entidade:
#: uma região mantém o slot dela em qualquer figura.
ORDEM_REGIOES = ("Brasil", "EUA", "Europa", "Japão", "Global")


def janelas_de_inicio(premios: pd.DataFrame, out_dir: Path) -> list[Path]:
    """Prêmio por ano de entrada, com a linha do zero como referência.

    O eixo do zero é o assunto: acima dele a gestão ativa venceu naquela janela,
    abaixo perdeu. É a figura que mostra que o prêmio global sobrevive às dez
    janelas e que o americano só existe numa.
    """
    piv = premios.pivot(index="inicio", columns="regiao", values="premio_pp")[
        list(ORDEM_REGIOES)
    ]
    anos = piv.index.to_numpy()

    saidas = []
    for t in TEMAS:
        fig, ax = plt.subplots(figsize=(10.0, 5.6))
        _base(t, fig, [ax])

        # O zero não é uma gridline: é a fronteira entre venceu e perdeu.
        ax.axhline(0, color=t.ink2, linewidth=1.4, zorder=2)

        for i, regiao in enumerate(ORDEM_REGIOES):
            v = piv[regiao].to_numpy()
            ax.plot(anos, v, color=t.series[i], linewidth=2.0,
                    solid_joinstyle="round", solid_capstyle="round", zorder=3)
            ax.plot([anos[-1]], [v[-1]], marker="o", markersize=5, color=t.series[i],
                    markeredgecolor=t.surface, markeredgewidth=2.0, zorder=5)
            ax.annotate(f"{regiao}  {_num(v[-1], 1)}", xy=(anos[-1], v[-1]),
                        xytext=(10, -4), textcoords="offset points", ha="left",
                        fontsize=9.5, color=t.ink2, fontweight="bold")

        ax.set_xlim(anos[0] - 0.2, anos[-1] + 3.4)
        ax.set_xticks(anos)
        ax.set_ylabel("prêmio, p.p. ao ano", color=t.muted, fontsize=9.5)
        ax.set_xlabel("ano de entrada — o fim é sempre dez/2025",
                      color=t.muted, fontsize=9.5, labelpad=8)
        ax.set_ylim(-3.0, float(piv.to_numpy().max()) * 1.08)
        # A metade negativa ganha uma lavagem recessiva em vez de uma seta com
        # texto: a seta precisaria atravessar quatro séries para alcançar o ponto,
        # e o que ela diria já está no desenho. A lavagem só nomeia o território.
        ax.axhspan(-3.0, 0, color=t.grid, alpha=0.55, zorder=0, linewidth=0)
        ax.text(anos[0] + 0.15, -2.5, "abaixo de zero, o índice da região venceu",
                color=t.muted, fontsize=9, va="center")

        fig.suptitle("O resultado depende de ter começado em 2006?",
                     color=t.ink, fontsize=13, x=0.02, ha="left", y=1.03)
        fig.text(0.02, 0.965,
                 "Allocator Premium por ano de entrada · acima de zero a gestão ativa "
                 "venceu o índice da própria região",
                 color=t.muted, fontsize=9.5, ha="left")
        fig.tight_layout()
        saidas.append(_salvar(fig, out_dir, "janelas-de-inicio", t))
    return saidas


#: Quais tickers são gestão ativa. Usado só para dar identidade ao halter — a
#: figura compara o mesmo ativo consigo mesmo, não um ativo com outro.
ALLOCATORS = frozenset({"ITSA4", "BRAP4", "BRK-B", "MKL", "INVE-B", "GBLB", "8058", "8031"})


def decomposicao(dec: pd.DataFrame, out_dir: Path) -> list[Path]:
    """Halteres: do retorno em moeda local ao retorno real em real.

    A distância entre as duas pontas é o que câmbio e inflação fizeram com o
    resultado do ativo — e ela é grande. É a figura que impede a leitura
    ingênua de que a diferença entre os ativos veio toda da empresa.

    Halter, e não barra empilhada, porque as três parcelas se **multiplicam**
    (`local × câmbio ÷ inflação`); empilhar somaria o que não se soma, com erro
    crescendo justamente nos ativos de maior retorno.
    """
    d = dec.sort_values("real_brl_aa").reset_index(drop=True)
    saidas = []
    for t in TEMAS:
        fig, ax = plt.subplots(figsize=(10.0, 6.2))
        _base(t, fig, [ax])
        ax.grid(False, axis="y")
        ax.grid(True, axis="x", color=t.grid, linewidth=1.0)

        y = range(len(d))
        for i, r in d.iterrows():
            a, b = r.local_aa * 100, r.real_brl_aa * 100
            cor = t.series[ALLOC] if r.ticker in ALLOCATORS else t.series[ETF]
            ax.plot([a, b], [i, i], color=cor, linewidth=2.0, alpha=0.45,
                    solid_capstyle="round", zorder=2)
            # Ponta vazada = moeda local; ponta cheia = o que o brasileiro levou.
            ax.plot([a], [i], marker="o", markersize=7, markerfacecolor=t.surface,
                    markeredgecolor=cor, markeredgewidth=2.0, zorder=3)
            ax.plot([b], [i], marker="o", markersize=8, color=cor,
                    markeredgecolor=t.surface, markeredgewidth=2.0, zorder=4)

        ax.set_yticks(list(y))
        ax.set_yticklabels(
            [f"{r.ticker}  ({r.moeda_exposicao})" for _, r in d.iterrows()],
            fontsize=9.5, color=t.ink2,
        )
        ax.axvline(0, color=t.axis, linewidth=1.0)
        ax.set_xlabel("retorno anualizado, %", color=t.muted, fontsize=9.5, labelpad=8)
        ax.set_ylim(-0.8, len(d) - 0.2)

        # Só os dois extremos ganham valor no desenho: o resto está no eixo. O
        # rótulo vai à **esquerda** da ponta cheia, que é sempre a menor das duas:
        # à direita ele cairia em cima do próprio haltere.
        ax.set_xlim(-1.6, float(d.local_aa.max()) * 100 * 1.06)
        for i in (0, len(d) - 1):
            r = d.iloc[i]
            ax.annotate(_num(r.real_brl_aa * 100, 1, "%"),
                        xy=(r.real_brl_aa * 100, i), xytext=(-11, -3),
                        textcoords="offset points", ha="right", fontsize=9,
                        color=t.ink2, fontweight="bold")

        handles = [
            plt.Line2D([], [], color=t.series[ALLOC], marker="o", linewidth=0,
                       markersize=8, markeredgecolor=t.surface, markeredgewidth=2.0),
            plt.Line2D([], [], color=t.series[ETF], marker="o", linewidth=0,
                       markersize=8, markeredgecolor=t.surface, markeredgewidth=2.0),
            plt.Line2D([], [], color=t.muted, marker="o", linewidth=0, markersize=7,
                       markerfacecolor=t.surface, markeredgecolor=t.muted,
                       markeredgewidth=2.0),
        ]
        leg = fig.legend(handles,
                         ["Capital Allocator (real em BRL)", "ETF (real em BRL)",
                          "ponta vazada: retorno em moeda local"],
                         loc="lower center", ncol=3, frameon=False, fontsize=9.5,
                         bbox_to_anchor=(0.5, -0.06))
        for texto in leg.get_texts():
            texto.set_color(t.ink2)

        fig.suptitle("De onde veio o retorno: da empresa ou da moeda?",
                     color=t.ink, fontsize=13, x=0.02, ha="left", y=1.03)
        fig.text(0.02, 0.965,
                 "retorno em moeda local → retorno real em reais · a distância é o "
                 "efeito do câmbio e da inflação brasileira",
                 color=t.muted, fontsize=9.5, ha="left")
        fig.tight_layout()
        saidas.append(_salvar(fig, out_dir, "decomposicao", t))
    return saidas


HORIZONTES = (1, 3, 5, 10)


def janelas_moveis(resultados: Path, out_dir: Path) -> list[Path]:
    """Com que frequência a gestão ativa venceu, por região e horizonte.

    Divergente, não sequencial, e o motivo é o dado: 50% não é "pouco", é o
    ponto em que vencer e perder se equilibram. Uma escala de uma cor só faria
    49% e 51% parecerem quase o mesmo tom de "baixo", quando são lados opostos
    da única fronteira que existe aqui.

    Os valores são impressos em toda célula — é o caso em que rotular tudo é
    certo, porque a matriz **é** a tabela: são dezesseis números, e a cor está
    ali para ordenar a leitura, não para substituí-los.
    """
    from capallo.analysis.scoreboard import win_rate

    dados = pd.DataFrame(
        [[win_rate(resultados / f"{a}.csv", resultados / f"{e}.csv", h) * 100
          for h in HORIZONTES]
         for _, a, e in REGIOES],
        index=[r for r, _, _ in REGIOES],
        columns=[f"{h} ano" if h == 1 else f"{h} anos" for h in HORIZONTES],
    )

    saidas = []
    for t in TEMAS:
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
            "premio", [t.div_neg, t.div_mid, t.div_pos]
        )
        fig, ax = plt.subplots(figsize=(8.4, 4.4))
        _base(t, fig, [ax])
        ax.grid(False)

        # Escala simétrica em torno de 50: sem isso o meio neutro escorregaria
        # para onde os dados por acaso estão, e a cor deixaria de significar lado.
        alcance = max(abs(dados.to_numpy() - 50).max(), 15)
        ax.imshow(dados.to_numpy(), cmap=cmap, vmin=50 - alcance, vmax=50 + alcance,
                  aspect="auto")

        for i in range(dados.shape[0]):
            for j in range(dados.shape[1]):
                v = float(dados.iat[i, j])
                # Dentro de um preenchimento colorido, o texto escolhe branco ou
                # tinta pela luminância da célula — a única exceção à regra de o
                # texto nunca vestir cor.
                intenso = abs(v - 50) > alcance * 0.55
                ax.text(j, i, _num(v, 0, "%"), ha="center", va="center", fontsize=11,
                        fontweight="bold", color="#ffffff" if intenso else t.ink)

        ax.set_xticks(range(dados.shape[1]), dados.columns, fontsize=10, color=t.ink2)
        ax.set_yticks(range(dados.shape[0]), dados.index, fontsize=10, color=t.ink2)
        ax.tick_params(length=0)
        for lado in ("left", "bottom"):
            ax.spines[lado].set_visible(False)
        # Grade de 2px na cor do fundo: o separador é o vazio, não uma borda.
        ax.set_xticks([x - 0.5 for x in range(1, dados.shape[1])], minor=True)
        ax.set_yticks([y - 0.5 for y in range(1, dados.shape[0])], minor=True)
        ax.grid(which="minor", color=t.surface, linewidth=2.0)
        ax.tick_params(which="minor", length=0)

        fig.suptitle("Com que frequência os allocators venceram o ETF da região",
                     color=t.ink, fontsize=13, x=0.02, ha="left", y=1.06)
        fig.text(0.02, 0.975,
                 "fração das janelas móveis em que a gestão ativa ficou à frente · "
                 "50% é o empate, e é o meio neutro da escala",
                 color=t.muted, fontsize=9.5, ha="left")
        fig.tight_layout()
        saidas.append(_salvar(fig, out_dir, "janelas-moveis", t))
    return saidas


#: Nome do arquivo → o que a figura responde. Serve à CLI e ao README.
FIGURAS = {
    "crescimento": "a gestão ativa venceu, e em que região",
    "janelas-de-inicio": "o resultado depende de ter começado em 2006",
    "decomposicao": "quanto do retorno veio da empresa e quanto da moeda",
    "janelas-moveis": "com que frequência os allocators venceram",
    "index-benchmark": "quanto do prêmio era o mercado e quanto era o produto",
}


def build_all(
    resultados: Path, curated: Path, engine: Path, out_dir: Path,
    premios: pd.DataFrame | None = None,
) -> list[Path]:
    """Gera as quatro figuras nos dois temas.

    `premios` vem de `sensitivity.janelas_de_inicio`, que roda o motor dez vezes.
    Deixá-lo opcional permite regerar as três figuras baratas sem repetir isso.
    """
    from capallo.analysis.decomposition import by_asset

    saidas = list(crescimento(resultados, curated, out_dir))
    saidas += decomposicao(by_asset(curated, engine), out_dir)
    saidas += janelas_moveis(resultados, out_dir)
    # A figura do Index Benchmark só existe se o experimento tiver rodado; quem
    # parou no Historical Reality não tem os CSVs de índice.
    if (resultados / "passive_indices.csv").exists():
        from capallo.analysis.index_benchmark import comparar

        saidas += index_benchmark(comparar(resultados, curated), out_dir)
    if premios is not None:
        saidas += janelas_de_inicio(premios, out_dir)
    return saidas


def index_benchmark(tabela: pd.DataFrame, out_dir: Path) -> list[Path]:
    """Halteres do prêmio contra o ETF até o prêmio contra o índice.

    Forma de "antes → depois por item": cada região tem o mesmo prêmio medido
    contra duas referências, e o que interessa é a **distância** entre elas — o
    quanto do prêmio era custo de produto e não gestão de capital.

    Duas cores, porque aqui há polaridade e não identidade: encolher e crescer
    são coisas opostas, e o Brasil é o único que cresce.
    """
    d = tabela.set_index("regiao").loc[list(ORDEM_REGIOES)].reset_index()
    saidas = []
    for t in TEMAS:
        fig, ax = plt.subplots(figsize=(9.6, 5.0))
        _base(t, fig, [ax])
        ax.grid(False, axis="y")
        ax.grid(True, axis="x", color=t.grid, linewidth=1.0)

        for i, r in d.iterrows():
            a, b = r.premio_vs_etf_pp, r.premio_vs_indice_pp
            cor = t.div_neg if b < a else t.div_pos
            ax.plot([a, b], [i, i], color=cor, linewidth=2.0, alpha=0.45,
                    solid_capstyle="round", zorder=2)
            ax.plot([a], [i], marker="o", markersize=7, markerfacecolor=t.surface,
                    markeredgecolor=t.muted, markeredgewidth=2.0, zorder=3)
            ax.plot([b], [i], marker="o", markersize=8, color=cor,
                    markeredgecolor=t.surface, markeredgewidth=2.0, zorder=4)
            lado, desloc = ("right", -11) if b < a else ("left", 11)
            ax.annotate(_num(b, 2), xy=(b, i), xytext=(desloc, -3),
                        textcoords="offset points", ha=lado, fontsize=9,
                        color=t.ink2, fontweight="bold")

        ax.axvline(0, color=t.ink2, linewidth=1.4, zorder=1)
        ax.set_yticks(range(len(d)), d.regiao, fontsize=10, color=t.ink2)
        ax.invert_yaxis()
        ax.set_xlabel("Allocator Premium, p.p. ao ano", color=t.muted,
                      fontsize=9.5, labelpad=8)
        ax.set_xlim(-1.4, float(d[["premio_vs_etf_pp", "premio_vs_indice_pp"]].to_numpy().max()) + 1.1)

        handles = [
            plt.Line2D([], [], color=t.muted, marker="o", linewidth=0, markersize=7,
                       markerfacecolor=t.surface, markeredgecolor=t.muted,
                       markeredgewidth=2.0),
            plt.Line2D([], [], color=t.div_neg, marker="o", linewidth=0, markersize=8,
                       markeredgecolor=t.surface, markeredgewidth=2.0),
            plt.Line2D([], [], color=t.div_pos, marker="o", linewidth=0, markersize=8,
                       markeredgecolor=t.surface, markeredgewidth=2.0),
        ]
        leg = fig.legend(handles,
                         ["contra o ETF de 2006", "contra o índice: prêmio encolhe",
                          "contra o índice: prêmio cresce"],
                         loc="lower center", ncol=3, frameon=False, fontsize=9.5,
                         bbox_to_anchor=(0.5, -0.07))
        for texto in leg.get_texts():
            texto.set_color(t.ink2)

        fig.suptitle("O allocator venceu o mercado, ou venceu o produto?",
                     color=t.ink, fontsize=13, x=0.02, ha="left", y=1.04)
        fig.text(0.02, 0.955,
                 "a distância é o que a taxa e o tracking error do ETF valiam · "
                 "nos EUA o prêmio inteiro era o produto",
                 color=t.muted, fontsize=9.5, ha="left")
        fig.tight_layout()
        saidas.append(_salvar(fig, out_dir, "index-benchmark", t))
    return saidas
