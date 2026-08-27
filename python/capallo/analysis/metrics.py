"""Métricas de risco e retorno.

Todas operam sobre a série mensal de patrimônio produzida pelo motor. Nenhuma
depende de moeda: a decomposição cambial é assunto separado e só faz sentido com
SEK, JPY e EUR na mesa.

Convenção: as funções recebem `pandas.Series` indexada por período mensal e
devolvem escalares ou séries. Elas não sabem de estratégia, ativo ou país.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MONTHS_PER_YEAR = 12

#: Abaixo disto, um excesso de retorno é ruído numérico e não sinal.
#:
#: A estratégia CDI comparada com o próprio CDI tem excesso exatamente zero na
#: matemática, mas ~1e-11 depois do arredondamento do dataset. Dividir uma média
#: de 1e-12 por um desvio de 4e-11 devolvia um Sharpe de -0,10: um número de
#: aparência plausível saído de uma divisão 0/0.
NOISE_FLOOR = 1e-9


def drawdown_series(wealth: pd.Series) -> pd.Series:
    """Queda percentual em relação ao topo histórico, mês a mês."""
    peak = wealth.cummax()
    return wealth / peak - 1.0


def max_drawdown(wealth: pd.Series) -> float:
    """Pior queda em relação a um topo anterior. Negativo por convenção."""
    return float(drawdown_series(wealth).min())


def recovery_months(wealth: pd.Series) -> int | None:
    """Meses do topo anterior até recuperá-lo, para o pior drawdown.

    Duas estratégias com o mesmo retorno podem oferecer experiências muito
    diferentes; a seção 19 do estudo pede este número junto do drawdown.

    Devolve ``None`` se a série termina sem recuperar — que é informação, não
    ausência dela: significa que o investidor ainda não voltou ao topo.
    """
    dd = drawdown_series(wealth)
    if dd.empty or dd.min() >= 0:
        return 0
    trough = dd.idxmin()
    peak_value = wealth.loc[:trough].max()
    after = wealth.loc[trough:]
    recovered = after[after >= peak_value]
    if recovered.empty:
        return None
    peak_pos = wealth.index.get_loc(wealth.loc[:trough].idxmax())
    return int(wealth.index.get_loc(recovered.index[0]) - peak_pos)


def monthly_returns(wealth: pd.Series, contributions: pd.Series | None = None) -> pd.Series:
    """Retorno mensal da carteira, isolando o efeito dos aportes.

    Aporte aumenta o patrimônio sem ser retorno. Tratar a variação bruta como
    retorno inflaria a série e distorceria volatilidade, Sharpe e Sortino — num
    estudo de aportes mensais isso não é detalhe.
    """
    if contributions is None:
        return wealth.pct_change().dropna()
    prev = wealth.shift(1)
    return ((wealth - contributions) / prev - 1.0).dropna()


def volatility(returns: pd.Series) -> float:
    """Desvio-padrão anualizado dos retornos mensais."""
    return float(returns.std(ddof=1) * np.sqrt(MONTHS_PER_YEAR))


def annualized_return(returns: pd.Series) -> float:
    """Retorno geométrico anualizado a partir dos retornos mensais."""
    if returns.empty:
        return float("nan")
    total = float((1 + returns).prod())
    years = len(returns) / MONTHS_PER_YEAR
    return total ** (1 / years) - 1


def sharpe(returns: pd.Series, rf_monthly: pd.Series) -> float:
    """Sharpe sobre o excesso em relação ao CDI, anualizado.

    O ativo livre de risco do investidor brasileiro é o CDI, e ele varia bastante
    no período: usar uma taxa fixa distorceria a comparação entre décadas.
    """
    excess = (returns - rf_monthly.reindex(returns.index)).dropna()
    if excess.empty:
        return float("nan")
    sd = float(excess.std(ddof=1))
    if sd < NOISE_FLOOR:
        # Sem excesso e sem risco: o Sharpe é zero, não indefinido.
        return 0.0 if abs(float(excess.mean())) < NOISE_FLOOR else float("nan")
    return float(excess.mean() / sd * np.sqrt(MONTHS_PER_YEAR))


def sortino(returns: pd.Series, rf_monthly: pd.Series) -> float:
    """Como o Sharpe, mas penalizando só a volatilidade negativa.

    Oscilação para cima não é risco para quem está comprado; o Sortino separa as
    duas coisas, e é por isso que a seção 15 pede os dois.
    """
    excess = (returns - rf_monthly.reindex(returns.index)).dropna()
    if excess.empty:
        return float("nan")

    # Downside deviation: raiz da média dos quadrados dos desvios abaixo do alvo,
    # com os meses acima contando como zero.
    #
    # Não é o desvio-padrão do subconjunto negativo. A diferença importa: uma
    # série que cai sempre o mesmo tanto tem desvio-padrão zero entre as quedas e
    # apareceria como se não tivesse risco algum.
    downside = np.minimum(excess, 0.0)
    dd = float(np.sqrt((downside ** 2).mean()))
    if dd < NOISE_FLOOR:
        if abs(float(excess.mean())) < NOISE_FLOOR:
            return 0.0
    if dd == 0.0:
        # Nenhum mês abaixo do CDI: o risco de baixa medido é zero. Infinito diz
        # "não houve downside"; NaN diria "não sei", que é informação diferente.
        return float("inf") if excess.mean() > 0 else float("nan")
    return float(excess.mean() / dd * np.sqrt(MONTHS_PER_YEAR))


def return_index(returns: pd.Series) -> pd.Series:
    """Valor de R$1 investido, acompanhando só o retorno.

    É sobre esta série que as janelas móveis devem ser calculadas, **nunca sobre o
    patrimônio**: num estudo de aportes mensais o patrimônio cresce porque o
    investidor deposita, e tratar isso como retorno produz números absurdos —
    janelas de 12 meses com mais de 1.000%, vindas dos primeiros meses em que o
    aporte é grande diante da base acumulada.
    """
    return (1 + returns).cumprod()


def rolling_window_returns(returns: pd.Series, years: int) -> pd.Series:
    """Retorno anualizado de todas as janelas móveis de `years` anos.

    Recebe **retornos**, não patrimônio. Reduz a dependência de uma única data
    inicial: a pergunta da seção 16 é em que porcentagem das janelas uma
    estratégia venceu a outra, não quem terminou com mais dinheiro numa data.
    """
    n = years * MONTHS_PER_YEAR
    if len(returns) < n:
        return pd.Series(dtype=float)
    # Produto móvel de (1+r) sobre n meses. Direto sobre os retornos, sem passar
    # por um índice acumulado: assim uma série de exatamente n retornos produz
    # uma janela, em vez de nenhuma por falta do ponto inicial.
    growth = (1 + returns).rolling(n).apply(np.prod, raw=True)
    return (growth ** (1 / years) - 1).dropna()


def best_worst_12m(returns: pd.Series) -> tuple[float, float]:
    """Melhor e pior janela de 12 meses, a partir dos retornos."""
    r = rolling_window_returns(returns, 1)
    if r.empty:
        return (float("nan"), float("nan"))
    return (float(r.max()), float(r.min()))
