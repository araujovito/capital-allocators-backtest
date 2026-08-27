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

## 2.3 Reformulando o problema — restrição: custo zero

O projeto opera com **orçamento zero**. Isso é restrição de projeto, não obstáculo
a contornar, e força duas perguntas que deveriam ter sido feitas antes.

### Pergunta 1: de quantos ativos estamos mesmo falando?

Dos 9 que faltam, **5 são listados nos EUA**: BRK.B, MKL, IVV, IEV e EWJ. Ações
e ETFs americanos são o segmento mais coberto por planos gratuitos de qualquer
provedor. Só **4** são de bolsa estrangeira: INVE-B (Estocolmo), GBLB (Bruxelas),
8058 e 8031 (Tóquio).

O problema difícil não tem 9 séries. Tem 4.

### Pergunta 2: qual granularidade o estudo realmente exige?

Revisando a metodologia: os aportes são **mensais**, o rebalanceamento é **anual**,
as janelas móveis são de 1/3/5/10 anos e o drawdown é medido sobre o patrimônio,
que só muda de forma relevante entre aportes.

**Dado diário não é requisito — dado mensal fecha o estudo.** O que se perde é
precisão na volatilidade e no drawdown intramês; ambos passam a ser medidos ponta
a ponta do mês, o que é uma escolha metodológica defensável e precisa ser
registrada como premissa, não escondida.

Isso importa porque histórico **mensal ajustado de 20+ anos costuma caber em uma
única chamada** nos planos gratuitos, enquanto o diário estoura qualquer limite.
A mesma cota gratuita que não cobre o estudo em dado diário cobre com folga em
mensal.

### Caminhos restantes, todos gratuitos

1. **Planos gratuitos com cadastro** (sem cartão). Cobrem com sobra os 5 ativos
   americanos. Para os 4 estrangeiros, a cobertura varia por provedor e precisa
   ser testada — é o próximo experimento.
2. **Relatórios anuais e RIs.** Investor AB e GBL publicam total return nos próprios
   relatórios — são investment companies, essa é *a* métrica que divulgam sobre si
   mesmas. Granularidade anual, coleta parcialmente manual, mas é a fonte de melhor
   rastreabilidade de evento societário e serve como **validação cruzada**.
3. **Redução explícita de escopo, se necessário.** Se os 4 estrangeiros não forem
   obteníveis, a alternativa honesta é publicar o estudo com o universo que existe e
   **declarar a ausência**, em vez de trocar as empresas por outras mais fáceis de
   achar. Trocar violaria a regra anti-cherry-picking da seção 4 — o universo foi
   congelado antes, e conveniência de dado não é critério para alterá-lo.

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


---

## 4. Rodada 4: Twelve Data no plano gratuito

Chave gratuita (sem cartão), plano Basic: 8 requisições/minuto, 800/dia.

### O que funcionou

**Os 5 ativos listados nos EUA, com total return completo:**

| Ticker | Meses | Total return 2006-2025 (USD) |
|---|---|---|
| BRK-B | 240/240 | +757,2% — 11,34% a.a. |
| MKL | 240/240 | +543,6% — 9,76% a.a. |
| IVV | 240/240 | +680,0% — 10,82% a.a. |
| IEV | 240/240 | +183,2% — 5,34% a.a. |
| EWJ | 240/240 | +101,1% — 3,56% a.a. |

Os números conferem: 10,82% a.a. é o total return conhecido do S&P 500 no período.

**A descoberta que destravou isso:** os endpoints `/dividends` e `/splits` são
pagos (HTTP 403 explícito). Mas o `time_series` aceita **`adjust=all`**, que já
devolve o fechamento ajustado por proventos e desdobramentos — e esse parâmetro
funciona no plano gratuito.

Validação do ajuste: IVV em jan/2006 fecha a **127,75 bruto** e **87,35 ajustado**.
A razão de 0,684 corresponde a ~20 anos de dividendos do S&P 500 reinvestidos.
O ajuste é real, não artefato.

