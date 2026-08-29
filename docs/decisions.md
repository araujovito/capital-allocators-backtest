# Registro de decisões

Decisões metodológicas com data e justificativa. Append-only.

## 2026-08-26 — Universo de Capital Allocators fechado

8 empresas, 2 por região. Critério: justificável com informação existente em
31/12/2005. Bradespar aprovada **com ressalva** (historicamente concentrada em
poucas participações) — a ressalva vira material de análise: holding diversificada
× holding concentrada × ETF.

Japão escolhido deliberadamente sobre China: em 2005, o Japão era a escolha
defensável para representar um grande mercado asiático. Escolher a China hoje seria
usar conhecimento retroativo do crescimento ocorrido. As japonesas são *sogo shosha*,
não holdings puras — diferença registrada, não corrigida.

## 2026-08-26 — ETFs (Historical Reality)

PIBB11 / IVV / IEV / EWJ. Critérios: existência em 2005-2006, índice amplo, liquidez,
metodologia transparente, histórico disponível, investibilidade real à época.

- **PIBB11**: única opção real no Brasil em 2006 — BOVA11 só nasce em 2008
- **IVV** sobre SPY: SPY é UIT e não pode reinvestir dividendos internamente
- **IEV** sobre VGK: VGK (mar/2005) teria só 10 meses de histórico no início da janela

## 2026-08-26 — Regras de execução

Definidas antes do primeiro backtest: aporte R$1.000, 1º dia útil no fechamento,
reajuste IPCA anual, fracionário permitido, caixa ao CDI, rebalanceamento via aporte
anual sem venda, dividendos reinvestidos líquidos de retenção na fonte.

Ver `methodology.md` para as justificativas.

## Em aberto

- Fonte definitiva de total return para INVE-B, GBLB, 8058, 8031
- Fonte de IPCA e CDI (SGS/Bacen vs. IBGE direto)
- Tesouro IPCA+ fica para V2 (introduz duration e marcação a mercado)

## 2026-08-26 — Câmbio via Olinda/PTAX, não SGS

O SGS não expõe a coroa sueca, e Investor AB negocia em SEK. A API Olinda/PTAX
cobre USD, EUR, JPY e SEK de forma uniforme. O coletor de câmbio usa Olinda.

## 2026-08-26 — PTAX guarda compra e venda

Spread médio na janela entre 0,159% (USD) e 0,204% (SEK). Em 240 aportes
convertidos, escolher uma das pontas arbitrariamente introduz viés sistemático.
O coletor persiste as duas; a escolha é do pipeline e ainda **não foi tomada**.

## 2026-08-26 — Spike de dados: macro resolvida, renda variável bloqueada

Ver `spike-dados.md`. A barra a ser batida está quantificada: **CDI rendeu 4,46%
a.a. reais** entre 2006 e 2025.

## Em aberto (atualizado)

- **Fonte de preço e eventos societários** para as 8 ações e 4 ETFs — bloqueador
  do motor de backtest
- PTAX: usar compra, venda, ou média?
- Tesouro IPCA+ fica para V2 (introduz duration e marcação a mercado)

## 2026-08-27 — Proventos japoneses vêm do relatório anual, não do mercado

Nenhuma fonte de mercado gratuita cobre 2006-2025 para 8058 e 8031: o IR Bank
começa em 2010 e, depois das guardas contra desalinhamento, sobram quatro
exercícios por empresa. As companhias publicam a tabela de dez anos no relatório
anual, e três a quatro documentos por empresa cobrem a janela com sobreposição.

Duas consequências de método ficam registradas:

- **A sobreposição é de propósito.** Cada exercício lido em dois documentos é uma
  conferência independente do alinhamento de coluna. Onde ela não existe
  (8031 2015-2017, 8058 2011-2015), o dado é de fonte única — e isso está no
  arquivo, na coluna `fontes`.
- **O desdobramento de 2024 é medido, não assumido.** Mitsubishi 3:1 em
  01/01/2024 e Mitsui 2:1 em julho de 2024. O fator sai da razão entre documentos
  de cada lado do evento e só é aplicado se bater com o que a companhia declara em
  nota. Sem sobreposição, a coleta falha em vez de adivinhar.

## 2026-08-27 — mitsubishicorp.com recusa o Brasil; o Internet Archive serve

O site da Mitsubishi devolve 403 do Akamai para esta rede, com cabeçalho de
navegador ou sob Playwright. Não é anti-bot, é geografia — o mesmo padrão que já
tinha derrubado o Yahoo Finance. Os PDFs vêm do Internet Archive, com o snapshot
**fixado por timestamp**: sem timestamp o Archive redireciona para a captura mais
recente, e uma das capturas de 2025 está truncada em 5 MB.

## 2026-08-27 — Data-ex de Europa e Japão é convenção declarada, não inferida

