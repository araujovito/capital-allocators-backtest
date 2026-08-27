"""Total return de Europa e Japão, a partir de preço e provento já coletados.

Fecha os quatro ativos que faltavam. O modelo é o mesmo do lado brasileiro —
unidades acumuladas, cada evento explícito, `tr_index = unidades × preço` — mas o
insumo é diferente e o código é separado de propósito: aqui não há desdobramento
a aplicar (as séries de Kabutan, onvista e Avanza já vêm ajustadas) nem provento
em espécie, e há um problema que o Brasil não tinha — **a data-ex não foi
coletada, só o valor anual**.

## Por que a data-ex não é inferida do preço

No lado brasileiro, desdobramento foi recuperado por salto de preço: um evento de
100% não se confunde com mercado. Dividendo não tem essa sorte. O provento do GBL
vale 3% a 6% do preço, e a volatilidade diária da ação é da mesma ordem — ao
procurar, em cada ano, o dia de abril a junho cuja queda mais se aproxima do
dividendo, o candidato pula de 7 de abril a 26 de junho sem padrão. **O sinal não
existe.** Inferir aqui seria produzir uma data plausível e errada, que é o modo
de falha que este projeto persegue desde a coleta japonesa.

## A convenção usada, e o que ela custa

Na falta da data, entra calendário declarado, não chute:

- **GBLB** — o dividendo do exercício N é aprovado pela Assembleia Ordinária de
  maio de N+1 e pago logo em seguida. O relatório de 2015 diz do dividendo do
  exercício de 2015: *"payable as from 5 May 2016"*; o de 2025 marca a Assembleia
  em 7 de maio de 2026. As duas pontas da janela apontam o mesmo começo de maio,
  e é ele que o coletor usa.
- **8058, 8031** — no Japão o exercício fecha em 31 de março e o dividendo anual
  se divide em duas parcelas com datas de registro fixas por prática de mercado:
  a interina em 30 de setembro e a final em 31 de março. Os relatórios publicam
  só o total do exercício, então ele entra **metade em cada data**. A série de
  preço japonesa é mensal, de forma que o que a convenção decide é o mês, não o
  dia.
- **INVE-B** — a série da Avanza já é total return; entra com uma unidade e sem
  provento, para o arquivo ficar uniforme.

A convenção move a data de reinvestimento, não o valor. `sensibilidade()` mede o
que isso custa: refaz a série com todo o provento japonês na data final e compara
o retorno acumulado de vinte anos.

## Duas omissões na borda da janela, declaradas

O calendário de provento não coincide com o da janela, e nas duas pontas sobra um
pagamento que o investidor do estudo teria recebido e que o dado não cobre:

- **GBLB, maio de 2006.** É o dividendo do exercício de 2005, e a coleta começa em
  2006 — a tabela de dez anos do relatório de 2015 não alcança 2005, e não há
  relatório anterior publicado nem no site nem no Internet Archive. Ordem de
  grandeza do que falta: o exercício seguinte pagou 1,90 EUR sobre uma ação de
  83 EUR, **cerca de 2,3% da posição, uma vez em vinte anos**.
- **8058 e 8031, setembro de 2025.** É a parcela interina do exercício que fecha
  em março de 2026, anunciada depois do último relatório coletado. Vale cerca de
  metade do dividendo anual, **na ordem de 1% do preço**.

As duas empurram o resultado para baixo, não para cima — o viés é conservador
justamente para os allocators, que é o lado que o estudo poderia ser acusado de
favorecer. Nenhuma é corrigida por estimativa: o número que falta é o número que
falta.

⚠️ Proventos entram **líquidos de retenção na fonte**, com as alíquotas
congeladas em `docs/methodology.md`: Bélgica 30%, Japão 15%.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from capallo.universe import BY_TICKER

#: Primeiro e último mês da janela do estudo.
START, END = pd.Timestamp("2006-01-01"), pd.Timestamp("2025-12-31")

#: Repartição do dividendo anual japonês entre as duas datas de registro.
#: A interina pertence ao ano-calendário anterior ao fim do exercício.
JP_PARCELAS = ((-1, 9, 0.5), (0, 3, 0.5))


def payouts_gbl(dividends: pd.DataFrame) -> pd.DataFrame:
    """Dividendo do exercício N com data-ex em 1º de maio de N+1."""
    d = dividends[dividends.ticker == "GBLB"]
    return pd.DataFrame({
        "ticker": "GBLB",
        "ex_date": [pd.Timestamp(year=int(y) + 1, month=5, day=1) for y in d.fiscal_year],
        "value": d.gross_dividend.astype(float).to_numpy(),
    })


def payouts_jp(dividends: pd.DataFrame) -> pd.DataFrame:
    """Dividendo do exercício encerrado em março, metade em cada data de registro."""
    linhas = []
    for _, r in dividends.iterrows():
        for desloc, mes, peso in JP_PARCELAS:
            ano = int(r.fiscal_year) + desloc
            linhas.append({
                "ticker": r.ticker,
                "ex_date": pd.Timestamp(year=ano, month=mes, day=1) + pd.offsets.MonthEnd(0),
                "value": float(r.dps_jpy) * peso,
            })
    return pd.DataFrame(linhas)


def accumulate(
    ticker: str, prices: pd.DataFrame, payouts: pd.DataFrame, withholding: float
) -> pd.DataFrame:
    """Unidades acumuladas com reinvestimento do provento líquido no próprio ativo.

    Cada provento é encaixado na **primeira observação de preço em ou depois** da
    data-ex nominal. Isso resolve os dois calendários de uma vez: no GBL diário,
    1º de maio cai no pregão seguinte quando é feriado; no Japão mensal, 30 de
    setembro cai na observação daquele mês. Provento anterior ao início da série é
    descartado — o investidor do estudo não detinha a ação.
    """
    px = (prices[prices.ticker == ticker]
          .sort_values("date").drop_duplicates("date").reset_index(drop=True))
    if px.empty:
        raise ValueError(f"sem preços para {ticker}")
    datas = pd.DatetimeIndex(px.date)

    liquido: dict[pd.Timestamp, float] = {}
    for _, r in payouts[payouts.ticker == ticker].iterrows():
        # Provento com data-ex anterior à série não é do investidor do estudo, que
        # só passa a deter a ação na primeira observação. Sem esta guarda ele seria
        # empurrado para o primeiro dia — o mesmo erro que dobrava a BRAP4.
        if r.ex_date < datas[0]:
            continue
        pos = datas.searchsorted(r.ex_date, side="left")
        if pos >= len(datas):
            continue
        dia = datas[pos]
        liquido[dia] = liquido.get(dia, 0.0) + float(r.value) * (1 - withholding)

    units, rows = 1.0, []
    for dia, preco in zip(px.date, px.close):
        pago = liquido.get(dia, 0.0)
        if pago and preco > 0:
            units += units * pago / preco
        rows.append({"date": dia, "ticker": ticker, "price": float(preco),
                     "units": units, "tr_index": units * float(preco)})
    return pd.DataFrame(rows)


def build(out_dir: Path) -> pd.DataFrame:
    be_px = pd.read_parquet(out_dir / "be_prices.parquet")
    jp_px = pd.read_parquet(out_dir / "jp_prices.parquet")
    se_px = pd.read_parquet(out_dir / "se_prices.parquet")[["date", "ticker", "close"]]

    payouts = pd.concat([
        payouts_gbl(pd.read_parquet(out_dir / "be_dividends.parquet")),
        payouts_jp(pd.read_parquet(out_dir / "jp_dividends.parquet")),
    ], ignore_index=True)

    frames = []
    for ticker, px in (("GBLB", be_px), ("8058", jp_px), ("8031", jp_px), ("INVE-B", se_px)):
        wt = BY_TICKER[ticker].withholding_tax
        # A série sueca já é total return: aplicar provento de novo contaria duas vezes.
        p = payouts if ticker != "INVE-B" else payouts.head(0)
        # A janela é recortada **antes** de acumular. Kabutan começa em 2001 e
        # Avanza em 2005: acumular fora da janela faria o índice de 2006 já embutir
        # reinvestimento que o investidor do estudo não fez, e tornaria a guarda de
        # provento pré-série uma comparação com 2001 em vez de com janeiro de 2006.
        janela = px[(px.date >= START) & (px.date <= END)]
        frames.append(accumulate(ticker, janela, p, wt))

    df = pd.concat(frames, ignore_index=True).reset_index(drop=True)
    df.to_parquet(out_dir / "intl_total_return.parquet", index=False)
    return df


def sensibilidade(out_dir: Path) -> pd.DataFrame:
    """Quanto a convenção de data-ex japonesa custa em vinte anos.

    Compara a repartição em duas parcelas com a alternativa de lançar o dividendo
    inteiro na data final do exercício. Se a diferença for pequena, a convenção
    não decide o resultado do estudo — e é isso que precisa ficar demonstrado, não
    afirmado.
    """
    jp_px = pd.read_parquet(out_dir / "jp_prices.parquet")
    div = pd.read_parquet(out_dir / "jp_dividends.parquet")
    wt = BY_TICKER["8058"].withholding_tax

    inteiro = div.copy()
    inteiro["ex_date"] = [pd.Timestamp(year=int(y), month=3, day=1) + pd.offsets.MonthEnd(0)
                          for y in inteiro.fiscal_year]
    inteiro = inteiro.rename(columns={"dps_jpy": "value"})[["ticker", "ex_date", "value"]]

    linhas = []
    for ticker in ("8058", "8031"):
        a = accumulate(ticker, jp_px, payouts_jp(div), wt)
        b = accumulate(ticker, jp_px, inteiro, wt)
        a, b = (x[(x.date >= START) & (x.date <= END)] for x in (a, b))
        linhas.append({
            "ticker": ticker,
            "duas_parcelas": a.tr_index.iloc[-1] / a.tr_index.iloc[0],
            "parcela_unica": b.tr_index.iloc[-1] / b.tr_index.iloc[0],
        })
    out = pd.DataFrame(linhas)
    out["diferenca_pp"] = (out.duas_parcelas / out.parcela_unica - 1) * 100
    return out


def validate(out_dir: Path, threshold: float = 0.35) -> list[str]:
    """O índice não pode ter salto artificial nem deixar de crescer com provento.

    O limiar é mais frouxo que o brasileiro porque a série japonesa é mensal: um
    mês de 2008 cabe inteiro em uma observação.
    """
    path = out_dir / "intl_total_return.parquet"
    if not path.exists():
        return [f"{path} não existe"]
    df = pd.read_parquet(path)

    problemas = []
    for ticker, g in df.groupby("ticker"):
        g = g.sort_values("date")
        if g.date.iloc[0] > pd.Timestamp("2006-02-28"):
            problemas.append(f"{ticker}: série começa em {g.date.iloc[0].date()}")
        if g.date.iloc[-1] < pd.Timestamp("2025-11-30"):
            problemas.append(f"{ticker}: série termina em {g.date.iloc[-1].date()}")
        if (g.units.diff().dropna() < -1e-12).any():
            problemas.append(f"{ticker}: unidades diminuíram — só evento de grupamento faria isso")
        # O provento reinvestido tem de aparecer: sem ele, units fica em 1 o tempo todo.
        if ticker != "INVE-B" and g.units.iloc[-1] <= 1.0:
            problemas.append(f"{ticker}: nenhum provento reinvestido")
    return problemas