### O que não funcionou

As bolsas de origem dos 4 estrangeiros são explicitamente pagas:

| Ticker | Bolsa | Resposta |
|---|---|---|
| GBLB | Euronext | "available starting with the **Grow** or Venture plan" |
| 8058 | JPX | "available starting with the **Pro** or Venture plan" |
| 8031 | JPX | "available starting with the **Pro** or Venture plan" |
| INVE.B | OMX | 404 — símbolo existe no catálogo, série indisponível |

### A alternativa OTC, e por que ela não resolve

As mesmas empresas negociam no mercado de balcão americano, coberto pelo plano
gratuito. Mas o histórico não alcança o início do estudo:

| Símbolo OTC | Empresa | Início | Meses |
|---|---|---|---|
| MITSF | Mitsui | **2006-01** | 240 ✅ |
| GBLBF | GBL | 2010-01 | 193 |
| IVSBF | Investor AB | 2010-02 | 192 |
| MSBHF | Mitsubishi | 2010-06 | 187 |

Três dos quatro só começam em 2010. **Isso descarta a crise de 2008**, que é um
dos períodos de estresse que a seção 18 do checkpoint pede explicitamente para
analisar — e é justamente onde uma holding se diferencia de um índice.

Usar OTC significaria comparar allocators europeus e japoneses com ETFs em janelas
diferentes, o que enviesa o resultado a favor de quem não viveu 2008. Não é opção
para o experimento principal.

Há ainda uma ressalva de qualidade: ações estrangeiras no balcão americano têm
negociação rala e preços frequentemente defasados em relação à bolsa de origem.
Mesmo no período coberto, MITSF precisaria de validação cruzada contra 8058 antes
de ser usado.

## 5. Estado consolidado

| Camada | Estado | Fonte |
|---|---|---|
| CDI, IPCA, PTAX | ✅ completa e validada | Banco Central |
| BRK-B, MKL, IVV, IEV, EWJ | ✅ total return, 240/240 meses | Twelve Data (grátis) |
| ITSA4, BRAP4, PIBB11 | ⬜ preço completo; faltam proventos | B3 COTAHIST |
| INVE-B, GBLB, 8058, 8031 | ❌ indisponível de graça no período completo | — |

**8 dos 12 ativos estão resolvidos ou a um passo de estar.** O bloqueio se
concentrou nos 4 allocators de Europa e Japão.


---

## 6. Coleta da B3 concluída — e uma armadilha do layout

Baixados os 20 arquivos anuais (550 MB) e extraídos os três tickers brasileiros:

| Ticker | Pregões | Período | Preço bruto |
|---|---|---|---|
| ITSA4 | 4.953 | 2006-01-02 → 2025-12-30 | 7,45 → 11,68 |
| BRAP4 | 4.953 | 2006-01-02 → 2025-12-30 | 58,50 → 19,90 |
| PIBB11 | 4.953 | 2006-01-02 → 2025-12-30 | 48,00 → 284,25 |

Contagem idêntica entre os três, sem nenhum ano com menos de 200 pregões.

### A armadilha: PIBB11 não é CODBDI 02

O filtro natural para cotação de ação é `CODBDI = 02` (lote padrão). Com ele,
**PIBB11 retornava só 92 pregões de 2019** — e a série parecia simplesmente não
existir.

A B3 classifica ETF como **certificado de investimento, `CODBDI = 14`**. O PIBB11
aparece sob 14 durante quase toda a série e migra para 02 no meio de 2019, quando
os dois códigos convivem (156 + 92 = 248 pregões).

Filtrar só por 02 teria perdido **13 dos 20 anos** da série — e o pior é que
falharia em silêncio: o arquivo existe, o parser roda, o resultado sai. Só a
checagem de que os três tickers da mesma bolsa precisam ter o mesmo número de
pregões expôs o problema. Essa validação virou teste.

