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
| INVE-B (preço) | ✅ 240/240 meses | Avanza (sueco) |
| Proventos JP | ⬜ parcial: 2010+ | IR Bank (japonês) |
| Proventos SE | ⬜ parcial: 2019+ | Avanza (sueco) |
| GBLB (preço) | ✅ 240/240 meses, Bruxelas em EUR | onvista (alemão) |

**Os 12 ativos têm série de preço.** Brasil e EUA completos, com total return validado.
O bloqueio restante são os quatro allocators de Europa e Japão.

Barra a ser batida, já quantificada: o **CDI rendeu 4,46% a.a. reais** entre 2006
e 2025 (IPCA acumulado 192,0%; CDI nominal 10,20% a.a.). É o número que Allocators
e ETFs precisam superar para o risco ter compensado.

Os dados internacionais são **essenciais** — sem eles não existem a comparação
regional, o Allocator Premium nem a pergunta central. Três rodadas de busca estão
documentadas em `docs/spike-dados.md`: agregadores, fontes primárias e automação
de navegador. Conclusão: o histórico global exige fonte paga ou coleta via
relatórios de RI.

## Primeiros resultados — parciais

Motor Rust rodando sobre dado real. Aportes mensais de R$1.000 corrigidos pelo
IPCA, jan/2006 a dez/2025, ótica do investidor brasileiro.

| Estratégia | R$ por R$1 de poder de compra aportado |
|---|---|
| US ETF (IVV) | **4,88** |
| US Allocators (BRK-B + MKL) | 4,06 |
| BR Allocators (ITSA4 + BRAP4) | 2,05 |
| CDI | 1,52 |
| BR ETF (PIBB11) | 1,45 |

⚠️ **Parcial e não conclusivo.** Faltam Europa e Japão, que são metade do universo
de allocators. Faltam também as métricas de risco da seção 15 — volatilidade,
drawdown, Sharpe, Sortino, janelas móveis —, sem as quais patrimônio final
isolado não decide nada. Ver `docs/methodology.md`, seção 11.

**Próximo passo:** métricas de risco e janelas móveis; destravar Europa e Japão.

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
