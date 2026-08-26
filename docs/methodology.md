# Metodologia

Documento de referência. Toda regra aqui é **congelada antes** do primeiro backtest
oficial. Alterações posteriores viram *variantes de robustez*, nunca reescrita
retroativa da estratégia principal.

## 1. Investidor-base

Investidor brasileiro, aportes recorrentes de jan/2006 a dez/2025. Unidade
econômica fundamental: **BRL**.

## 2. Aportes

| Regra | Decisão |
|---|---|
| Valor inicial | R$ 1.000 em jan/2006 |
| Dia | 1º dia útil do mês, execução no **fechamento** |
| Mercado fechado | executa no próximo pregão daquele mercado; caixa retido até lá |
| Cenário nominal | R$ 1.000 fixos (secundário) |
| Cenário real | **principal** — reajustado pelo IPCA |
| Reajuste IPCA | **anual**, em janeiro, pelo IPCA acumulado do ano anterior |

O reajuste é anual, não mensal, por dois motivos: é o que uma pessoa real faz
(reajusta o aporte quando reajusta a renda) e evita *lookahead* — o IPCA do mês
corrente ainda não foi divulgado no dia do aporte.

## 3. Execução e carteira

| Regra | Decisão |
|---|---|
| Ações fracionárias | **permitidas** (documentado como premissa) |
| Caixa residual | conta caixa remunerada ao **CDI**, inclusive nas pernas estrangeiras |
| Rebalanceamento | **via aporte**, anual em janeiro; **sem venda** |
| Aporte mensal | proporcional aos pesos-alvo |

Fracionário evita *cash drag* artificial: R$1.000 divididos em 8 ativos dão ~R$125
por ativo, e o lote de 100 de ITSA4 em 2006 era inviável. Rebalanceamento com venda
dispara IR e distorceria a comparação com o CDI.

## 4. Dividendos

Reinvestidos **no próprio ativo pagador**, na **data de pagamento**, **líquidos de
imposto na fonte**. Alíquotas estatutárias por país (refinar se houver dado melhor):

| País | Retenção |
|---|---|
| 🇧🇷 Brasil | dividendos isentos; JCP 15% |
| 🇺🇸 EUA | 30% (não há tratado com o Brasil) |
| 🇸🇪 Suécia | 30% |
| 🇧🇪 Bélgica | 30% |
| 🇯🇵 Japão | 15% |

Ignorar retenção favoreceria artificialmente allocators estrangeiros de alto
payout — exatamente o viés que a metodologia quer evitar.

## 5. Câmbio

Moedas: BRL, USD, SEK, EUR, JPY.

Decomposição sempre em **retorno local do ativo × efeito FX da moeda subjacente**.

⚠️ IVV, IEV e EWJ são listados em USD, mas seus ativos subjacentes são EUR/JPY/etc.
O wrapper USD é tratado como **transparente**: a exposição cambial é atribuída à
moeda do mercado subjacente, não à moeda de listagem. Sem isso, a decomposição
ficaria assimétrica entre a perna passiva e a perna dos allocators (INVE-B em SEK,
8058 em JPY).

## 6. Estratégias

| Estratégia | Composição |
|---|---|
| Capital Allocators | 12,5% em cada uma das 8 empresas |
| Passive ETFs | 25% Brasil / EUA / Europa / Japão |
| CDI | 100% CDI |

Sem carteiras 60/40, 70/30 na V1.

## 7. Tipos de experimento

Resultados **nunca misturados** entre tipos.

1. **Historical Reality** (principal) — apenas produtos realmente compráveis à época
2. **Index Benchmark** — índices no lugar dos ETFs, elimina tracking error e taxas
3. **Modern Alternative** — contrafactual com alternativas modernas

## 8. Métricas

Patrimônio final nominal e real; total aportado nominal e real; retorno acumulado;
CAGR; retorno real anualizado; volatilidade; max drawdown; Sharpe; Sortino; pior e
melhor janela de 12 meses; tempo de recuperação; efeito cambial; efeito da inflação.

Métrica-síntese: **para cada R$1 de poder de compra aportado, quantos reais de poder
de compra o investidor terminou possuindo?**

## 9. Robustez

- **Rolling returns** — janelas de 1, 3, 5 e 10 anos
- **Múltiplas datas de início** — 2006→2025, 2007→2025, ... 2015→2025
- **Contribuição individual** de cada ativo ao resultado
- **Remover o melhor ativo** — a conclusão sobrevive sem a empresa excepcional?
- **Remover o pior ativo**
- **Crises** — 2008, crise europeia, recessão brasileira, COVID-19, ciclos de juros.
  Regras **não mudam** durante crises; apenas se observa.

## 10. Allocator Premium

`retorno dos Capital Allocators − retorno dos ETFs equivalentes`, calculado por
região e global, **sempre relacionado ao risco adicional assumido**. "+1 p.p. ao ano"
só significa algo junto de quanto risco extra foi necessário.

## 11. Placar

Vencedor não é decidido por patrimônio final. Placar multi-métrica: patrimônio real,
retorno real anualizado, volatilidade, max drawdown, tempo de recuperação, Sharpe,
Sortino, % de vitórias em janelas de 5 e 10 anos.

## Riscos

**O maior risco do projeto é dado, não código.** Total return com eventos
societários corretos desde 2005, em moeda local, com licença utilizável, para:

- INVE-B (Estocolmo)
- GBLB (Bruxelas)
- 8058 e 8031 (Tóquio)

Fontes gratuitas dão séries "ajustadas" para esses tickers com qualidade irregular
pré-2010 e sem rastreabilidade de eventos. **Validar a disponibilidade desses quatro
antes de escrever o motor.**

"Dado público" não significa API gratuita + histórico perfeito + licença irrestrita.
Verificar sempre: fonte, qualidade, licença, frequência, dados ausentes, mudança de
ticker, eventos societários, ajustes, moeda e calendário de negociação.