### Os preços brutos ilustram por que proventos não são opcional

ITSA4 sai de 7,45 para 11,68 em vinte anos — **+57% bruto**, o que faria a Itaúsa
parecer um investimento medíocre. Mas a Itaúsa distribuiu dividendos e JCP e fez
bonificações sucessivas ao longo de todo o período, e nada disso está no COTAHIST.
BRAP4 chega a *cair* de 58,50 para 19,90 em preço bruto, por conta de
desdobramento.

Comparar esses números com o total return já obtido para os ativos americanos
produziria uma conclusão completamente invertida. **O total return brasileiro está
bloqueado até os proventos serem coletados** — é a próxima tarefa da perna Brasil.


---

## 7. Proventos brasileiros: metade resolvida, metade suspeita

Fonte encontrada: o **proxy oficial da B3** que alimenta o site de companhias
listadas. Público, gratuito, sem chave — o payload vai em base64 na própria URL.

A CVM foi testada antes e descartada: `dados.cvm.gov.br/dados/CIA_ABERTA/EVENTOS/`
só publica recompra de ações, não proventos por ação.

### Proventos em dinheiro — completos ✅

`GetListedCashDividends`, paginado, com histórico integral:

| Ticker | Registros | Cobertura | Tipos |
|---|---|---|---|
| ITSA4 | 504 | 1996 → 2026 | 322 JCP, 182 dividendos |
| BRAP4 | 140 | 2001 → 2025 | 74 JCP, 66 dividendos |

A separação entre **dividendo e JCP importa**: JCP sofre 15% de retenção na fonte
e dividendo é isento. Itaúsa paga majoritariamente JCP, então tratar tudo como
dividendo superestimaria o retorno líquido dela.

### Eventos em ações — um faltava mesmo, o outro era falso alarme

`GetListedSupplementCompany` devolve bonificação, desdobramento e grupamento, mas
o resultado não passa no teste de sanidade:

| Ticker | Eventos na janela | Retorno ingênuo (preço + proventos) |
|---|---|---|
| ITSA4 | 3 | **5,89% a.a.** |
| BRAP4 | 3 | **0,61% a.a.** |

Ambos ficam **abaixo do CDI** (10,20% a.a. nominal), e a Itaúsa registra um único
evento em ações — uma bonificação de 2% em 2025 — em vinte anos, sendo uma empresa
conhecida por bonificar com regularidade.

**A primeira heurística usada aqui estava errada, e vale registrar por quê.**

Ela comparava o retorno de cada ativo com o CDI e acusava "dado faltando" quando
ficava abaixo. Isso produziu falso positivo: ação brasileira render menos que o CDI
entre 2006 e 2025 é fato corriqueiro, não sintoma de dado ausente. A heurística
confundia *desempenho fraco* com *erro de coleta* — e, pior, teria levado a
"corrigir" dado correto até ele produzir o resultado esperado, que é exatamente o
viés que a metodologia do projeto existe para evitar.

O teste que a substituiu olha para **evidência direta**: desdobramento, grupamento
e bonificação deixam descontinuidade artificial no preço bruto. A série salta e não
há evento registrado? Aí sim há dado faltando.

Resultado, com corte em 25% de variação diária:

| Ticker | Data | Variação | Evento na B3? | Veredicto |
|---|---|---|---|---|
| ITSA4 | 2008-10-13 | **+25,1%** | não | rali global pós-Lehman — **não é evento** |
| BRAP4 | 2007-01-09 | **−50,4%** | não | desdobramento, fator implícito **2,02** |
| BRAP4 | 2007-10-16 | **−51,0%** | não | desdobramento, fator implícito **2,04** |
| BRAP4 | 2021-12-17 | −58,5% | **sim** | distribuição de ações da Vale, já registrada |
| PIBB11 | — | nenhum | — | série limpa |

