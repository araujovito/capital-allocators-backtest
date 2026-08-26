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
