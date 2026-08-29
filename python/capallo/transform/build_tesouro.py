"""Índice de retorno total do Tesouro IPCA+, e a duration que ele carrega.

Esta perna ficou fora do estudo desde o começo por um motivo escrito em
`docs/decisions.md`: *"Tesouro IPCA+ fica para V2 (introduz duration e marcação a
mercado)"*. É a única das quatro pernas em que **o ativo tem prazo** — ele vence,
e vencer obriga a decidir o que fazer no dia seguinte.

⚠️ Não é acréscimo pós-resultado ao universo congelado. O item está declarado em
`decisions.md` como pendente desde **26/08/2026**, antes de existir motor e antes
de qualquer número — e entra como **referência**, ao lado do CDI, não como ativo
das carteiras. A regra anti-cherry-picking continua valendo para o universo.

## As duas regras de rolagem, e por que as duas aparecem

Um título com prazo obriga a escolher uma regra, e a escolha muda o resultado. Em
vez de escolher e afirmar que não importa, as duas são implementadas:

- **`mais_longo`** (principal) — carrega sempre o Tesouro IPCA+ de vencimento mais
  distante disponível; troca quando aparece um mais longo ou quando o atual vence.
  Três rolagens em vinte anos: 2024→2035 em mar/2010, 2035→2045 em fev/2017 e
  2045→2050 em fev/2025.
- **`ate_o_vencimento`** — compra o mais longo disponível e **carrega até o
  vencimento**, só então rolando. Uma rolagem: o 2024 vence em ago/2024 e o dinheiro
  vai para o 2045.

A principal é `mais_longo` porque descreve o mandato do investidor do estudo:
vinte anos de aporte mensal com objetivo de retorno real de longo prazo. Quem
acumula não deixa a carteira encurtar sozinha — em 2023, sob a outra regra, o
aporte do mês estaria comprando um título de um ano de prazo, que é caixa
disfarçado de renda fixa longa.

`comparar_regras()` mede o que a escolha custa.

## O que é preço e o que é imposto

O **spread de rolagem entra**: vender ao `PU Venda` e comprar ao `PU Compra` é
preço, e o estudo modela preço em todas as pernas. Ele também é **intrínseco ao
instrumento** — uma ação nunca é obrigada a transacionar, um título que vence é.

O **imposto de renda não entra**, e a razão é consistência, não conveniência: a §4
congelou apenas retenção sobre dividendo, o CDI entra bruto, e as carteiras de
ação rebalanceiam por aporte justamente para não realizar ganho. Mudar a regra
tributária só para esta perna a tornaria incomparável com as outras.

Mas o que a regra ignora é medido: `custo_do_ir()` calcula quanto os 15% sobre o
ganho nominal, cobrados nas rolagens e no resgate, tirariam do resultado. É um
número grande, e o leitor precisa vê-lo mesmo que a metodologia congelada não o
aplique.

⚠️ O spread de **entrada** de cada aporte mensal não é modelado — nem aqui nem em
nenhuma outra perna, já que o estudo não cobra corretagem de ninguém. Custaria
cerca de 1,1% de cada aporte, algo como 0,06 p.p. ao ano em vinte anos.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REGRAS = ("mais_longo", "ate_o_vencimento")

#: Alíquota de IR sobre o ganho nominal em aplicação de renda fixa mantida por
#: mais de dois anos. Não é aplicada ao índice — é medida por `custo_do_ir()`.
IR_LONGO_PRAZO = 0.15


@dataclass(frozen=True)
class Rolagem:
    mes: str
    de: str
    para: str
    motivo: str
    custo_pct: float


def _mensal(df: pd.DataFrame) -> pd.DataFrame:
    """Último pregão de cada mês, por vencimento."""
    g = df.copy()
    g["month"] = g.date.dt.to_period("M")
    idx = g.groupby(["maturity", "month"]).date.idxmax()
    return g.loc[idx].sort_values(["month", "maturity"]).reset_index(drop=True)


def build_index(
    df: pd.DataFrame, regra: str = "mais_longo"
) -> tuple[pd.DataFrame, list[Rolagem]]:
    """Índice de retorno total mensal para uma regra de rolagem.

    A marcação é o `PU Venda` — o que o investidor receberia vendendo hoje, e a
    única coluna com significado estável nos vinte anos.

    A ordem dentro do mês importa e é esta: **primeiro marca, depois rola.** O
    título que se vai é avaliado ao preço do próprio mês antes de sair; só então o
    dinheiro compra o novo, ao `PU Compra`, e passa a ser marcado ao `PU Venda`
    dele. A diferença entre esses dois preços é o spread, e ele aparece uma vez,
    na rolagem — não todo mês.

    ⚠️ Quando o título vence, ele deixa de ser cotado. O valor usado é a última
    cotação publicada, que é véspera do vencimento e portanto praticamente o valor
    de face. A alternativa seria modelar o resgate ao par, e a diferença entre as
    duas está na terceira casa.
    """
    if regra not in REGRAS:
        raise ValueError(f"regra deve ser uma de {REGRAS}, veio {regra!r}")

    m = _mensal(df)
    nivel, held, marca = 1.0, None, None
    linhas: list[dict] = []
    rolagens: list[Rolagem] = []

    for mes in sorted(m.month.unique()):
        disp = m[m.month == mes]
        atual = disp[disp.maturity == held] if held is not None else disp.iloc[:0]

        # 1. Marcar o que já se tem, ao preço deste mês.
        if held is not None and not atual.empty:
            pu = float(atual.pu_venda.iloc[0])
            nivel *= pu / marca
            marca = pu

        # 2. Decidir a rolagem. Vencido ou fora de oferta obriga; um vencimento
        #    mais longo só convida, e só sob a regra que aceita o convite.
        obriga = held is None or atual.empty
        convida = regra == "mais_longo" and not obriga and disp.maturity.max() > held

        if obriga or convida:
            novo = disp.maturity.max()
            linha = disp[disp.maturity == novo].iloc[0]
            compra, venda = float(linha.pu_compra), float(linha.pu_venda)
            if held is not None:
                # O dinheiro do título antigo compra o novo ao preço de compra e
                # passa a valer o preço de venda: a diferença é o custo da troca.
                nivel *= venda / compra
                rolagens.append(Rolagem(
                    mes=str(mes),
                    de=str(pd.Timestamp(held).date()),
                    para=str(pd.Timestamp(novo).date()),
                    motivo="venceu ou saiu de oferta" if obriga else "surgiu mais longo",
                    custo_pct=(1 - venda / compra) * 100,
                ))
            held, marca = novo, venda

        linhas.append({"month": mes, "maturity": held, "pu": marca, "tr_index": nivel})

    out = pd.DataFrame(linhas)
    out["date"] = out.month.dt.to_timestamp(how="end").dt.normalize()
    out["ticker"] = "IPCAP"
    return out[["date", "ticker", "maturity", "pu", "tr_index"]], rolagens


def build(curated: Path, regra: str = "mais_longo") -> pd.DataFrame:
    df = pd.read_parquet(curated / "tesouro_ipca.parquet")
    out, _ = build_index(df, regra)
    out.to_parquet(curated / "tesouro_total_return.parquet", index=False)
    return out


def comparar_regras(curated: Path) -> pd.DataFrame:
    """Quanto a regra de rolagem decide, em vinte anos."""
    df = pd.read_parquet(curated / "tesouro_ipca.parquet")
    linhas = []
    for regra in REGRAS:
        idx, rolagens = build_index(df, regra)
        anos = (idx.date.iloc[-1] - idx.date.iloc[0]).days / 365.25
        linhas.append({
            "regra": regra,
            "rolagens": len(rolagens),
            "acumulado": float(idx.tr_index.iloc[-1] / idx.tr_index.iloc[0]),
            "nominal_aa": float(idx.tr_index.iloc[-1] / idx.tr_index.iloc[0]) ** (1 / anos) - 1,
            "custo_de_rolagem_pp": sum(r.custo_pct for r in rolagens),
        })
    return pd.DataFrame(linhas)


def custo_do_ir(curated: Path, regra: str = "mais_longo") -> dict:
    """Quanto os 15% de IR custariam, se a metodologia os aplicasse.

    Não é aplicado ao índice — ver o cabeçalho. O cálculo é o do investidor real:
    o imposto incide sobre o **ganho nominal** da posição, é cobrado quando ela é
    desfeita — nas rolagens e no resgate final — e o que sobra é reinvestido, com
    o custo virando a nova base.

    O ganho nominal de vinte anos de IPCA+ embute a inflação acumulada do período,
    então 15% do ganho nominal mordem bem mais que 15% do ganho real. É esse
    número que o leitor precisa ver, mesmo com a metodologia congelada sem ele.
    """
    df = pd.read_parquet(curated / "tesouro_ipca.parquet")
    idx, rolagens = build_index(df, regra)
    realizacoes = {r.mes for r in rolagens}

    bruto = (idx.tr_index / idx.tr_index.iloc[0]).to_numpy()
    meses = [str(m) for m in idx.date.dt.to_period("M")]

    liquido, base = 1.0, 1.0
    for i in range(1, len(bruto)):
        liquido *= bruto[i] / bruto[i - 1]
        if meses[i] in realizacoes:
            liquido -= max(liquido - base, 0.0) * IR_LONGO_PRAZO
            base = liquido
    # Resgate final: o ganho que restava desde a última realização é tributado.
    liquido -= max(liquido - base, 0.0) * IR_LONGO_PRAZO

    anos = (idx.date.iloc[-1] - idx.date.iloc[0]).days / 365.25
    b = float(bruto[-1])
    return {
        "regra": regra,
        "realizacoes": len(realizacoes) + 1,
        "bruto_aa": b ** (1 / anos) - 1,
        "liquido_de_ir_aa": liquido ** (1 / anos) - 1,
        "custo_pp_aa": (b ** (1 / anos) - liquido ** (1 / anos)) * 100,
    }


def validate(curated: Path) -> list[str]:
    path = curated / "tesouro_total_return.parquet"
    if not path.exists():
        return [f"{path} não existe"]
    df = pd.read_parquet(path).sort_values("date")

    problemas = []
    if len(df) != 241:
        problemas.append(f"{len(df)} meses, esperados 241 (dez/2005 mais a janela)")
    if (df.tr_index <= 0).any():
        problemas.append("índice com nível não positivo")
    # Título com prazo tem marcação a mercado: quedas mensais são esperadas, mas
    # uma queda enorme indicaria rolagem contabilizada como perda de nível.
    ret = df.tr_index.pct_change().dropna()
    if ret.min() < -0.25:
        problemas.append(f"queda mensal de {ret.min():.1%} — rolagem provavelmente "
                         f"lançada como perda de nível em vez de troca de título")
    if df.maturity.nunique() < 2:
        problemas.append("nenhuma rolagem em vinte anos — o título de 2024 venceu")
    return problemas
