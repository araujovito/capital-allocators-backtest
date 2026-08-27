# Capital Allocators vs Passive Investing

Sistema de backtesting que compara, sob a ótica de um **investidor brasileiro** com
aportes mensais entre **jan/2006 e dez/2025** (240 meses), três caminhos:

| Papel | Estratégia |
|---|---|
| Gestão ativa | **Capital Allocators** — 8 empresas, 2 por região |
| Gestão passiva | **ETFs** amplos dos mesmos 4 mercados |
| Custo de oportunidade | **CDI** |
| Régua de poder de compra | **IPCA** (não é investimento) |

> Entre 2006 e 2025, qual foi a recompensa obtida por um investidor brasileiro ao
> escolher grandes alocadores de capital, investir passivamente através de ETFs
> ou permanecer em renda fixa?

O sistema executa uma metodologia **definida previamente** e apresenta os resultados,
inclusive se contradisserem a hipótese inicial.

## Universo

### Capital Allocators

| Região | Ativo 1 | Ativo 2 |
|---|---|---|
| 🇧🇷 Brasil | Itaúsa (ITSA4) | Bradespar (BRAP4) |
| 🇺🇸 EUA | Berkshire Hathaway (BRK.B) | Markel (MKL) |
| 🇪🇺 Europa | Investor AB (INVE-B, SEK) | GBL (GBLB, EUR) |
| 🇯🇵 Japão | Mitsubishi Corp (8058, JPY) | Mitsui & Co (8031, JPY) |

### ETFs — Historical Reality

| Região | ETF | Índice | Início |
|---|---|---|---|
| 🇧🇷 Brasil | PIBB11 | IBrX-50 | jul/2004 |
| 🇺🇸 EUA | IVV | S&P 500 | mai/2000 |
| 🇪🇺 Europa | IEV | S&P Europe 350 | jul/2000 |
| 🇯🇵 Japão | EWJ | MSCI Japan | mar/1996 |

**Regra anti-cherry-picking:** todo ativo precisa ser justificável com informação
que já existia aproximadamente em 31/12/2005. Depois de fechado o universo,
resultado ruim **não** é motivo para remover um ativo.

## Arquitetura

```
FONTES → PYTHON (coleta, ETL, validação) → PARQUET
                                              ↓
                                    RUST (backtest engine)
                                              ↓
                              PYTHON (estatística, gráficos)
```

O motor Rust é **genérico**: nenhum ticker, índice ou país é hard-coded. As
estratégias são declaradas em TOML (ver `strategies/`). O experimento financeiro
é uma *aplicação* do motor, não o motor.

## Layout

```
python/capallo/     pipeline de dados e análise
  ingest/           coletores por fonte
  transform/        normalização, FX, total return
  analysis/         métricas, rolling windows, relatórios
engine/             backtest engine em Rust
strategies/         definições .toml das estratégias
data/               raw → interim → curated (fora do git)
docs/               metodologia e decisões
tests/              testes do pipeline
```

## Estado

**Pré-desenvolvimento.** Spike de dados concluído — ver `docs/spike-dados.md`.

| Camada | Estado | Fonte |
|---|---|---|
| CDI, IPCA, câmbio | ✅ resolvida e validada | Banco Central (SGS + Olinda/PTAX) |
| BRK-B, MKL, IVV, IEV, EWJ | ✅ total return, 240/240 meses | Twelve Data (plano gratuito) |
| ITSA4, BRAP4, PIBB11 (preço) | ✅ 4.953 pregões cada, 2006-2025 | B3, arquivo `COTAHIST` |
| Proventos Brasil (dinheiro) | ✅ 644 registros, dividendo × JCP separados | B3, proxy oficial |
| Eventos em ações Brasil | ✅ ITSA4 completa; 2 desdobramentos de BRAP4 recuperados | B3 + detecção por salto |
| **Total return Brasil** | ✅ **fechado e validado** | COTAHIST + eventos + proventos |
| 8058, 8031 (preço) | ✅ 240/240 meses | Kabutan 株探 (japonês) |
| **INVE-B (total return)** | ✅ 240/240 meses — série já ajustada | Avanza (sueco) |
| **Proventos JP** | ✅ 20/20 exercícios, 8058 e 8031 | relatórios anuais das companhias (PDF) |
| Proventos SE | ✅ desnecessários — já no preço | — |
| GBLB (preço) | ✅ 240/240 meses, Bruxelas em EUR | onvista (alemão) |
| **Proventos BE** | ✅ 20/20 exercícios | relatórios anuais do GBL (PDF) |
| **Total return EU e JP** | ✅ **fechado e validado** | preço + provento, convenção de data-ex declarada |

**Os 12 ativos estão no painel do motor**, com total return em moeda local
convertido a real pela PTAX de venda. Não há mais buraco de dado nem
transformação pendente: o estudo passou de coleta para análise.