Os relatórios anuais publicam o **valor** do provento, não a data-ex. No lado
brasileiro, evento societário foi recuperado por salto de preço; com dividendo
isso não funciona — o provento do GBL vale 3% a 6% do preço e a volatilidade
diária é da mesma ordem. Procurando, em cada ano, o dia de abril a junho cuja
queda mais se aproxima do dividendo, o candidato pula de 7 de abril a 26 de junho
sem padrão. **O sinal não existe**, e inferir produziria data plausível e errada.

Entra calendário declarado:

- **GBLB** — 1º de maio de N+1 para o exercício N. O relatório de 2015 diz
  *"payable as from 5 May 2016"*; o de 2025 marca a Assembleia em 7 de maio de
  2026. As duas pontas da janela apontam começo de maio.
- **8058, 8031** — metade em 30 de setembro, metade em 31 de março, as duas datas
  de registro da prática japonesa. Os relatórios publicam só o total do exercício.

O custo da convenção é **medido, não afirmado**: `sensibilidade()` refaz a série
com o dividendo inteiro na data final e a diferença em vinte anos é de +1,37%
(8058) e +1,88% (8031) acumulados — cerca de 0,08 p.p. ao ano. A convenção não
decide o resultado do estudo.

## 2026-08-27 — Duas omissões de borda ficam declaradas, não estimadas

O calendário de provento não coincide com o da janela. Falta o dividendo do GBL
pago em maio de 2006 (exercício de 2005; nenhum relatório publicado alcança) e a
parcela interina japonesa de setembro de 2025 (exercício que fecha em março de
2026, anunciada depois do último relatório). As duas empurram o resultado para
baixo — viés conservador justamente para os allocators, que é o lado que o estudo
poderia ser acusado de favorecer. Nenhuma é corrigida por estimativa.

## 2026-08-27 — A janela é recortada antes de acumular unidades

Kabutan começa em 2001 e Avanza em 2005. Acumular sobre a série inteira e recortar
depois faria o índice de janeiro de 2006 já embutir reinvestimento que o investidor
do estudo não fez, e tornaria a guarda de provento pré-série uma comparação com
2001 em vez de com janeiro de 2006. O teste que pega isso é
`test_provento_anterior_ao_inicio_da_serie_e_descartado` — é o mesmo erro que
dobrava a quantidade inicial de BRAP4.

## 2026-08-27 — O wrapper em dólar cancela, e o cancelamento é exato

IEV e EWJ replicam Europa e Japão e liquidam em dólar. A seção 5 da metodologia
manda atribuir o câmbio à moeda do mercado subjacente; a implementação faz isso
sem inventar cotação, porque a identidade se lê nas duas ordens:

    tr_brl = tr_usd × USD/BRL = (tr_brl ÷ EUR/BRL) × EUR/BRL

O retorno local em euro é **derivado** do resultado em real dividido pelo câmbio
da moeda de exposição. `validate()` confere que `local × câmbio` reproduz o
retorno em BRL em todos os doze ativos.

## 2026-08-27 — Diferença de volatilidade tem piso de materialidade

O prêmio por unidade de risco extra dividia o prêmio pela diferença de
volatilidade entre as carteiras. Nos EUA essa diferença é de **0,005 p.p.**, e a
divisão devolvia −26,6: número de aparência plausível saído de divisão por ruído.
É a mesma armadilha que o `EPS` de `metrics.py` já documenta, na escala da
volatilidade.

Abaixo de `VOL_MINIMA_PP` (0,5 p.p.) as duas carteiras correram o **mesmo** risco,
o quociente não é calculado, e o veredito diz isso em vez de fingir precisão.
Foi essa guarda que separou o Japão — prêmio de 6,46 p.p. com risco praticamente
igual — de um falso "prêmio com menos risco".

## 2026-08-27 — Robustez é medida por concentração, não por remoção de ativo

A metodologia pede o teste "remover o melhor ativo". Remover e refazer o backtest
depois de ver o resultado é escolher a carteira pelo resultado — exatamente o que
a regra anti-cherry-picking proíbe. `sem_o_melhor()` responde à mesma pergunta sem
mexer na carteira: mede quanto do patrimônio final veio do ativo de maior peso.

Maior peso 19,0% (Mitsui), HHI 0,144 contra 0,125 do equilíbrio perfeito entre
oito ativos. O resultado não depende de uma empresa excepcional.

## 2026-08-27 — Janelas de crise são datadas por terceiros

Escolher o início e o fim de uma crise depois de ver o resultado é escolher o
resultado. Nenhuma janela do módulo de crises foi datada pelo estudo: NBER para
os Estados Unidos (2007-12 a 2009-06; 2020-02 a 2020-04), CEPR para a área do
euro (3T2011 a 1T2013), CODACE/FGV para o Brasil (2T2014 a 4T2016). O aperto
monetário de 2022 não tem árbitro oficial e usa o ano-calendário inteiro, com a
ausência de árbitro declarada no campo `fonte`.

Um teste exige que toda crise declare a fonte da datação.

## 2026-08-27 — Duas escolhas que mudam o número da crise