**ITSA4 estava completa o tempo todo.** Os 5,89% a.a. são reais, não artefato — a
Itaúsa de fato rendeu menos que o CDI no período, e o estudo tem de poder dizer
isso. **BRAP4 tinha dois desdobramentos 1:2 ausentes do cadastro da B3**, ambos em
2007, agora identificados com fator implícito e registrados em
`data/manual/b3_missing_events.csv` com status `inferido`, à espera de confirmação
documental.

O detector só reporta quedas: alta de 25% em um pregão é movimento de mercado
comum em crise, enquanto desdobramento e grupamento têm assinatura característica
no sinal e na magnitude.

O BRAP4 tem uma complicação adicional e real: o evento `REST CAP ACOES` de
dezembro/2021 distribuiu **ações da Vale** aos acionistas — um provento em espécie,
de valor relevante, que nenhuma série de preço captura e que precisa ser avaliado
pela cotação da Vale na data para entrar no total return.

### Por que isso virou código, não só nota

A função `reconcile()` compara o retorno ingênuo de cada ativo com o CDI do mesmo
período e dispara aviso quando o resultado é implausível ou quando há poucos
eventos societários. É uma **guarda contra o pior tipo de erro deste projeto**: o
que não quebra nada, produz um número, e leva a uma conclusão invertida.

Sem ela, ITSA4 entraria no backtest rendendo 5,89% a.a. e o estudo concluiria com
confiança que capital allocators brasileiros perdem do CDI — possivelmente por
causa de bonificações não coletadas.

**O total return brasileiro continua bloqueado**, agora por um motivo preciso e
localizado: validar os eventos em ações de ITSA4 e BRAP4 contra os RIs das
empresas, e valorar a distribuição de ações da Vale de 2021.


---

## 8. Total return brasileiro fechado

Série de retorno total montada a partir de preço bruto do COTAHIST mais todos os
eventos, com validação de que **não sobra descontinuidade artificial**.

| Ticker | Unidades finais | TR nominal | % a.a. nominal | % a.a. **real** |
|---|---|---|---|---|
| BRAP4 | 36,751 | +1.150,2% | 13,46% | **7,54%** |
| ITSA4 | 2,834 | +344,4% | 7,74% | **2,12%** |
| PIBB11 | 1,000 | +492,2% | 9,30% | **3,60%** |

Referência: CDI 10,20% nominal / **4,46% real**. IPCA 5,50% a.a.

### O modelo é de unidades acumuladas, não de fator retroativo

Parte-se de 1 ação e acompanha-se quantas ações o investidor passa a ter:
desdobramento multiplica, provento reinvestido soma. O índice é `unidades × preço`.
Cada evento fica explícito e auditável, ao contrário de um fator de ajuste aplicado
retroativamente sobre o preço.

### A distribuição de ações da Vale, resolvida

O fator declarado pela B3 parecia não fechar: 33,2373% × R$79,17 = R$26,31, contra
uma queda observada de R$32,64 na data-ex.

A diferença **não era erro do fator** — era um dividendo em dinheiro de R$6,0439
com a mesma data-ex, que entra por outra série:

```
Vale        0,332373 × 79,17 = R$ 26,31
dinheiro     dividendo do dia = R$  6,04
                               ─────────
                                R$ 32,35
queda observada                 R$ 32,64
resíduo                         R$  0,29   ← mercado caiu 1,6% no dia
```

### Semântica da B3 que quase passou batido

O campo `lastDatePrior` é o **último pregão com direito**, não a data-ex — esta é o
pregão seguinte. Verificado na bonificação de 12,95% da BRAP4, cujo efeito no preço
aparece em 21/09/2021 e não em 20/09. Errar isso deslocaria todo evento em um dia.

### Dois bugs encontrados pela desconfiança de um número

O primeiro resultado deu **173 unidades** de BRAP4 partindo de uma ação. O número
passava em todas as validações, mas não fechava com a conta de guardanapo
(2 desdobramentos × bonificação × Vale × reinvestimento ≈ 40). Investigar a
discrepância revelou dois erros:

