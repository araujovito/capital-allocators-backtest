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
