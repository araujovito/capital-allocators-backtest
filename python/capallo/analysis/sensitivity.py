"""Experimentos de sensibilidade: quanto as escolhas de método decidem o resultado.

Toda metodologia congela decisões que poderiam ter sido outras. Declará-las é o
mínimo; medi-las é o que separa "a escolha foi razoável" de "a escolha não decide
o resultado". Este módulo mede duas, e registra por que uma terceira não roda.

## 1. Ponta da PTAX — compra, venda ou média

A seção 5 da metodologia converte tudo pela PTAX de **venda**, que é a ponta que o
investidor brasileiro paga ao comprar moeda. A escolha parece inócua: converter
todos os níveis pela mesma ponta faz o spread cancelar no retorno.

Ele cancelaria se fosse constante — e não é. O spread médio do dólar era **0,46%
em 2006** e é **0,011% desde 2020**: a B3 e o mercado de câmbio apertaram a ponta
ao longo da janela. Um spread que encolhe não cancela; deixa resíduo, e o resíduo
tem sinal conhecido — converter pela venda infla o nível inicial mais que o final,
o que **subestima** o retorno de todo ativo estrangeiro.

O experimento refaz o painel com `bid` e com a média e roda o motor de novo. O que
interessa não é qual ponta é "certa" — a metodologia já decidiu isso, e antes de
ver resultado —, mas se a decisão move o veredito.

## 2. Janelas de início móvel

A §9 da metodologia prevê "múltiplas datas de início — 2006→2025, 2007→2025, …
2015→2025". É o teste anti-cherry-picking mais direto que resta: a conclusão do
estudo depende de ter começado em 2006?

O aporte é reajustado pelo IPCA a partir do início de cada janela, então R$1.000
de 2010 não é R$1.000 de 2006. A métrica-síntese do estudo — reais de poder de
compra por real aportado — é imune a isso, porque normaliza pelo próprio aportado.

## 3. O que não roda: a data do aporte dentro do mês

A §2 congela o aporte no **1º dia útil do mês, no fechamento**, e a pergunta
natural é quanto muda se cair no meio ou no fim. **Este experimento não pode ser
executado com o dado que existe**, e a razão é o Japão: a série do Kabutan é
mensal, não diária — o site publica ~14 meses de pregão a pregão e nada além
disso. Sem preço diário de 8058 e 8031 não há como mover o aporte dentro do mês
para dois dos doze ativos, e movê-lo só para os outros dez compararia estratégias
com regras diferentes, que é exatamente o que `regras_congeladas()` existe para
impedir.

Fica declarado como limitação de dado, não como experimento omitido. Executá-lo
exigiria uma fonte diária japonesa com vinte anos de histórico, que as três
rodadas de busca em `docs/spike-dados.md` não encontraram de graça.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pandas as pd

from capallo.analysis.scoreboard import evaluate
from capallo.transform.dataset import export

#: Estratégias necessárias para o prêmio global e as regionais.
PARES = (
    ("Global", "capital_allocators", "passive_etfs"),
    ("Brasil", "br_allocators", "br_etf"),
    ("EUA", "us_allocators", "us_etf"),
    ("Europa", "eu_allocators", "eu_etf"),
    ("Japão", "jp_allocators", "jp_etf"),
)


def _binario(engine_dir: Path) -> Path:
    exe = engine_dir / "target" / "release" / "backtest"
    if not exe.exists():
        raise FileNotFoundError(
            f"motor não compilado em {exe} — rode `cargo build --release` em {engine_dir}"
        )
    return exe


def _rodar(exe: Path, toml: Path, data_dir: Path, out: Path) -> None:
    subprocess.run(
        [str(exe), "run", str(toml), "--data", str(data_dir), "--out", str(out)],
        check=True, capture_output=True,
    )


def _premios(resultados: dict[str, Path], curated: Path) -> pd.DataFrame:
    """Retorno real anualizado por estratégia e prêmio por região."""
    metricas = {nome: evaluate(p, curated) for nome, p in resultados.items()}
    linhas = []
    for regiao, alloc, etf in PARES:
        if alloc not in metricas or etf not in metricas:
            continue
        a, e = metricas[alloc], metricas[etf]
        linhas.append({
            "regiao": regiao,
            "alloc_aa": a["retorno_real_aa"],
            "etf_aa": e["retorno_real_aa"],
            "premio_pp": (a["retorno_real_aa"] - e["retorno_real_aa"]) * 100,
            "alloc_reais_por_real": a["reais_por_real"],
            "etf_reais_por_real": e["reais_por_real"],
        })
    return pd.DataFrame(linhas)


def ponta_da_ptax(
    curated: Path, engine_dir: Path, strategies: Path, sides: tuple[str, ...] = ("ask", "bid", "mid")
) -> pd.DataFrame:
    """Refaz o estudo inteiro com cada ponta da PTAX e compara os prêmios."""
    exe = _binario(engine_dir)
    nomes = sorted({s for _, a, e in PARES for s in (a, e)})

    quadros = []
    for side in sides:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            dados, saidas = tmp / "engine", tmp / "results"
            saidas.mkdir(parents=True)
            export(curated, dados, fx_side=side)

            resultados = {}
            for nome in nomes:
                out = saidas / f"{nome}.csv"
                _rodar(exe, strategies / f"{nome}.toml", dados, out)
                resultados[nome] = out
            q = _premios(resultados, curated)
        quadros.append(q.assign(ponta=side))

    return pd.concat(quadros, ignore_index=True)


def _toml_com_inicio(origem: Path, inicio: str, destino: Path) -> Path:
    """Copia a estratégia trocando só a data de início.

    Trocar por substituição de linha, e não regravando o TOML, é deliberado: o
    arquivo continua sendo o mesmo que roda no estudo, com uma única diferença
    visível — se outra regra mudasse junto, a comparação não seria da janela.
    """
    linhas = origem.read_text().splitlines()
    trocadas, achou = [], False
    for ln in linhas:
        if ln.strip().startswith("start =") and not achou:
            trocadas.append(f'start = "{inicio}"')
            achou = True
        else:
            trocadas.append(ln)
    if not achou:
        raise ValueError(f"{origem} não declara `start`")
    destino.write_text("\n".join(trocadas) + "\n")
    return destino


def janelas_de_inicio(
    curated: Path, engine_dir: Path, strategies: Path, engine_data: Path,
    primeiro: int = 2006, ultimo: int = 2015,
) -> pd.DataFrame:
    """Roda o estudo começando em cada janeiro de `primeiro` a `ultimo`.

    O fim é sempre dez/2025: o que varia é o quanto de história entra, não o
    quanto sai. Uma conclusão que só existe começando em 2006 é uma conclusão
    sobre 2006.
    """
    exe = _binario(engine_dir)
    nomes = sorted({s for _, a, e in PARES for s in (a, e)})

    quadros = []
    for ano in range(primeiro, ultimo + 1):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            saidas = tmp / "results"
            saidas.mkdir(parents=True)
            resultados = {}
            for nome in nomes:
                toml = _toml_com_inicio(
                    strategies / f"{nome}.toml", f"{ano}-01-01", tmp / f"{nome}.toml"
                )
                out = saidas / f"{nome}.csv"
                _rodar(exe, toml, engine_data, out)
                resultados[nome] = out
            q = _premios(resultados, curated)
        quadros.append(q.assign(inicio=ano, anos=2026 - ano))

    return pd.concat(quadros, ignore_index=True)