1. **Eventos anteriores à janela aplicados no primeiro pregão.** O desdobramento de
   2005 da BRAP4 entrava em 02/01/2006, porque a busca pelo pregão seguinte pegava
   o primeiro disponível. O investidor do estudo não detinha a ação em 2005 e não
   recebeu aquele desdobramento.
2. **Eventos contados duas vezes.** A B3 publica cada bonificação e desdobramento
   uma vez para ON e outra para PN, com o mesmo fator. Aplicar as duas **dobrava
   todo evento societário**.

Ambos inflavam o retorno da Bradespar sem quebrar nada e sem disparar validação
alguma. O que os pegou foi um número que não batia com a ordem de grandeza
esperada. Os dois viraram teste.

### A lista de exceções verificadas

A alta de 25,1% do ITSA4 em 13/10/2008 é movimento de mercado real — o rali global
que seguiu o anúncio coordenado de socorro bancário. Ela fica em
`data/manual/verified_market_moves.csv` com justificativa.

Isso importa metodologicamente: sem a lista, a validação acusaria erro para sempre
numa data correta, e a saída tentadora seria **afrouxar o limite do detector** —
que é exatamente o que o faria parar de encontrar desdobramentos reais.

### Primeira leitura do resultado, com a ressalva devida

Os allocators brasileiros em pesos iguais rendem ~10,6% a.a. nominais contra 9,30%
do PIBB11 — e a Bradespar sozinha, 13,46%, carrega o par, enquanto a Itaúsa perde
tanto do ETF quanto do CDI.

É precisamente o cenário que a seção 20 do checkpoint antecipou: *"uma única empresa
excepcional carregou a carteira inteira"*. **Nenhuma conclusão deve ser tirada
disto ainda** — falta o backtest com aportes mensais, que é sensível ao momento das
entradas de um jeito que a comparação ponta a ponta não é.


---

## 9. Fontes locais destravam Japão e Suécia

A hipótese: agregadores internacionais **revendem caro** o que a fonte da praça de
origem publica aberto, e a barreira real costuma ser o idioma, não a licença.

Confirmada em dois dos quatro casos.

| Ativo | Fonte | Idioma | Cobertura |
|---|---|---|---|
| 8058 Mitsubishi | **Kabutan** (株探) | japonês | **240/240 meses** |
| 8031 Mitsui | **Kabutan** (株探) | japonês | **240/240 meses** |
| INVE-B Investor AB | **Avanza** | sueco | **240/240 meses** |
| GBLB GBL | — | — | ainda sem fonte |

O Kabutan publica visão mensal (`ashi=mon`) desde 2001, em HTML de tabela simples,
sem JavaScript — a mesma qualidade de acesso da B3. A Avanza expõe a API de
gráfico da corretora, que aceita `timePeriod=infinity` e devolve série desde 1984.

Nenhuma das duas pede chave, cadastro ou pagamento. As mesmas séries custam plano
Pro na Twelve Data.

### Verificações que passaram

Os saltos mensais acima de 25% nas séries japonesas concentram-se todos em
**setembro a novembro de 2008** — as *sogo shosha* desabando na crise, movimento de
mercado real. Nenhum salto compatível com desdobramento, o que confirma que o
Kabutan já entrega preço ajustado por evento societário. A série sueca não tem
salto algum.

Duas armadilhas de formato, ambas viraram teste:

- **Kabutan usa ano de dois dígitos** (`06/01/31`). Interpretar como 1906
  destruiria a série inteira.
- **A Avanza rotula cada barra pelo último pregão do mês.** Pedir a partir de
  2006-01-01 devolve 2005-12-31 como primeira barra; a janela é buscada folgada e
  filtrada por período depois.

### O que ainda falta nestes três

