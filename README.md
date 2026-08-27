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

**Próximo passo:** decomposição do retorno entre ativo e câmbio, e o Allocator
Premium por região.

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
capallo probe           # viabilidade das series ainda bloqueadas
pytest tests/

# Rust (ainda não instalado nesta máquina)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
cd engine && cargo build --release
```