Barra a ser batida, já quantificada: o **CDI rendeu 4,46% a.a. reais** entre 2006
e 2025 (IPCA acumulado 192,0%; CDI nominal 10,20% a.a.). É o número que Allocators
e ETFs precisam superar para o risco ter compensado.

Os dados internacionais são **essenciais** — sem eles não existem a comparação
regional, o Allocator Premium nem a pergunta central. Três rodadas de busca estão
documentadas em `docs/spike-dados.md`: agregadores, fontes primárias e automação
de navegador. Conclusão: o histórico global exige fonte paga ou coleta via
relatórios de RI.

## Resultados — universo completo

Motor Rust rodando sobre dado real, **os doze ativos**. Aportes mensais de
R$1.000 corrigidos pelo IPCA, jan/2006 a dez/2025, ótica do investidor
brasileiro, dividendos reinvestidos líquidos de retenção na fonte.

| Estratégia | R$ por R$1 aportado | Retorno real a.a. | Vol. | Máx. drawdown | Sharpe |
|---|---|---|---|---|---|
| JP Allocators (8058 + 8031) | **4,90** | 8,79% | 21,97% | −33,8% | 0,29 |
| US ETF (IVV) | 4,88 | 9,54% | 22,13% | −32,0% | 0,32 |
| US Allocators (BRK-B + MKL) | 4,06 | 9,42% | 22,14% | −23,6% | 0,32 |
| EU Allocators (INVE-B + GBLB) | 3,19 | 6,63% | 17,86% | −40,5% | 0,20 |
| EU ETF (IEV) | 2,27 | 4,11% | 24,14% | −32,4% | 0,10 |
| JP ETF (EWJ) | 2,12 | 2,34% | 22,02% | −31,6% | 0,01 |
| BR Allocators (ITSA4 + BRAP4) | 2,05 | 5,03% | 27,93% | −41,7% | 0,16 |
| CDI | 1,52 | 4,43% | 0,94% | 0,0% | 0,00 |
| BR ETF (PIBB11) | 1,45 | 2,77% | 21,31% | −40,5% | 0,03 |

Vitórias dos allocators sobre o ETF da mesma região, em janelas móveis:

| Região | 1 ano | 3 anos | 5 anos | 10 anos |
|---|---|---|---|---|
| Brasil | 49% | 57% | 62% | 62% |
| EUA | 50% | 49% | 41% | **24%** |
| Europa | 59% | 75% | 89% | **100%** |
| Japão | 61% | 70% | 69% | 64% |

O resultado **não é uniforme entre regiões**, e é essa a descoberta: nos EUA o
índice venceu os allocators em janelas longas; na Europa e no Japão, o contrário.
Um estudo que olhasse só o mercado americano teria concluído o oposto de um que
olhasse só o japonês.

⚠️ Duas omissões conhecidas, ambas na borda da janela e ambas contra os
allocators: falta o dividendo do GBL pago em maio de 2006 (exercício de 2005, sem
relatório publicado) e a parcela interina japonesa de setembro de 2025 (exercício
que fecha em março de 2026). Ver `build_intl.py`.

### De onde veio o retorno

`retorno real em BRL = retorno local do ativo × efeito da moeda ÷ inflação`. Os
três fatores se multiplicam, e separá-los muda a leitura: o câmbio contribuiu com
3% a 4,7% ao ano para todo ativo estrangeiro, e sozinho responde por metade do
resultado de EWJ e IEV.

| Ativo | Moeda | Ativo a.a. | Câmbio a.a. | Real em BRL a.a. |
|---|---|---|---|---|
| INVE-B | SEK | 12,23% | 3,69% | **10,33%** |
| BRK-B | USD | 10,88% | 4,65% | 10,02% |
| 8031 | JPY | 12,08% | 3,14% | 9,60% |
| IVV | USD | 10,36% | 4,65% | 9,50% |
| MKL | USD | 9,30% | 4,65% | 8,45% |
| 8058 | JPY | 10,07% | 3,14% | 7,64% |
| BRAP4 | BRL | 12,07% | — | 6,25% |
| IEV | EUR* | 5,06% | 4,50% | 4,09% |
| PIBB11 | BRL | 8,38% | — | 2,76% |
| EWJ | JPY* | 4,64% | 3,14% | 2,33% |
| ITSA4 | BRL | 6,73% | — | 1,19% |
| GBLB | EUR | 1,53% | 4,50% | **0,59%** |

\* IEV e EWJ liquidam em dólar, mas o câmbio é atribuído à moeda do mercado
subjacente — sem isso a perna passiva apareceria como aposta em dólar contra uma
perna ativa em euro e iene, carregando as duas a mesma economia.

### Allocator Premium, sempre ao lado do risco