**Preço não é total return.** As duas fontes ajustam por desdobramento, mas não por
dividendo. Sem a série de proventos, estes ativos **não podem entrar no backtest**:
compará-los com Berkshire e IVV, que já têm total return, subestimaria seu retorno
de forma sistemática — e Investor AB e as *sogo shosha* são pagadoras relevantes.

### GBL: o que já foi descartado

Euronext cifra o payload; Boursorama aposentou o endpoint de histórico (HTTP 410);
De Tijd responde 403; ABC Bourse está atrás de desafio anti-bot; Beursduivel mudou
de estrutura; a Avanza não lista o papel; a bolsa de Frankfurt responde 403 na API.
O site institucional migrou de `gbl.be` para `gbl.com`.

Resta procurar em holandês e francês belga com mais profundidade, e no RI em
`gbl.com`, que como investment company tende a publicar total return sobre si
mesma — o mesmo padrão observado na Investor AB.


---

## 10. Proventos de Japão e Suécia: parcialmente encontrados

Com preço resolvido para 8058, 8031 e INVE-B, o total return depende só da série de
proventos. Ela **não fechou**.

### O que foi encontrado

| Fonte | Ativo | Cobertura | Problema |
|---|---|---|---|
| **Avanza** (`/details`) | INVE-B | **2019-2026** | 15 eventos; faltam 13 anos da janela |
| **IR Bank** (irbank.net) | 8058, 8031 | **2010-2027** | tabela com `rowspan`, colunas embaralham no parse; faltam 2006-2009 |
| Kabutan `/finance` | 8058 | recente | mistura dividendo com revisão de resultado |

O achado positivo: a Avanza expõe `exDate`, `paymentDate`, `amount` e tipo, e o IR
Bank tem coluna **調整** (dividendo ajustado por desdobramento), que é exatamente o
campo necessário. As duas fontes servem — só não alcançam o início da janela.

### O que foi descartado

| Fonte | Resultado |
|---|---|
| RI Mitsubishi (EN e JP) | HTTP 403 |
| RI Mitsui (EN e JP) | HTTP 404 |
| RI Investor AB | aplicação de página única, sem tabela estática |
| Nordnet | exige sessão autenticada |
| **Listagens alemãs na Twelve Data** | MBI, MBI1, MTS1, EAI e o ISIN sueco em FSX/XSTU: **todos exigem plano Grow** |

A tentativa das bolsas alemãs merecia registro porque era a saída mais elegante: as
quatro empresas negociam na Alemanha, e o `adjust=all` da Twelve Data já entrega
total return. Mas o plano gratuito cobre **apenas listagens dos EUA** — nenhuma
praça europeia ou asiática, nem por ISIN.

### O que sobrou, e por que não é aceitável ainda

Usar preço sem proventos para estes três **enviesaria o estudo contra os
allocators**. Investor AB e as *sogo shosha* são pagadoras relevantes: as japonesas
rendem 2% a 5% ao ano em dividendo pelos próprios dados do IR Bank, e a Investor AB
paga duas vezes por ano. Vinte anos de dividendo ignorado é um buraco de dezenas de
pontos percentuais, comparado contra Berkshire e IVV que **já têm** total return.

Seria erro pior do que não ter o ativo: produziria um número, passaria em todas as
validações, e responderia à pergunta central do estudo de forma invertida.

### Caminho restante

**Relatórios anuais.** Companhias japonesas publicam 有価証券報告書 com série
histórica, e a Investor AB publica resumo de dez anos com dividendo por ação — são
investment companies e *sogo shosha*, esse dado é institucional. É coleta em PDF,
parcialmente manual, mas com 3 ativos e ~20 anos é finita.

Combinada com o que já se tem, cobriria a janela: Avanza de 2019 em diante e IR Bank
de 2010 em diante reduzem o trabalho manual a **2006-2009** para o Japão e
**2006-2018** para a Suécia.


---

## 11. GBL resolvido — pela porta alemã, com dado belga

Último ativo sem fonte, e o que mais custou. Resolvido pelo portal alemão
**onvista**.

