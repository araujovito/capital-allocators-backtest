"""O teste de sobrevivência: o que dá para medir, e o que não fecha.

O README declarou este como o ataque que sobra ao estudo. Os oito allocators
foram escolhidos com informação de 2005 — mas **por alguém que já sabia quais
holdings de 2005 ainda existiriam em 2025**. Separar o prêmio da gestão do prêmio
de ter sobrevivido exigiria refazer a seleção por critério mecânico sobre todas as
empresas listadas em 2005, mortas inclusive.

Este módulo tentou fazer isso pelo Brasil, que é a única das quatro regiões em que
a fonte existe de graça: o COTAHIST publica todo papel negociado, sobrevivente ou
não. **A tentativa não fecha**, e o motivo é específico o bastante para valer mais
que a tentativa.

## O que ficou medido, e é sólido

Das **96 empresas** com pelo menos R$ 1 milhão de volume mensal em jan/2006 —
universo completo, sem viés por construção —, apenas **40 ainda negociam sob o
mesmo nome** em dez/2025, e **32 sob o mesmo ticker**. É a dimensão do problema: a
lista de onde um analista de 2026 escolhe "duas holdings brasileiras justificáveis
em 2005" é uma lista que já perdeu a maioria dos nomes.

## Por que o número de sobrevivência não é o que parece

Contar "morreu" por desaparecimento de ticker **superestima grosseiramente** a
mortalidade, e dá para provar com nomes:

| aparece como morta | o que de fato aconteceu |
|---|---|
| AMBEV | virou AMBEV S/A (ABEV3) |
| VALE R DOCE | virou VALE |
| DURATEX | virou Dexco |
| LOJAS AMERIC | virou Americanas |
| ITAUBANCO + UNIBANCO | fundiram-se no Itaú Unibanco |
| SADIA + PERDIGÃO | fundiram-se na BRF |
| TELEMAR | virou Oi |

Nenhum desses é morte, e a identidade também não se reconstrói por nome: só 40 dos
96 batem string a string. Reconstruir a cadeia exige **mapa de entidades** — o
equivalente do `PERMNO` do CRSP —, que é exatamente o produto que as bases pagas
vendem, e que a B3 não publica.

Pior: mesmo com o mapa, "sobreviveu" fica ambíguo por definição. Sadia e Perdigão
desapareceram como tickers e continuaram como negócio dentro da BRF. Contá-las
como mortas exagera o viés; como vivas, o subestima. **A pergunta não tem resposta
única**, e é por isso que a literatura de viés de sobrevivência usa bases com
ligação de entidade curada à mão.

## E por que o retorno também não fecha

Ainda que a identidade fosse resolvida, o COTAHIST é preço **bruto**: sem ajuste
por desdobramento, o relativo de vinte anos de cada papel é lixo. O estudo corrigiu
isso para três tickers com eventos da B3 mais detecção por salto, e a API de
eventos **cobre parte** das empresas mortas — ACESITA, encerrada em 2009, devolve
quatro eventos. Não é bloqueio absoluto; é trabalho de curadoria ativo a ativo, com
julgamento em cada um, sobre 96 empresas.

## O que fica registrado

A limitação **permanece de pé e passa a ser específica**: não é "faltou tempo", é
"falta ligação de entidade, e a pergunta é ambígua mesmo com ela". O painel do
universo fica versionado em `b3_universo.parquet` para que uma tentativa futura
comece daqui, e não do zero.

⚠️ Estados Unidos, Europa e Japão não têm nem essa fonte: não há histórico
gratuito com empresas deslistadas em nenhuma das três praças. Mesmo resolvido o
Brasil, o teste cobriria uma das quatro regiões.
"""

from __future__ import annotations

import pandas as pd

from capallo.ingest.b3_universo import MES_BASE, MES_FIM, universo_investavel

#: Empresas que somem por ticker ou por nome e **não** morreram. Transcritas à
#: mão do próprio painel, e são a evidência de que a contagem automática mente.
#: Não é lista exaustiva — é contraexemplo, e um contraexemplo basta.
RENOMEADAS_OU_FUNDIDAS = {
    "AMBEV": "AMBEV S/A (ABEV3)",
    "VALE R DOCE": "VALE",
    "DURATEX": "Dexco",
    "LOJAS AMERIC": "Americanas",
    "ITAUBANCO": "fundiu-se com UNIBANCO no Itaú Unibanco",
    "UNIBANCO": "fundiu-se com ITAUBANCO no Itaú Unibanco",
    "SADIA S/A": "fundiu-se com PERDIGAO na BRF",
    "PERDIGAO S/A": "fundiu-se com SADIA na BRF",
    "TELEMAR": "virou Oi",
    "SUZANO PAPEL": "virou Suzano",
    "TIM PART S/A": "virou TIM",
}


def permanencia(painel: pd.DataFrame, mes_base: str = MES_BASE,
                mes_fim: str = MES_FIM) -> dict:
    """Quantas empresas do universo inicial ainda aparecem no fim da janela.

    Devolve **permanência**, não sobrevivência: mede se o mesmo identificador
    continua no arquivo, que é coisa diferente de a empresa existir.
    """
    inicio = universo_investavel(painel, mes_base)
    fim = painel[painel.mes == mes_fim]
    tickers_fim, nomes_fim = set(fim.ticker), set(fim.nome)
    return {
        "empresas_no_inicio": len(inicio),
        "mesmo_ticker": int(inicio.ticker.isin(tickers_fim).sum()),
        "mesmo_nome": int(inicio.nome.isin(nomes_fim).sum()),
        "sumiram_por_nome": int((~inicio.nome.isin(nomes_fim)).sum()),
    }


def sumiram(painel: pd.DataFrame, mes_base: str = MES_BASE,
            mes_fim: str = MES_FIM) -> pd.DataFrame:
    """Quem sumiu do arquivo, com o contraexemplo ao lado quando existe."""
    inicio = universo_investavel(painel, mes_base)
    nomes_fim = set(painel[painel.mes == mes_fim].nome)
    fora = inicio[~inicio.nome.isin(nomes_fim)].copy()
    fora["nao_morreu"] = fora.nome.map(RENOMEADAS_OU_FUNDIDAS)
    return fora[["nome", "ticker", "nao_morreu"]].sort_values("nome").reset_index(drop=True)


def por_que_nao_fecha(painel: pd.DataFrame) -> list[str]:
    """As razões, com o número que sustenta cada uma."""
    p = permanencia(painel)
    fora = sumiram(painel)
    identificadas = int(fora.nao_morreu.notna().sum())
    razoes = [
        (f"das {p['empresas_no_inicio']} empresas investáveis de jan/2006, "
         f"{p['mesmo_nome']} aparecem com o mesmo nome em dez/2025 e "
         f"{p['mesmo_ticker']} com o mesmo ticker"),
        (f"entre as {p['sumiram_por_nome']} que somem, ao menos {identificadas} "
         f"não morreram — foram renomeadas ou fundidas, e estão nomeadas em "
         f"RENOMEADAS_OU_FUNDIDAS"),
        ("contar desaparecimento de ticker como morte superestima a mortalidade; "
         "reconstruir a cadeia exige mapa de entidades, que a B3 não publica"),
        ("mesmo com o mapa, 'sobreviveu' é ambíguo: Sadia e Perdigão sumiram como "
         "ticker e continuaram como negócio dentro da BRF"),
        ("e o COTAHIST é preço bruto: sem ajuste por desdobramento, o relativo de "
         "vinte anos de cada papel não se sustenta"),
    ]
    return razoes