**Retorno real, não nominal.** No recorte da recessão brasileira a inflação
acumulou 22%: uma carteira nominalmente positiva pode ter destruído poder de
compra.

**Nível de entrada no mês de véspera.** Tomar o primeiro mês de dentro da janela
como base engoliria a queda desse mês, que é justamente a que se quer medir. Na
crise financeira global a diferença é de vários pontos.

O `queda_max` é limitado a zero: quem nunca ficou abaixo do nível de entrada não
teve queda, e sem o limite o CDI reportava "+0,1% de queda".

## 2026-08-27 — "As regras não mudam na crise" virou checagem, não texto

A seção 6 da metodologia promete que as regras não mudam durante crises. A
promessa não vale como afirmação: se um arquivo de estratégia tivesse outra
janela ou outro aporte, o recorte compararia carteiras diferentes em condições
diferentes e nada denunciaria. `regras_congeladas()` confere que todos os arquivos
em `strategies/` compartilham `start`, `end`, `base_currency`, `dividends` e o
bloco de aporte — diferindo só na composição.

## 2026-08-27 — A retenção americana faltava, e o viés era contra os allocators

A seção 4 da metodologia congela 30% de retenção para papel americano e explica
por quê: ignorar retenção favoreceria artificialmente ativos de alto payout.
Brasil, Bélgica e Japão aplicavam a alíquota; os Estados Unidos, não — a série
vinha do fechamento ajustado da Twelve Data, que reinveste o dividendo **bruto**.

O viés não era simétrico, e o motivo só aparece nos dados: **Berkshire e Markel
não pagam dividendo**. Ajustado e preço puro coincidem casa a casa nos dois, com
1,000x de provento acumulado em vinte anos. Quem se beneficiava da isenção
indevida era o **lado passivo** — IVV rendeu 1,89% ao ano de dividendo, IEV 2,88%
e EWJ 1,69%, todos sem imposto.

O plano gratuito da Twelve Data não expõe `/dividends`, mas expõe o mesmo papel
com `adjust=all` (total return bruto) e `adjust=splits` (preço puro). O provento
do mês é o que sobra entre os dois, e é sobre ele que a alíquota incide. Custo
medido: 0,89 p.p. ao ano no IEV, 0,62 no IVV, 0,52 no EWJ, **zero** em BRK-B e
MKL — e esse zero é a conferência que sustenta o método.

Uma conclusão mudou de sinal. Os EUA saíram de "mesmo risco, sem prêmio"
(−0,13 p.p.) para "mesmo risco, com prêmio" (+0,49 p.p.), e o prêmio global subiu
de +2,72 para +3,26 p.p. ao ano. A correção favorece a tese do estudo, o que
obriga a registrar que a alíquota foi congelada em `methodology.md` **antes** de
qualquer resultado — não escolhida depois de ver o número.

## 2026-08-27 — Em aberto: a retenção sueca do INVE-B

Fechada a americana, resta uma assimetria na direção oposta. A série da Avanza já
é total return **bruto**, e a Investor AB não publica série de dividendo
acessível para os vinte anos: a página de histórico renderiza no cliente e volta
vazia sob Playwright, e o relatório anual traz tabela de cinco anos, o que exigiria
quatro documentos e o desdobramento 4:1 de 2021.

Pelo rendimento observado de 2020 a 2024 (1,8% a 2,6% ao ano), os 30% suecos
valem de 0,5 a 0,8 p.p. ao ano no ativo — cerca de 0,3 p.p. no prêmio europeu e
0,1 p.p. no global. Não inverte veredito nenhum, e **favorece os allocators**.
Fica declarado no README como item aberto, não corrigido por estimativa.

## 2026-08-29 — O item sueco não era retenção: era o dividendo inteiro

A entrada anterior está errada no diagnóstico, e o erro é instrutivo o bastante
para ficar registrado em vez de reescrito.

Ela dizia que a série da Avanza para INVE-B era total return **bruto** e que
faltava aplicar os 30% suecos. A primeira metade da frase vinha de um teste feito
em `avanza.py`: em cinco datas-ex conhecidas o retorno médio do papel era +0,146%,
contra +0,087% de um dia qualquer, enquanto uma série de preço cairia ~1,6%.
Parecia demonstração, e foi tratada como tal por dois dias.

Era **erro de alinhamento de um dia**. As datas usadas vinham do calendário de
assembleia; o teste comparava o fechamento do dia-ex com o do pregão *seguinte* e
mediu, portanto, o dia depois da queda.

### A refutação

A página de dividendos do site da Investor AB é um iframe do provedor de IR
(`vp053.alertir.com`), que lê um endpoint público de dados de mercado alimentado
pela Millistream. Ele devolve todos os eventos societários desde 1976, com
data-ex, valor nominal e valor ajustado por desdobramento — o 4:1 de 2021
inclusive, como dado da fonte e não premissa nossa. Foi o que faltava: não a
retenção, a **data-ex**.

Com a data verdadeira e 27 eventos em vez de 5:

