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
| Yahoo Finance (`query1`/`query2`) | **HTTP 429** em todos os símbolos, inclusive com User-Agent de navegador e cookie de sessão. O handshake de crumb (`fc.yahoo.com`) também responde 429. Bloqueio por IP, não rate-limit transitório. |
| Stooq (`.com` e `.pl`) | Desafio anti-bot com prova de trabalho em JavaScript. Requer navegador. |
| brapi.dev | Exige token (`MISSING_TOKEN`). Cadastro gratuito disponível. |
| Frankfurter | Funciona, **mas só câmbio** — não resolve renda variável, e o PTAX é fonte melhor para a ótica brasileira. |

O código do probe (`capallo probe`) está pronto e testado; ele reporta por
símbolo: moeda, data inicial, cobertura ano a ano, contagem de dividendos e
splits, e presença de close ajustado. **Só falta uma fonte que responda.**

### Caminhos, em ordem de preferência

1. **Rodar `capallo probe` da sua própria rede.** É plausível que o bloqueio seja
   deste ambiente. Custo zero, resposta imediata, e é o primeiro teste a fazer.
2. **Provedor com chave gratuita.** brapi.dev resolve só o Brasil. Para cobertura
   global com histórico desde 2005 e eventos societários, os candidatos reais são
   pagos ou têm limites apertados no plano gratuito.
3. **Dado oficial por bolsa.** Mais trabalhoso, mas é a fonte de maior qualidade e
   a única com rastreabilidade real de eventos societários.

### O risco continua sendo o previsto

O `methodology.md` já apontava **INVE-B, GBLB, 8058 e 8031** como o ponto frágil:
total return correto desde 2005, em moeda local, com eventos societários
rastreáveis. O spike não refutou nem confirmou essa preocupação — apenas mostrou
que ela **não pode ser resolvida com fontes gratuitas anônimas**.

Enquanto essas quatro séries não estiverem validadas, escrever o motor de backtest
é construir sobre fundação não verificada.

---

## 3. Conclusão

**Pode seguir:** tudo que depende só de macro — aporte real corrigido pelo IPCA,
conta caixa remunerada ao CDI, conversão cambial, e a estratégia CDI inteira, que
é executável hoje de ponta a ponta.

**Não pode seguir:** as estratégias Capital Allocators e Passive ETFs, até haver
fonte confiável de preço e evento societário.

**Próximo passo concreto:** rodar `capallo probe` de uma rede não bloqueada e
comparar o resultado com esta tabela.
