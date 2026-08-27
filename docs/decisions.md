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