O detalhe que destravou: a onvista indexa o papel pelo **ISIN** e expõe todas as
praças em que ele negocia. Para o GBL isso inclui **Bruxelas, `idNotation` 29217**,
em EUR — a bolsa de origem, não a listagem secundária alemã.

Ou seja: a fonte é alemã, mas o dado é belga, na moeda certa. Não houve troca de
praça nem compromisso metodológico.

| Ativo | Pregões | Período | Saltos > 25% |
|---|---|---|---|
| GBLB | 5.118 | 2006-01-02 → 2025-12-31 | nenhum |

240 meses completos.

### A armadilha do parâmetro

`range=Y20` responde **HTTP 400**. `range=Y10` responde **200 com um mês de dados** —
ignora o parâmetro em silêncio, que é o pior dos dois casos: quem não conferir o
intervalo retornado conclui que o histórico não existe.

O que funciona é `range=Y1` **combinado com `startDate`**. Vinte requisições, uma
por ano, cobrem o estudo.

### Por que a substituição do ativo não foi necessária

Cogitou-se trocar o GBL por uma holding alemã ou francesa. A investigação mostrou
que isso **não teria resolvido nada**: a barreira não era a Bélgica, era a
**Euronext**, que cifra o histórico de qualquer papel listado nela. Wendel, Eurazeo
e Sofina são todas Euronext e teriam exatamente o mesmo problema.

E o custo metodológico teria sido real. Trocar um ativo do universo congelado por
outro mais fácil de coletar é um critério de seleção aplicado **depois** de
31/12/2005 — a regra anti-cherry-picking da seção 4 valendo contra o próprio autor.
Vale registrar que a alternativa foi considerada e descartada por método, não por
teimosia: se a coleta tivesse falhado, a saída correta seria declarar a ausência,
não substituir.


---

## 12. As três fontes internacionais são ajustadas? Medido, não assumido

Antes de caçar séries de proventos, valia responder a pergunta anterior: **essas
fontes já incluem dividendo no preço?** A suposição de que não incluem estava sendo
carregada desde a coleta, sem verificação.

O teste é direto: se a série for bruta, o preço cai na data-ex pelo valor do
provento. Se já for ajustada, não cai.

### Avanza / Investor AB — **já é total return** ✅

Cinco datas-ex conhecidas, com a série diária:

```
retorno médio na data-ex : +0,146%
retorno médio geral      : +0,087%
se a série fosse bruta   : −1,603%
```

O retorno nas datas-ex é indistinguível de um dia comum. **INVE-B não precisa de
série de proventos** — o que a Avanza entrega já é retorno total.

### onvista / GBL — **é preço bruto** ❌

Datas-ex de 2024 e 2025, com quedas de **−2,71%** e **−3,92%** exatamente no dia,
contra um yield na faixa de 4%. Inequívoco.

### Kabutan / Mitsubishi e Mitsui — provavelmente bruto ⚠️

Sem série diária longa (o Kabutan guarda ~14 meses no diário), o teste teve de ser
feito na série mensal. Proventos japoneses têm data-ex no fim de março e de
setembro, que são fronteiras de mês:

| Ticker | mar/set | demais meses | diferença | t |
|---|---|---|---|---|
| 8058 | −0,019% | +1,084% | **−1,10 p.p.** | −0,74 |
| 8031 | −0,447% | +1,317% | **−1,76 p.p.** | −1,11 |

As duas diferenças são negativas e de magnitude compatível com o provento semestral
típico de ~1,5%, mas o ruído mensal é grande demais para significância. **É
sugestivo, não conclusivo.**

Somado ao fato de a coluna de ajuste do Kabutan dizer 分割 — desdobramento — sem
mencionar dividendo, a leitura adotada é **preço bruto**, e a série de proventos
japonesa continua necessária. A premissa fica registrada como premissa.

### Um subproduto: a série de balcão americano é ruim