| medida | valor |
|---|---|
| retorno médio no dia-ex | **−2,085%** |
| dividendo esperado, sobre o preço cum | −2,051% |
| resíduo | −0,034 p.p. |
| um dia qualquer | +0,066% (dp 1,51%) |
| t contra zero | **−5,63** |

O papel cai exatamente o dividendo. A série da Avanza é **preço puro**. Confere
também o nível: o fechamento de 2005-01-02 é 21,44 SEK pós-desdobramento, que é o
preço que a Investor B tinha — uma série com vinte anos de dividendo reinvestido
começaria bem abaixo disso.

### O que estava em jogo

INVE-B ia ao motor **sem provento nenhum** por vinte anos. O erro não valia 0,5 a
0,8 p.p. ao ano, e não corria a favor dos allocators: corria **contra**. Corrigido,
o ativo sai de 12,23% para 14,43% ao ano em SEK, o prêmio europeu de +3,40 para
+4,94 p.p. e o global de +3,26 para +3,66 p.p. Nenhum veredito regional inverte —
a dispersão entre regiões, que é a descoberta do estudo, fica mais forte, não mais
fraca.

### As duas lições, que valem mais que o número

1. **Um teste que confirma a hipótese barata merece a mesma desconfiança que um
   que a contraria.** Concluir "já é total return" dispensava coletar proventos de
   um ativo estrangeiro. O teste que autorizava essa economia foi aceito com cinco
   observações e sem checar de onde vinha a data.
2. **Classificação de série é medida, não comentário.** O veredito agora é
   recalculado toda vez que `capallo fetch-se-dividends` roda, com t-stat impresso,
   e o teste que trancava a exceção do INVE-B em `build_intl.validate()` — a única
   linha do código que sabia que aquele ativo não tinha provento — foi removido em
   favor de uma guarda que vale para os quatro ativos.

## 2026-08-29 — O Kabutan é preço puro, agora medido e não suposto

Fechado o caso sueco, sobrava a premissa simétrica e não verificada. O commit
`e07d0a4` tinha testado as três séries estrangeiras pela queda na data-ex e
registrado o resultado com honestidade: onvista **verificado** como preço puro
(quedas de 2,71% e 3,92% nas datas-ex), Avanza "verificado" como total return — o
erro corrigido hoje mais cedo — e **Kabutan inconclusivo**, com t de −0,74 e −1,11,
adotado como preço puro "registrada como premissa, não como fato".

Essa premissa passou a ser risco material. Se o Kabutan fosse total return, o
provento japonês estaria sendo **contado duas vezes** — e o Japão é a região de
maior prêmio do estudo (+6,97 p.p.). O erro seria a imagem espelhada do sueco, no
ativo onde mais custa.

### Por que o teste de data-ex não fecha, e o que fecha

O Kabutan guarda cerca de 14 meses de série diária, então o teste precisa rodar na
série mensal, onde o ruído de um mês inteiro engole um provento semestral de ~1,5%.
Aumentar a amostra não resolve: a granularidade é que está errada para a pergunta.

A saída foi trocar de pergunta. Ajuste por dividendo **se acumula para trás**: a
~3,5% ao ano, em vinte anos, o começo de uma série ajustada cai perto da metade do
preço que a ação realmente teve. Isso não é sinal a extrair de ruído — é um fator
de 2. Basta uma referência de **nível** vinda de fora, e ela estava no disco: os
relatórios anuais já coletados publicam o preço da própria ação.

| ativo | referência publicada pela companhia | pontos | razão média |
|---|---|---|---|
| 8058 | média do preço no exercício (`mc_ar2015.pdf`) | 5 | 1,009 |
| 8031 | fechamento de 31 de março na TSE (`en_ar2015_all.pdf`) | 7 | **1,000** |

O 8031 bate **ao iene**: fechamento do Kabutan em 31/03/2006 é 851, e o relatório
publica 1.702 antes do desdobramento 1:2. O resíduo do 8058 é maior porque a média
do relatório corre sobre todos os pregões e a nossa sobre doze fechamentos mensais
— diferença de método, de ordem 2%, contra os ~50% que o cenário alternativo
produziria.

O fator de desdobramento também deixa de ser premissa nossa: o mesmo relatório do
8031 traz 24 JPY de provento no exercício de 2006, e `jp_dividends` traz 12.

### O que fica

`capallo check-jp-prices` roda a conferência e emite veredito; a referência está em
`data/manual/jp_reported_prices.csv`, transcrita dos PDFs com fonte por linha, no
mesmo padrão dos outros arquivos de `data/manual`. Nenhum número do estudo muda —
a premissa estava certa. O que mudou é que ela deixou de ser premissa.

Vale registrar o padrão, porque foi ele que resolveu os dois casos do dia: quando o
teste natural não tem poder, **procurar a evidência de nível em vez de a de evento**.
A data-ex é um sinal de um dia competindo com ruído de um dia; o nível acumula vinte
anos de diferença contra ruído nenhum.

