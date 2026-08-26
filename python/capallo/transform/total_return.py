"""Total return dos ativos brasileiros.

Reconstrói a série de retorno total a partir de preço bruto do COTAHIST mais
eventos, seguindo as regras congeladas em `docs/methodology.md`:

- dividendos e JCP reinvestidos **no próprio ativo pagador**, na data-ex,
  **líquidos de imposto na fonte** (JCP 15%, dividendo isento);
- bonificações, desdobramentos e grupamentos aplicados como variação da
  quantidade de ações detidas;
- provento em espécie (a distribuição de ações da Vale pela Bradespar em 2021)
  valorado pela cotação do ativo distribuído na data-ex e tratado como caixa
  reinvestido no pagador.

O modelo é de **unidades acumuladas**: parte-se de 1 ação e acompanha-se quantas
ações o investidor passa a ter. O índice de total return é `unidades × preço`.
Essa formulação torna cada evento explícito e auditável, ao contrário de um fator
de ajuste retroativo aplicado ao preço.

⚠️ Semântica da B3: o campo `lastDatePrior` é o **último pregão com direito**, não
a data-ex. A data-ex é o pregão seguinte. Verificado na bonificação de 12,95% da
BRAP4, cujo efeito no preço aparece em 21/09/2021, e não em 20/09 como o campo
sugere.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

#: Retenção na fonte por tipo de provento, na ótica do investidor pessoa física.
WITHHOLDING = {
    "JRS CAP PROPRIO": 0.15,  # JCP: 15% retidos na fonte
    "DIVIDENDO": 0.00,        # dividendo: isento
}

#: Eventos que multiplicam a quantidade de ações. `factor_pct` vem em percentual.
UNIT_EVENTS = {"BONIFICACAO", "DESDOBRAMENTO", "GRUPAMENTO"}


def next_session(day: pd.Timestamp, sessions: pd.DatetimeIndex) -> pd.Timestamp | None:
    """Primeiro pregão estritamente posterior a `day`, dentro da série.

    Devolve ``None`` para datas **anteriores ao início da série**. Sem essa guarda,
    um evento de 2005 seria aplicado no primeiro pregão de 2006: o investidor do
    estudo não detinha a ação em 2005 e não recebeu aquele desdobramento. O bug
    dobrava a quantidade inicial de BRAP4.
    """
    if not len(sessions) or day < sessions[0]:
        return None
    later = sessions[sessions > day]
    return later[0] if len(later) else None


def build_series(
    ticker: str,
    prices: pd.DataFrame,
    cash: pd.DataFrame,
    stock: pd.DataFrame,
    in_kind: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Série diária de unidades acumuladas e índice de total return."""
    px = prices[prices.ticker == ticker].sort_values("date").reset_index(drop=True)
    if px.empty:
        raise ValueError(f"sem preços para {ticker}")
    sessions = pd.DatetimeIndex(px.date)
    price_of = dict(zip(px.date, px.close))

    # A série de preço é da classe PN; só proventos dessa classe contam.
    # astype(str) protege o caso sem proventos, em que a coluna vem sem dtype de texto.
    div = cash[
        (cash.ticker == ticker)
        & cash.stock_type.astype(str).str.contains("PN", na=False)
    ].copy()
    div["ex"] = [next_session(d, sessions) for d in div.ex_date]
    div = div.dropna(subset=["ex"])

    ev = stock[stock.ticker == ticker].copy()
    ev = ev[ev.kind.isin(UNIT_EVENTS)]
    # A B3 publica cada evento duas vezes, uma por classe (ON e PN), com o mesmo
    # fator. Aplicar as duas dobrava todo desdobramento e toda bonificação.
    ev = ev.drop_duplicates(subset=["ex_date", "kind", "factor_pct"])
    ev["ex"] = [next_session(d, sessions) for d in ev.ex_date]
    ev = ev.dropna(subset=["ex"])

    kind_by_day: dict[pd.Timestamp, float] = {}
    if in_kind is not None and not in_kind.empty:
        k = in_kind[in_kind.ticker == ticker]
        for _, r in k.iterrows():
            ex = next_session(pd.Timestamp(r.ex_date), sessions)
            if ex is not None:
                kind_by_day[ex] = kind_by_day.get(ex, 0.0) + float(r.value_per_share)

    units_add = div.groupby("ex").apply(
        lambda g: sum(v * (1 - WITHHOLDING.get(k, 0.0)) for v, k in zip(g.value, g.kind)),
        include_groups=False,
    ).to_dict()
    unit_mult = ev.groupby("ex").apply(
        lambda g: float((1 + g.factor_pct / 100).prod()), include_groups=False
    ).to_dict()

    units, rows = 1.0, []
    for day in px.date:
        price = price_of[day]
        if day in unit_mult:
            units *= unit_mult[day]
        payout = units_add.get(day, 0.0) + kind_by_day.get(day, 0.0)
        if payout and price > 0:
            units += units * payout / price
        rows.append({"date": day, "ticker": ticker, "price": price,
                     "units": units, "tr_index": units * price})
    return pd.DataFrame(rows)