Tentou-se validar o Kabutan contra MITSF, o Mitsui negociado no balcão dos EUA, que
a Twelve Data entrega com `adjust=all` e portanto seria total return. O resultado
foi o oposto do esperado:

```
MITSF (suposto total return, USD):  2,37x   4,41% a.a.
Kabutan 8031 em USD              :  4,12x   7,33% a.a.
```

O preço bruto japonês **cresce quase 3 p.p. ao ano a mais** do que o suposto retorno
total americano. Isso não diz nada sobre o Kabutan — diz que a série de balcão é
inconfiável, com preços defasados, exatamente a ressalva levantada quando ela foi
descartada por não cobrir 2006-2009. Fica o registro de que ela também não serviria
como validação cruzada.


---

## 13. Proventos de GBL e Japão: não fechados

Depois do resultado da seção 12, restaram dois buracos. **Nenhum dos dois fechou**,
e vale registrar exatamente onde cada um parou.

### Japão — IR Bank entrega 4 exercícios confiáveis, não 20

A página `irbank.net/{code}/dividend` tem a coluna **分割調整**, dividendo por ação
já ajustado por desdobramento — o campo certo. Mas duas limitações a inviabilizam:

1. **Começa em 2010.** Os exercícios de 2006 a 2009 não estão na página, e o CSV de
   download (`fy-stock-dividend.csv`) traz só cinco anos.
2. **Não é uma série anual, é um log de anúncios.** Cada linha é um comunicado, com
   `区分` igual a 実績, 修正 ou 予想, e linhas referenciam mais de um exercício
   usando `rowspan` de forma irregular.

O segundo ponto rendeu a lição mais útil desta rodada. O parse ingênuo devolvia
16 exercícios e **números errados**: numa linha com `rowspan` na primeira célula, as
colunas seguintes deslizam uma posição, e o valor lido como "dividendo ajustado" era
na verdade o **dividendo semestral da coluna anterior** — metade do valor correto,
plausível, na ordem de grandeza certa, e impossível de notar num gráfico.

Foram escritas duas defesas:

- **`normalize_table`**, que expande `rowspan` e `colspan` numa grade retangular.
  Correto e testado; fica no repositório como utilitário reutilizável.
- **Uma guarda de sanidade** que descarta qualquer linha cujo `区分` não seja um dos
  três valores válidos. Linha desalinhada exibe um ano nessa coluna, e o descarte é
  obrigatório justamente porque o número resultante seria crível.

Com as duas defesas, o que resta é **4 exercícios confiáveis por empresa** —
2010 a 2013. Insuficiente.

### GBL — nenhuma fonte gratuita com a janela

| Fonte | Resultado |
|---|---|
| onvista (`cnDps`) | 6 anos |
| stockanalysis.com | 5 anos no acesso livre |
| wallstreet-online | 2021 em diante |
| ariva.de | tabela de dividendos não exposta |
| dividendmax | HTTP 404 |
| **gbl.com** | páginas `/en/dividend` e `/en/total-shareholder-return` existem e carregam, mas renderizam só anos recentes mesmo após aceitar cookies |

O achado da rodada é que **o GBL publica `/en/total-shareholder-return`**. Se essa
página tiver série longa, resolve o ativo inteiro de uma vez — não só os proventos,
mas o retorno total já calculado pela companhia. Ela não entregou os dados via
navegação automatizada, mas o **relatório anual em PDF** está aberto
(`gbl.com/en/media/.../annual_report_2025.pdf`), e investment companies publicam
série histórica de TSR nesses documentos.

### Situação dos quatro ativos internacionais

| Ativo | Preço | Proventos | Pronto? |
|---|---|---|---|
| INVE-B | ✅ | ✅ já incluídos | **sim** |
| GBLB | ✅ | ❌ | não |
| 8058 | ✅ | ❌ (4 de 20 anos) | não |
| 8031 | ✅ | ❌ (4 de 20 anos) | não |
