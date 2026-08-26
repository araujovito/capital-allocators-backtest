# Spike de viabilidade de dados

**Data:** 2026-08-26
**Pergunta:** as séries necessárias existem, com qualidade e licença utilizáveis,
antes de valer a pena escrever o motor de backtest?

**Resposta curta:** a camada macro está resolvida e validada. A camada de renda
variável **não** está — e é aí que o projeto tem risco real.

---

## 1. Camada macro — RESOLVIDA ✅

Fonte única: **Banco Central do Brasil**. Oficial, gratuita, sem chave de API,
sem anti-bot, sem limite prático de requisição.

| Série | API | Código | Observações | Cobertura |
|---|---|---|---|---|
| CDI | SGS | 12 | 5.044 obs | 2005-12-01 → 2025-12-31, zero nulos |
| IPCA | SGS | 433 | 241 obs | **240/240 meses** da janela, nenhum faltando |
| USD/BRL | Olinda PTAX | — | 5.044 obs | compra e venda |
| EUR/BRL | Olinda PTAX | — | 5.044 obs | compra e venda |
| JPY/BRL | Olinda PTAX | — | 5.044 obs | compra e venda |
| SEK/BRL | Olinda PTAX | — | 5.044 obs | compra e venda |

Reproduzir com `capallo fetch-macro` → grava Parquet em `data/curated/`.

### Duas descobertas que mudaram o código

**O SGS não expõe a coroa sueca.** Os códigos de câmbio do SGS cobrem USD, EUR,
JPY e GBP, mas não SEK — e Investor AB negocia em SEK. A API Olinda/PTAX cobre as
quatro moedas de forma uniforme, então o coletor de câmbio usa Olinda, não SGS.

**PTAX tem compra e venda, com spread não desprezível.** Médias na janela: USD
0,159%, EUR 0,179%, JPY 0,180%, SEK 0,204%. Ao longo de 240 aportes convertidos,
escolher compra ou venda arbitrariamente introduz viés sistemático. O coletor
guarda **as duas** e deixa a escolha para o pipeline — que precisa decidir e
registrar em `decisions.md`.

### Sanidade econômica

Os números batem com a realidade conhecida do período:

```
IPCA acumulado 2006-2025    192,0%   (5,50% a.a.)
  R$1.000 de jan/2006  =  R$2.920 em dez/2025
CDI acumulado 2006-2025     598,2%   (10,20% a.a. nominal)
  deflacionado pelo IPCA           4,46% a.a. REAL
USD/BRL   2,34 → 5,50   (+135,1%)
EUR/BRL   2,77 → 6,47   (+133,6%)
SEK/BRL   0,294 → 0,598 (+103,2%)
JPY/BRL   0,0198 → 0,0351 (+77,2%)
```

**Isso já define a barra a ser batida:** qualquer estratégia de renda variável
precisa superar **4,46% a.a. reais** para ter valido o risco. É a resposta
quantitativa à pergunta da seção 12 do checkpoint.

---

## 2. Camada de renda variável — BLOQUEADA ⚠️

Nenhuma fonte gratuita e sem cadastro entregou preços das ações e ETFs a partir
deste ambiente.

| Fonte | Resultado |
|---|---|
| **B3 — arquivo COTAHIST** | ✅ **FUNCIONA.** Ver seção 2.1. |
| Yahoo Finance (`query1`/`query2`) | **HTTP 429** em todos os símbolos, inclusive com User-Agent de navegador e cookie de sessão. O handshake de crumb (`fc.yahoo.com`) também responde 429. |
| Stooq (`.com` e `.pl`) | Desafio anti-bot com prova de trabalho em JavaScript. Requer navegador. |
| brapi.dev | Exige token (`MISSING_TOKEN`). Cadastro gratuito disponível, cobre só o Brasil. |
| EODHD | Token `demo` funciona, mas só em símbolos de demonstração. `INVE-B.ST` → `Forbidden`. Cobertura global real é paga. |
| Alpha Vantage | Chave `demo` funciona em símbolos fixos. Chave gratuita tem limite diário apertado e cobertura internacional fraca. |
| Tiingo | 403 sem chave. |
| Frankfurter | Funciona, mas só câmbio — e o PTAX é fonte melhor para a ótica brasileira. |