## 2026-08-29 — Janelas de início: o prêmio global sobrevive, o americano não

A §9 previa "múltiplas datas de início — 2006→2025, 2007→2025, … 2015→2025" desde
antes de existir motor. Rodado agora, com o fim sempre em dez/2025: o que varia é
quanto de história entra, não quanto sai.

O resultado tem duas metades, em direções opostas, e as duas importam.

**O prêmio global sobrevive às dez janelas**, entre +3,08 e +7,46 p.p. ao ano.
Mais que isso: 2006, o início que o estudo escolheu antes de ver qualquer número,
é a **terceira pior** das dez. A escolha de janela não infla o resultado do estudo
— deflaciona. Europa é a região mais estável, entre +4,13 e +5,85, sem uma janela
negativa. Brasil e Japão sobem forte com entradas tardias (+8,32 e +11,82 em 2015),
o que é informação sobre 2015-2025 e não sobre gestão ativa.

**A vantagem americana some.** O +0,49 p.p. do placar principal é a **única janela
positiva das dez**; de 2007 a 2015, todo início entrega prêmio negativo nos EUA.
O veredito "mesmo risco, com prêmio" era artefato do ponto de partida.

Isso obriga a corrigir o README, e a correção **não** enfraquece a conclusão
central: a dispersão entre regiões é maior do que o placar de 2006 sugeria. Vale
registrar que a regra anti-cherry-picking funciona nos dois sentidos — ela impediu
remover um ativo ruim, e aqui impede manter um veredito bom que só existe numa
data de entrada.

## 2026-08-29 — A ponta da PTAX não decide nada, e o resíduo prova por quê

A §5 converte tudo pela PTAX de **venda**. O spread pareceria cancelar no retorno,
já que todos os níveis usam a mesma ponta — mas só cancelaria se fosse constante,
e não é: o spread médio do dólar era **0,46% em 2006** e é **0,011% desde 2020**.
Um spread que encolhe deixa resíduo, com sinal conhecido: converter pela venda
infla o nível inicial mais que o final, subestimando o retorno de todo ativo
estrangeiro.

Refeito o estudo inteiro com cada ponta, o efeito máximo no prêmio é de **0,028
p.p. ao ano** (Europa), 0,011 no global. Não move veredito nenhum.

O que vale mais que a magnitude é **onde** o resíduo aparece, porque isso testa o
mecanismo em vez de só reportar um número:

- **Brasil: exatamente zero.** Não há câmbio.
- **EUA: exatamente zero.** As duas pernas liquidam em USD, e o spread cancela
  entre allocator e ETF, não dentro de cada um.
- **Europa e Japão: diferente de zero.** É onde o ETF liquida em dólar e o
  allocator não — as duas pernas usam moedas diferentes, e aí o spread sobra.

Um número pequeno pelo motivo errado seria robustez aparente. Este é pequeno pelo
motivo certo.

## 2026-08-29 — A data do aporte não roda, e a limitação é de dado

A §2 congela o aporte no **1º dia útil do mês, no fechamento**, e o experimento
natural é mover esse dia. Ele **não pode ser executado** com o dado que existe.

O bloqueio é o Japão: a série do Kabutan é mensal. O site publica cerca de catorze
meses de pregão a pregão e nada além, e as três rodadas de busca de
`docs/spike-dados.md` não acharam fonte diária japonesa gratuita com vinte anos.
Sem preço diário de 8058 e 8031, mover o aporte para os outros dez ativos
compararia estratégias com regras diferentes — exatamente o que `regras_congeladas()`
existe para impedir.

Fica declarado como limitação de dado, não como experimento omitido. A diferença
importa: a primeira é honesta sobre o alcance do estudo, a segunda seria silêncio
sobre um resultado que não se quis ver.

## 2026-08-29 — Index Benchmark: o prêmio global sobrevive, o americano era o produto

Segundo dos três tipos de experimento da §7, rodado com o **índice** no lugar do
ETF. Ele existe porque o placar principal responde "a gestão ativa venceu o
produto que dava para comprar em 2006", que é a pergunta certa para um investidor
e **não** é a pergunta "a gestão ativa venceu o mercado". Esta é.

| Região | Prêmio vs ETF | vs índice | Custo do produto |
|---|---|---|---|
| Brasil | +2,26 | **+2,57** | **−0,31** |
| EUA | +0,49 | **−0,01** | +0,50 |
| Europa | +4,94 | +3,83 | +1,11 |
| Japão | +6,97 | +6,01 | +0,96 |
| **Global** | **+3,66** | **+3,08** | **+0,58** |

O prêmio global cai de +3,66 para +3,08 p.p. ao ano: cerca de um sexto dele era
custo de embrulhar o mercado num fundo. **Nos EUA o prêmio inteiro era o produto**
— contra o índice ele é zero. Junto com as janelas de início, em que os EUA são
positivos em 1 de 10, o veredito americano cai por dois testes independentes.