| Região | Allocators | ETF | Prêmio | Vol. extra | Δ Sharpe | Veredito |
|---|---|---|---|---|---|---|
| Brasil | 5,03% | 2,77% | +2,26 p.p. | +6,62 p.p. | +0,12 | prêmio com risco extra |
| EUA | 9,42% | 9,54% | −0,13 p.p. | +0,00 p.p. | −0,00 | mesmo risco, sem prêmio |
| Europa | 6,63% | 4,11% | +2,52 p.p. | −6,29 p.p. | +0,10 | **dominância** |
| Japão | 8,79% | 2,34% | +6,46 p.p. | −0,05 p.p. | +0,28 | mesmo risco, com prêmio |
| **Global** | **8,47%** | **5,76%** | **+2,72 p.p.** | −6,33 p.p. | +0,19 | **dominância** |

A carteira ativa entregou 3,58x o poder de compra aportado contra 2,66x da
passiva, com **menos** volatilidade (13,3% contra 19,7%) — oito empresas em quatro
regiões diversificam mais que quatro índices regionais.

E o resultado **não depende de uma empresa excepcional**: o maior peso final é
19,0% (Mitsui), o HHI da carteira é 0,144 contra 0,125 do equilíbrio perfeito, e
o pior ativo do universo — GBL, com 0,59% real ao ano — permaneceu na carteira,
como a regra anti-cherry-picking exige.

⚠️ Nos EUA o índice empatou com os allocators, e em janelas de 10 anos venceu em
76% delas. Quem olhasse só o mercado americano concluiria o oposto de quem
olhasse só o japonês. **É essa a descoberta, não o placar global.**

### Como cada estratégia atravessou as crises

Janelas datadas por **terceiros** — NBER, CEPR, CODACE/FGV —, nunca pelo estudo.
Retorno real, aporte expurgado, nível de entrada tomado no mês de véspera. As
regras não mudam durante a crise, e `regras_congeladas()` confere que os onze
arquivos de estratégia compartilham janela, aporte e regra de dividendo.

| Crise | Allocators | ETFs | CDI | Recuperação |
|---|---|---|---|---|
| Crise financeira global (2007-12 → 2009-06) | −39,4% | −32,9% | +9,1% | 68 meses |
| Crise da dívida do euro (2011-08 → 2013-02) | +13,0% | +17,5% | +4,4% | — |
| Recessão brasileira (2014-04 → 2016-12) | +31,2% | +25,6% | +14,0% | — |
| COVID-19 (2020-02 → 2020-04) | +1,9% | +5,4% | +0,9% | — |
| Aperto monetário (2022) | −5,7% | −24,0% | +6,2% | 11 vs 19 meses |

**A gestão ativa não protegeu de forma consistente.** Venceu o índice da mesma
região em apenas 2 das 5 crises no agregado global, e caiu **mais** que o passivo
em 2008 — a crise mais profunda da janela. Protegeu bem em 2022 (−5,7% contra
−24,0%, recuperando em 11 meses contra 19) e na Europa (4 de 5 crises), e mal no
Japão (1 de 5).

É um contrapeso ao placar de vinte anos: o prêmio global de +2,72 p.p. ao ano veio
mais de acumular vantagem na alta do que de perder menos na queda — e um investidor
que abandona a estratégia no fundo do poço só vive a segunda metade.

**Próximo passo:** os experimentos de sensibilidade da metodologia (PTAX compra vs
venda, retenção na fonte, data do aporte).

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e "./python[dev]"

cp .env.example .env  # preencha TWELVEDATA_API_KEY (chave gratuita)

capallo fetch-macro     # CDI, IPCA e PTAX do Banco Central
capallo fetch-equities  # total return dos ativos listados nos EUA
capallo fetch-b3        # precos da B3 (baixa ~550MB de COTAHIST)
capallo fetch-b3-events # proventos e eventos societarios, com reconciliacao
capallo build-br        # monta e valida o total return brasileiro
capallo fetch-intl      # precos de Japao (Kabutan) e Suecia (Avanza)
capallo fetch-jp-dividends  # proventos de 8058 e 8031, dos relatorios anuais
capallo build-intl      # monta e valida o total return de Europa e Japao
capallo export-dataset  # painel mensal em BRL para o motor Rust
pytest tests/

# Motor
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
cd engine && cargo build --release
for s in br_allocators br_etf us_allocators us_etf eu_allocators eu_etf \
         jp_allocators jp_etf capital_allocators passive_etfs cdi; do
  ./target/release/backtest run ../strategies/$s.toml \
    --out ../data/results/$s.csv --positions ../data/results/${s}_positions.csv
done

# Analise
capallo scoreboard      # placar multi-metrica das nove estrategias
capallo decompose       # retorno entre ativo, cambio e inflacao
capallo premium         # Allocator Premium por regiao, ao lado do risco
```
