"""Relatório do spike de viabilidade de dados.

Responde: quais das séries necessárias existem, desde quando, e com que evidência
de eventos societários. Não decide nada — reporta.
"""

from __future__ import annotations

import time
from datetime import date

import requests

from capallo.ingest.symbols import YAHOO_SYMBOLS
from capallo.ingest.yahoo import Probe, probe

STUDY_START = date(2006, 1, 1)

#: Dias de pregão por ano, aproximado. Serve só para flagrar buracos grosseiros.
EXPECTED_BARS_PER_YEAR = 245


def run(tickers: list[str] | None = None, pause: float = 1.5) -> list[Probe]:
    names = tickers or list(YAHOO_SYMBOLS)
    sess = requests.Session()
    out: list[Probe] = []
    for i, name in enumerate(names):
        symbol = YAHOO_SYMBOLS.get(name, name)
        out.append(probe(symbol, session=sess))
        if i < len(names) - 1:
            time.sleep(pause)  # o endpoint responde 429 sob rajada
    return out


def _coverage_flag(p: Probe) -> str:
    """Anos dentro da janela do estudo com cobertura suspeita."""
    if not p.ok:
        return "-"
    thin = [
        y
        for y, n in sorted(p.coverage_by_year.items())
        if STUDY_START.year <= y <= 2025 and n < EXPECTED_BARS_PER_YEAR * 0.9
    ]
    if not thin:
        return "ok"
    return f"{len(thin)} ano(s): {', '.join(str(y) for y in thin[:6])}"


def render(probes: list[Probe]) -> str:
    lines = []
    head = f"{'ticker':<12}{'moeda':<7}{'inicio':<12}{'cobre 2006?':<13}{'divs':<7}{'1o div':<12}{'splits':<8}{'adj':<5}"
    lines.append(head)
    lines.append("-" * len(head))
    for p in probes:
        if not p.ok:
            lines.append(f"{p.symbol:<12}FALHA: {p.error}")
            continue
        covers = "sim" if p.first_date and p.first_date <= STUDY_START else "NAO"
        lines.append(
            f"{p.symbol:<12}{p.currency or '?':<7}{str(p.first_date):<12}{covers:<13}"
            f"{p.n_dividends:<7}{str(p.first_dividend or '-'):<12}{p.n_splits:<8}"
            f"{'sim' if p.has_adjclose else 'NAO':<5}"
        )

    lines.append("")
    lines.append("Buracos de cobertura dentro da janela do estudo (2006-2025):")
    for p in probes:
        flag = _coverage_flag(p)
        if flag not in ("ok", "-"):
            lines.append(f"  {p.symbol:<12}{flag}")
    lines.append("")
    lines.append("Closes nulos:")
    for p in probes:
        if p.ok and p.n_null_close:
            lines.append(f"  {p.symbol:<12}{p.n_null_close} de {p.n_bars}")
    return "\n".join(lines)