No Brasil o experimento anda para o **outro lado**: o PIBB11 superou o IBrX-50 em
0,31 p.p. ao ano, então trocar produto por índice aumenta o prêmio. Vale registrar
porque é a evidência de que o experimento não está viciado a favor da tese — e
também que o estudo **não tem dado para explicar por quê**: aluguel de ações e
convenção de reinvestimento do índice são hipóteses não testadas.

### Metade dos índices é substituta, e a troca é medida

A S&P Dow Jones responde 403 a qualquer requisição de nível de índice, com
navegador ou sem. A MSCI publica de graça, mensal, desde os anos 1970, nas três
variantes. Então IBrX-50 (do PIBB11) e MSCI Japan (do EWJ) são os índices exatos,
e MSCI USA e MSCI Europe entram no lugar de S&P 500 e S&P Europe 350.

O tamanho da troca não fica no texto, fica em número: comparando cada índice com o
total return bruto do próprio ETF, +0,05 p.p. ao ano no IVV — imaterial —, +0,87
no IEV, que mistura custo de produto com diferença de índice sem que esta fonte
separe as parcelas. Onde o índice é o do próprio ETF a diferença é só produto:
+0,68 p.p. no EWJ, contra taxa declarada de 0,50%. Os números batem com as taxas
reais, o que é a melhor confirmação disponível de que a comparação está medindo o
que diz medir.

### `NETR` existia pronta e foi recusada

A MSCI publica a variante líquida. Ela já vem com retenção — mas com **as
alíquotas que a MSCI assume**, não os 30% que a §4 congelou para o investidor
brasileiro antes de qualquer resultado. Usar `NETR` faria a perna do índice ser
tributada diferente da perna do ETF, e a comparação passaria a medir regime fiscal
em vez de custo de produto. Entra `GRTR` com a retenção aplicada por fora, pelo
mesmo método de `transform.us_net` — o provento do mês é o que sobra entre o bruto
e o preço puro.

### O susto do PIBB11

Ao classificar a série brasileira apareceu que `b3_cash_dividends` não tem
**nenhum** provento do PIBB11 em vinte anos e que as unidades dele nunca crescem —
a assinatura exata do erro do INVE-B, encontrada no mesmo dia.

Um teste de ordenação respondeu às duas dúvidas de uma vez: PIBB11 só preço 8,42%,
PIBB11 total return do pipeline 8,42%, IBrX-50 publicado 8,09%. Índice só de preço
ficaria pontos **abaixo** do total return do ETF; provento perdido do ETF o
deixaria pontos abaixo do índice. Os três colados só são compatíveis com índice de
retorno total e fundo que reinveste internamente, que é característica declarada
do PIBB11. As duas premissas estavam certas — e o susto valeu por transformá-las
em medida.

Uma armadilha de alinhamento apareceu aqui e vale registro: a primeira rodada
comparou o índice a partir de 31/12/2005 com o ETF a partir de 02/01/2006 e
produziu diferenças que embutiam **um mês inteiro de bolsa** — maior que o custo
anual de qualquer ETF. Toda comparação do módulo passa agora por uma grade mensal
comum, e a base é a mesma para as duas séries.

## 2026-08-29 — Modern Alternative: o benchmark mais duro, e o allocator ainda vence

Terceiro e último tipo de experimento da §7. O contrafactual é um fundo global de
índice — MSCI ACWI, o mundo ponderado por capitalização num ticker só, em reais,
sem conta no exterior. Em 2006 o investidor brasileiro não tinha isso; hoje é a
recomendação padrão.

### Por que é o benchmark mais duro do estudo

A perna passiva do placar principal tem quatro ETFs em **pesos iguais**, espelhando
a construção da perna ativa — oito empresas, duas por região. É uma comparação
justa, e é uma comparação que **subponderou os Estados Unidos exatamente no período
em que os Estados Unidos ganharam de todo mundo**. O ACWI carrega o peso de mercado
de cada região a cada data e por isso rende 6,56% ao ano real contra 5,21% dos ETFs
de 2006 e 5,79% dos índices regionais.

Contra ele, a carteira ativa entrega **+2,31 p.p. ao ano, com 2,13 p.p. menos de
volatilidade e drawdown máximo 8,3 p.p. mais raso** — vitórias em 55% / 61% / 67% /
62% das janelas de 1, 3, 5 e 10 anos.

Não é dominância confortável, e o número que mostra isso é o pior caso relativo:
entre 180 janelas de cinco anos, a que começa em set/2015 custa **−7,6 p.p. ao ano**
contra o ACWI. Cinco anos de arrependimento é tempo suficiente para a maioria das
pessoas abandonar a estratégia — e quem abandona não colhe os vinte anos.

### O anacronismo está no acesso, não na regra do índice

Vale separar duas coisas que se confundem num contrafactual. Os pesos do ACWI em
2006 são os de 2006: **não há lookahead na regra do índice**. E escolher "global
ponderado por capitalização" como o padrão moderno também não é hindsight — era
recomendação de manual em 2006. Ao investidor brasileiro faltava o **veículo**, e é
isso que o experimento torna disponível.

