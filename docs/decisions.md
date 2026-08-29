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
