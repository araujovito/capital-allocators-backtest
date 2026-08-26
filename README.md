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

- ✅ **Macro resolvida:** CDI, IPCA e PTAX (USD/EUR/JPY/SEK) do Banco Central,
  validados na janela inteira. `capallo fetch-macro`
- ⚠️ **Renda variável bloqueada:** nenhuma fonte gratuita anônima entregou preços
  das 8 ações e 4 ETFs. É o bloqueador do motor de backtest.

Barra a ser batida, já quantificada: o **CDI rendeu 4,46% a.a. reais** entre 2006
e 2025 (IPCA acumulado 192,0%; CDI nominal 10,20% a.a.).

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e "./python[dev]"

capallo fetch-macro   # baixa e valida CDI, IPCA e PTAX
capallo probe         # spike de viabilidade das series de renda variavel
pytest tests/

# Rust (ainda não instalado nesta máquina)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
cd engine && cargo build --release
```
