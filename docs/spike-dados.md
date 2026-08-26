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

### O bloqueio do Yahoo não é de IP — a API está fechada

Testado de duas origens completamente distintas:

| Origem | IP | Yahoo | B3 |
|---|---|---|---|
| Rede local | `45.170.152.180` | **429** | 200 |
| Runner GitHub Actions | `20.57.47.228` | **429** | 200 |

Sem variáveis de proxy no caminho, com User-Agent de navegador, cookie de sessão e
3 segundos de pausa entre requisições. O handshake de crumb (`fc.yahoo.com`)
também responde 429.

**Conclusão: trocar de IP não resolve.** A API pública do Yahoo está fechada para
acesso programático anônimo, de qualquer origem. O workflow `.github/workflows/probe.yml`
fica como sentinela semanal — se o bloqueio ceder, ele avisa.

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

Estes dados são considerados **essenciais** para o projeto: sem eles não existem
as seções 14 (comparação regional), 22 (Allocator Premium) nem a pergunta central
do estudo. O Brasil sozinho não responde nada.

### Rodada 2: fontes primárias — emissores, bolsas e RIs

Tentativa de ir direto à fonte, contornando agregadores. Resultado:

| Fonte | Alvo | Resultado |
|---|---|---|
| iShares / BlackRock | IVV, IEV, EWJ | Endpoint de NAV histórico existe e responde **HTTP 200 com `content-type: text/csv`** — mas o corpo é a página HTML do produto. Gate de bot servido sob o content-type do arquivo. |
| API Nasdaq (`api.nasdaq.com`) | IVV | JSON válido, `totalRecords: 0` para **toda** data testada (2006, 2010, 2015, 2020, 2026). Endpoint desativado ou fechado. |
| Nasdaq Nordic (`DataFeedProxy.aspx`) | INVE-B | HTTP 301 → site novo, renderizado em JavaScript. O proxy de dados legado saiu do ar. |
| RI Investor AB | INVE-B | Página fala explicitamente de *total return* como a métrica da casa, mas **nenhum link estático** de `.csv`/`.xls`. Dado renderizado no cliente. |
| RI Markel | MKL | Idem — sem link estático de dado. |
| JPX | 8058, 8031 | Página institucional responde; estatísticas são navegação em JavaScript. |

**O padrão é consistente e vale registrar:** as fontes primárias não estão
*bloqueando* por reputação, como o Yahoo. Elas simplesmente **não expõem mais
arquivos estáticos** — migraram para front-ends que montam a tabela no cliente,
consumindo APIs internas autenticadas por sessão de navegador.

Isso muda a natureza do problema. Não é "achar a URL certa": as URLs certas foram
encontradas e respondem. É que **o dado só existe do outro lado de um navegador**.

A B3 é a exceção justamente por ser retrógrada no bom sentido — publica um arquivo
de largura fixa por ano, como em 1998, e por isso é a fonte mais acessível do
projeto inteiro.

### Rodada 3: automação de navegador

Se o dado só existe depois do JavaScript rodar, rodar o JavaScript é a resposta
técnica adequada. Montado com **Playwright + Chromium headless próprio** — não usa
o navegador pessoal, roda isolado, e é reproduzível em CI.

**A automação funciona.** O Chromium resolveu a prova de trabalho do Stooq e
carregou a página de 8058.JP com cotação real, onde o `curl` só via o desafio.
Ferramenta validada.

Mas ela esbarrou em outra coisa:

| Fonte | Resultado com navegador |
|---|---|
| Stooq — página | ✅ carrega, prova de trabalho resolvida |
| Stooq — CSV histórico | ❌ o download entrega `error.txt` com **"Access denied"** |
| Euronext (GBLB) | ⚠️ endpoint devolve **628 KB de payload cifrado** (AES, `ct`/`iv`/`s`), decifrado no cliente |
| WSJ | ❌ HTTP 401 |
| API Nasdaq Nordic | ❌ erro de protocolo |
| S&P Dow Jones | ❌ navegação recusada |

### Onde a busca para, e por quê

O Stooq não *falha* ao entregar o CSV — ele **recusa explicitamente**. Exportação
em massa é recurso pago lá. O Euronext não expõe o histórico em claro: ele cifra o
payload para que só o próprio front-end o leia.

Nos dois casos existe caminho técnico para obter o dado assim mesmo — raspar a
tabela renderizada, ou reimplementar a decifragem. **Não foi feito, por decisão.**
São controles de acesso deliberados, e contorná-los é diferente de ler uma página
pública. Um projeto que se apresenta como portfólio não deveria ter no histórico um
commit que burla proteção de fonte de dados.

A automação de navegador continua no projeto como ferramenta legítima — ela é a
resposta certa para fontes que publicam o dado abertamente mas o renderizam no
cliente. Só não é a resposta para fontes que decidiram não publicar.

### Caminhos restantes

1. **Provedor pago, um mês** (~US$20–80). As 9 séries são de um período fechado que
   nunca muda: baixa uma vez, valida, congela em Parquet, cancela. Não é assinatura
   recorrente, é uma compra única de dado histórico. **Menor risco e menor esforço.**
2. **Relatórios anuais e RIs.** Investor AB e GBL publicam total return nos próprios
   relatórios — são investment companies, essa é *a* métrica que elas divulgam.
   Parcialmente manual, mas com 9 ativos é viável, e é a fonte de maior qualidade
   e melhor rastreabilidade de evento societário.
3. **Combinação.** Provedor pago para as séries diárias, RI como validação cruzada
   de INVE-B, GBLB, 8058 e 8031 — os quatro que a metodologia marcou como frágeis.
   Duas fontes independentes discordando é exatamente o sinal que se quer ver antes
   de confiar no número final.

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