O que é escolha nossa é a taxa de administração, e ela ficou em 0,30% ao ano: a
ponta cara da faixa dos produtos globais acessíveis hoje. A ponta barata
favoreceria o lado contra o qual a tese está sendo testada, e não é assim que se
testa uma tese. Medida em três níveis, a taxa move o prêmio entre +2,05 e +2,52
p.p. — não decide veredito.

### Um sumiço silencioso, achado por acaso

Ao entrar no painel, o ACWI simplesmente **não chegou ao motor**. A causa: o mapa
`CURRENCY` de `transform.dataset` não tinha o ticker, o `map` devolveu NaN, e o
`groupby` por moeda descarta NaN sem avisar. O erro só apareceu adiante, como
"sem preço para ACWI em 2006-01" — mensagem que aponta para o motor quando o
problema estava três passos antes.

Ficou uma guarda que transforma o sumiço em erro no lugar certo. Vale a
generalização: **`groupby` silencioso sobre chave derivada é um lugar onde dado
some sem deixar rastro**, e o pipeline já tinha uma coluna derivada por `map` em
cada camada.

### O estudo respondeu às três perguntas que se propôs

- **Historical Reality** — venceu o produto que dava para comprar em 2006: +3,66 p.p.
- **Index Benchmark** — venceu o mercado: +3,08 p.p., exceto nos EUA, onde o prêmio
  inteiro era o produto.
- **Modern Alternative** — venceria o produto de hoje: +2,31 p.p., com menos risco.

Os três números caem nessa ordem, e a ordem é informativa: cada experimento
sucessivo remove uma vantagem do lado ativo, e o que sobra depois dos três é o que
o estudo pode chamar de gestão de capital.

## 2026-08-29 — Tesouro IPCA+: retorno alto, resultado ruim, e a razão é sequência

Último item herdado do começo do projeto. Ficou para "V2" com o motivo escrito em
26/08/2026: *"introduz duration e marcação a mercado"*. Era exatamente o problema —
e o problema virou o achado.

Entra como **régua ao lado do CDI**, não como ativo das carteiras: o CDI pergunta
se o risco da bolsa compensou contra o juro nominal, e esta perna pergunta a versão
dura, contra um retorno real contratado. Estava declarada como pendente antes de
existir motor e antes de qualquer número, então não é acréscimo pós-resultado ao
universo congelado — e o título já era comprável em 31/12/2005 de todo modo.

### O resultado

**6,85% ao ano real, e 1,41 real de poder de compra por real aportado — menos que
o CDI**, que rendeu 4,43%. Os dois números não se contradizem: o primeiro é
ponderado por tempo, o segundo por dinheiro, e a distância entre eles é a
sequência.

| período | Tesouro IPCA+ | CDI | Capital Allocators |
|---|---|---|---|
| 2006-2012 | **+20,1%** a.a. | +5,8% | −0,5% |
| 2013-2018 | +1,6% | +4,2% | +13,8% |
| 2019-2025 | **−0,6%** | +3,4% | +14,6% |

O título longo brilhou quando o investidor quase não tinha dinheiro aplicado e
afundou quando já tinha quase tudo. Quem acumula não recebe o retorno médio do
ativo; recebe o retorno dos anos em que o patrimônio dele era grande.

### A ressalva que isso cria contra o número principal do estudo

Os Capital Allocators são a **imagem espelhada**: fracos em 2006-2012, fortes
depois. O placar de 3,75x se beneficiou de uma sequência favorável na mesma medida
em que o do título sofreu de uma desfavorável. Não é acusação de sorte — é
definição de carteira com aporte mensal. O teste de janelas de início já apontava
para o mesmo lugar (prêmio cresce com entradas tardias); aqui aparece o mecanismo,
e ele passa a constar do README como ressalva ao lado do placar.

Vale registrar como pauta: um *bootstrap* de blocos, embaralhando a ordem dos
retornos e mantendo a distribuição, diria quanto do prêmio sobrevive a uma sequência
diferente da que a história sorteou. É o teste adversarial natural daqui em diante.

### As decisões que a perna obrigou

**Zero-cupom, não o primo com juros semestrais.** O total return vira variação de
preço unitário e ponto; o outro exigiria uma convenção de reinvestimento nova a
cada seis meses por vinte anos — a mesma família de problema que a data-ex criou no
lado internacional, e desta vez evitável.

**Duas regras de rolagem, as duas reportadas.** `mais_longo` (principal, 3
rolagens, 12,76% a.a. nominal) contra `ate_o_vencimento` (1 rolagem, 13,85%). A
principal descreve o mandato: quem acumula por vinte anos não deixa a carteira
encurtar sozinha — sob a outra regra, em 2023 o aporte compraria um título de um
ano, caixa disfarçado de renda fixa longa. A escolha custa 1,09 p.p. ao ano, e o
número fica declarado.