### O bloqueio do Yahoo não é do ambiente

Verificado: **sem variáveis de proxy**, IP de saída `45.170.152.180` — a rede real
da máquina. O 429 persiste com 3 segundos de pausa entre requisições. Rodar de
outro terminal na mesma máquina não muda nada. O caminho "tentar da própria rede"
está esgotado.

## 2.1 Brasil — RESOLVIDO com dado oficial ✅

A B3 publica o arquivo histórico anual `COTAHIST_A<ANO>.ZIP`, sem chave e sem
anti-bot:

```
https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A2006.ZIP
```

Verificado em 2006 — 8,9 MB compactados, 47 MB de texto, layout de largura fixa:

| Ticker | Pregões em 2006 |
|---|---|
| ITSA4 | 246 |
| BRAP4 | 246 |
| PIBB11 | 246 |

Campos relevantes do layout: posição 1-2 tipo de registro, 3-10 data, 11-12 CODBDI,
13-24 código de negociação, 109-121 preço de fechamento (2 casas implícitas).

⚠️ **Ressalva importante:** COTAHIST traz **preço bruto**, sem ajuste por
proventos, splits ou bonificações. Ele resolve a série de preços, **não** o total
return da seção 11 do checkpoint. Os eventos societários de Itaúsa, Bradespar e
PIBB11 precisam vir à parte — RI das empresas, CVM, ou o próprio arquivo de
proventos da B3.

O código do probe (`capallo probe`) está pronto e testado; ele reporta por
símbolo: moeda, data inicial, cobertura ano a ano, contagem de dividendos e
splits, e presença de close ajustado. **Só falta uma fonte que responda.**

## 2.2 EUA, Europa e Japão — ainda bloqueados ⚠️

Restam **BRK.B, MKL, INVE-B, GBLB, 8058, 8031, IVV, IEV, EWJ**.

O padrão da B3 sugere o caminho: **dado oficial por bolsa**. Nasdaq/NYSE, Nasdaq
Stockholm, Euronext Brussels e JPX publicam históricos, com formatos e políticas
de acesso distintos entre si. É trabalhoso, mas é a fonte de maior qualidade e a
única com rastreabilidade real de eventos societários.

A alternativa é um provedor pago com cobertura global desde 2005. Decisão de custo,
não técnica — precisa da sua chamada.

### O risco continua sendo o previsto

O `methodology.md` já apontava **INVE-B, GBLB, 8058 e 8031** como o ponto frágil:
total return correto desde 2005, em moeda local, com eventos societários
rastreáveis. O spike não refutou nem confirmou essa preocupação — apenas mostrou
que ela **não pode ser resolvida com fontes gratuitas anônimas**.

Enquanto essas quatro séries não estiverem validadas, escrever o motor de backtest
é construir sobre fundação não verificada.

---

## 3. Conclusão

**Pode seguir:**
- Tudo que depende só de macro — aporte real corrigido pelo IPCA, caixa remunerado
  ao CDI, conversão cambial. A estratégia **CDI é executável hoje** de ponta a ponta.
- A **comparação regional do Brasil** (seção 14 do checkpoint): Itaúsa + Bradespar
  × PIBB11, assim que os proventos forem coletados. É um recorte completo do estudo,
  com dado oficial, e serve para validar o motor inteiro em escala reduzida.

**Não pode seguir:** as estratégias globais, até haver fonte para os nove ativos
de EUA, Europa e Japão.

**Próximo passo concreto:** coletar proventos e eventos societários de ITSA4, BRAP4
e PIBB11, montar o total return brasileiro e rodar o primeiro backtest regional.
Isso exercita aporte, caixa, dividendos, rebalanceamento e IPCA — todo o motor —
sem depender das fontes bloqueadas.