**Spread de rolagem entra, IR não, e a linha entre os dois é principiada.** Spread
é preço, e o estudo modela preço em todas as pernas; além disso é intrínseco — uma
ação nunca é obrigada a transacionar, um título que vence é. IR não entra porque a
§4 congelou só retenção sobre dividendo, o CDI entra bruto e as carteiras de ação
rebalanceiam por aporte para não realizar ganho. Mas o que a regra ignora é
medido: 1,46 p.p. ao ano, grande porque o ganho nominal de vinte anos de IPCA+
embute toda a inflação do período.

### Mais uma coluna que muda de significado no meio da série

A leitura inicial tomou `PU Base` como preço de marcação, porque nas linhas
recentes ele é idêntico ao `PU Venda`. A guarda de coerência reprovou: coincide em
30% da amostra e diverge em 70%, ficando ~0,04% abaixo até 2021 e igual de 2022 em
diante. É a terceira vez no projeto que uma classificação feita pelas últimas
linhas da série se revela errada — depois da Avanza e do Kabutan. A regra que fica:
**classificar coluna olhando a amostra inteira, nunca a cauda dela.**

E um pregão único (01/07/2010, vencimento 2015) traz spread negativo, que não
existe. É descartado na coleta com o motivo escrito, sob uma guarda que falha se
deixar de ser caso isolado.

## 2026-08-29 — Bootstrap: a sequência move o placar, mas não pode mover o prêmio

Primeiro teste puramente adversarial do projeto, e ele obrigou a separar duas
perguntas que a ressalva do Tesouro IPCA+ deixou embaralhadas.

### O que é aritmética e o que é empírico

O retorno anualizado é a média geométrica dos retornos mensais, e média geométrica
**não depende da ordem**. Logo, reordenar os meses não pode mover o prêmio em
pontos ao ano — não aproximadamente, e sim identicamente. Isso não é resultado do
bootstrap; é aritmética, e o bootstrap serve para conferir que o código a respeita.
Confere: desvio máximo de 2·10⁻¹⁴ p.p. em 4.000 reordenações.

O múltiplo por real aportado, esse sim, é ponderado por dinheiro, e é onde a
sequência aparece.

### O placar teve sorte; a comparação, não

O múltiplo dos allocators sob reordenação tem mediana 2,67x, p5 2,04x e p95 3,67x.
O que aconteceu — 3,76x — está no **percentil 96**. A sequência ajudou muito, e a
ressalva levantada pelo Tesouro IPCA+ está confirmada e quantificada.

**Mas a razão entre os múltiplos não se move**: mediana 1,509 contra 1,506
observado. A sequência favorável levantou as duas pernas igualmente — o ETF também
foi comprado barato cedo e valorizado tarde. A sorte está no número absoluto, não
na comparação, e o estudo passa a dizer as duas coisas em vez de uma.

### O prêmio contra a incerteza de amostra

Reamostragem com reposição, blocos de 12 meses, 4.000 histórias: prêmio médio
+3,62 p.p., desvio 1,66, p5 +0,92, p95 +6,36, **positivo em 98,8%**. O tamanho do
bloco não decide — de 3 a 24 meses a fração positiva vai de 95,3% a 99,3%, e bloco
curto é a escolha mais adversarial porque destrói a memória da série.

Positivo não é grande: no percentil 5 vale +0,92 p.p. ao ano. Suficiente para o
veredito sobreviver, insuficiente para ele ser confortável — e é assim que fica
escrito.

### A guarda que faz o teste valer

**Todas as pernas reamostradas com os mesmos índices.** Se cada estratégia
sorteasse os próprios meses, a correlação entre elas iria embora, os allocators de
um mês bom encontrariam o ETF de um mês ruim, e a distribuição do prêmio ficaria
larga por artefato — dando aparência de rigor a ruído. O bootstrap é do
**calendário**, não das séries.

### Um bug pego pela própria checagem

A primeira versão do embaralhamento usava blocos circulares de tamanho fixo. Como
239 não é múltiplo de 12, o corte final duplicava meses e descartava outros: não
era permutação. O prêmio, que tem de ser idêntico sob reordenação, saía 0,38 p.p.
diferente — e foi `conferir_invariancia()` que acusou. Vale o registro de método:
**quando existe uma invariante analítica, ela é o melhor teste disponível**, porque
falha por bug e nunca por ruído. A versão correta particiona a janela em blocos
contíguos e sorteia só a ordem deles.

### O que este teste não alcança

Ele reamostra a história dos oito ativos **que foram escolhidos**. Não diz nada
sobre a escolha em si — e a escolha foi feita por alguém que já sabia quais
holdings de 2005 ainda existiriam em 2025. É a limitação de fundo do estudo, e
passa a estar escrita no README como o ataque que sobra: só um universo montado por
critério mecânico sobre todas as holdings listadas em 2005, mortas inclusive,
separaria o prêmio da gestão do prêmio de ter sobrevivido.
