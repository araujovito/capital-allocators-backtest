//! Simulação da carteira.
//!
//! Determinística e sem conhecimento do experimento financeiro: recebe uma
//! estratégia declarada e um dataset, devolve o estado da carteira mês a mês.

use crate::data::{is_january, year_of, Dataset, CASH_TICKER};
use crate::strategy::{ContributionMode, Frequency, RebalanceMethod, Strategy};
use anyhow::{bail, Result};
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct MonthState {
    pub month: String,
    pub contribution: f64,
    pub contributed_cum: f64,
    pub value: f64,
    /// Posição por ativo no fim do mês.
    ///
    /// O motor emite isto desde a primeira versão porque as seções 20, 21 e 22 do
    /// estudo dependem disso e **não podem ser derivadas da série agregada**:
    /// contribuição individual de cada ativo, remoção do melhor e do pior, e
    /// Allocator Premium por região. Adicionar depois obrigaria a mexer no motor
    /// com o estudo já em produção.
    pub positions: Vec<Position>,
}

#[derive(Debug, Clone)]
pub struct Position {
    pub ticker: String,
    pub units: f64,
    pub price: f64,
    pub value: f64,
    /// Quanto foi aportado neste ativo neste mês.
    pub invested: f64,
}

/// Quantas unidades de cada ativo o investidor detém.
type Holdings = HashMap<String, f64>;

fn portfolio_value(holdings: &Holdings, ds: &Dataset, month: &str, cash: f64) -> Result<f64> {
    let mut total = cash;
    for (ticker, units) in holdings {
        if ticker == CASH_TICKER {
            // A posição em CDI é escriturada em reais, não em cotas: o valor é
            // a própria quantidade, já corrigida pelo fator do mês.
            total += units;
            continue;
        }
        let Some(price) = ds.price(month, ticker) else {
            bail!("sem preço para {ticker} em {month}");
        };
        total += units * price;
    }
    Ok(total)
}

/// Divide o aporte entre os ativos.
///
/// Fora do mês de rebalanceamento, o aporte vai proporcional aos pesos-alvo. No
/// mês de rebalanceamento, ele é direcionado primeiro aos ativos abaixo do alvo —
/// o que reequilibra a carteira **sem vender**, evitando o imposto que uma venda
/// dispararia e que distorceria a comparação com o CDI.
fn split_contribution(
    strategy: &Strategy,
    values: &HashMap<String, f64>,
    total_before: f64,
    amount: f64,
    rebalancing: bool,
) -> HashMap<String, f64> {
    let mut out = HashMap::new();
    if !rebalancing || total_before <= 0.0 {
        for w in &strategy.weights {
            out.insert(w.ticker.clone(), amount * w.weight);
        }
        return out;
    }

    let target_total = total_before + amount;
    let mut deficits = HashMap::new();
    let mut deficit_sum = 0.0;
    for w in &strategy.weights {
        let current = values.get(&w.ticker).copied().unwrap_or(0.0);
        let deficit = (w.weight * target_total - current).max(0.0);
        deficits.insert(w.ticker.clone(), deficit);
        deficit_sum += deficit;
    }

    if deficit_sum <= 0.0 {
        for w in &strategy.weights {
            out.insert(w.ticker.clone(), amount * w.weight);
        }
    } else if deficit_sum >= amount {
        // O aporte não cobre todos os déficits: rateia na proporção deles.
        for w in &strategy.weights {
            out.insert(w.ticker.clone(), amount * deficits[&w.ticker] / deficit_sum);
        }
    } else {
        // Cobre os déficits e distribui a sobra pelos pesos-alvo.
        let leftover = amount - deficit_sum;
        for w in &strategy.weights {
            out.insert(w.ticker.clone(), deficits[&w.ticker] + leftover * w.weight);
        }
    }
    out
}

pub fn run(strategy: &Strategy, ds: &Dataset) -> Result<Vec<MonthState>> {
    let months = ds.window(&strategy.start, &strategy.end);
    if months.is_empty() {
        bail!("nenhum mês no dataset dentro de {} a {}", strategy.start, strategy.end);
    }

    let rebalancing_enabled = matches!(strategy.rebalance.method, RebalanceMethod::ViaContribution);
    let mut holdings: Holdings = HashMap::new();
    let mut cash = 0.0_f64;
    let mut contribution = strategy.contribution.amount;
    let mut contributed_cum = 0.0;
    let mut states = Vec::with_capacity(months.len());
    let start_year = year_of(&months[0]);

    for month in &months {
        // 1. O caixa rende CDI antes de qualquer movimento do mês.
        if let Some(f) = ds.cdi.get(month) {
            cash *= f;
        }
        if let Some(units) = holdings.get_mut(CASH_TICKER) {
            if let Some(f) = ds.cdi.get(month) {
                *units *= f;
            }
        }

        // 2. Reajuste do aporte: anual, em janeiro, pelo IPCA do ano anterior.
        //    Anual e não mensal para não usar um IPCA ainda não divulgado no dia
        //    do aporte, o que seria lookahead.
        if matches!(strategy.contribution.mode, ContributionMode::Real)
            && is_january(month)
            && year_of(month) > start_year
        {
            let prev = year_of(month) - 1;
            let factor: f64 = ds
                .ipca
                .iter()
                .filter(|(m, _)| year_of(m) == prev)
                .map(|(_, f)| *f)
                .product();
            contribution *= factor;
        }

        // 3. Aporte.
        let rebalancing = rebalancing_enabled
            && matches!(strategy.rebalance.frequency, Some(Frequency::Annual))
            && is_january(month)
            && year_of(month) > start_year;

        let mut values = HashMap::new();
        for w in &strategy.weights {
            let units = holdings.get(&w.ticker).copied().unwrap_or(0.0);
            let v = if w.ticker == CASH_TICKER {
                units
            } else {
                units * ds.price(month, &w.ticker).unwrap_or(0.0)
            };
            values.insert(w.ticker.clone(), v);
        }
        let total_before = portfolio_value(&holdings, ds, month, cash)?;

        let invested_now =
            split_contribution(strategy, &values, total_before, contribution, rebalancing);
        for (ticker, amount) in invested_now.clone() {
            if amount <= 0.0 {
                continue;
            }
            if ticker == CASH_TICKER {
                *holdings.entry(ticker).or_insert(0.0) += amount;
                continue;
            }
            let Some(price) = ds.price(month, &ticker) else {
                bail!("sem preço para {ticker} em {month}");
            };
            // Fracionário permitido: sem isso o aporte de R$125 por ativo não
            // compraria um lote de 100 ações em 2006, e o caixa ocioso viraria
            // um viés que nada tem a ver com a estratégia.
            *holdings.entry(ticker).or_insert(0.0) += amount / price;
        }
        contributed_cum += contribution;

        let mut positions: Vec<Position> = strategy
            .weights
            .iter()
            .map(|w| {
                let units = holdings.get(&w.ticker).copied().unwrap_or(0.0);
                let price = if w.ticker == CASH_TICKER {
                    1.0
                } else {
                    ds.price(month, &w.ticker).unwrap_or(0.0)
                };
                Position {
                    ticker: w.ticker.clone(),
                    units,
                    price,
                    value: units * price,
                    invested: invested_now.get(&w.ticker).copied().unwrap_or(0.0),
                }
            })
            .collect();
        positions.sort_by(|a, b| a.ticker.cmp(&b.ticker));

        states.push(MonthState {
            month: month.clone(),
            contribution,
            contributed_cum,
            value: portfolio_value(&holdings, ds, month, cash)?,
            positions,
        });
    }
    Ok(states)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::strategy::{Contribution, Rebalance, Weight};

    fn strategy(weights: Vec<(&str, f64)>, method: RebalanceMethod) -> Strategy {
        Strategy {
            name: "teste".into(),
            start: "2006-01-01".into(),
            end: "2025-12-31".into(),
            base_currency: "BRL".into(),
            contribution: Contribution {
                amount: 1000.0,
                frequency: Frequency::Monthly,
                mode: ContributionMode::Real,
                inflation_index: Some("IPCA".into()),
                adjustment: Some(Frequency::Annual),
            },
            rebalance: Rebalance {
                method,
                frequency: Some(Frequency::Annual),
                allow_selling: false,
            },
            dividends: crate::strategy::DividendPolicy::Reinvest,
            weights: weights
                .into_iter()
                .map(|(t, w)| Weight { ticker: t.into(), weight: w })
                .collect(),
        }
    }

    #[test]
    fn aporte_sem_rebalanceamento_segue_os_pesos() {
        let s = strategy(vec![("A", 0.5), ("B", 0.5)], RebalanceMethod::None);
        let values = HashMap::from([("A".to_string(), 900.0), ("B".to_string(), 100.0)]);
        let split = split_contribution(&s, &values, 1000.0, 100.0, false);
        assert!((split["A"] - 50.0).abs() < 1e-9);
        assert!((split["B"] - 50.0).abs() < 1e-9);
    }

    #[test]
    fn rebalanceamento_direciona_ao_subponderado() {
        // Carteira 900/100 com alvo 50/50: o aporte deve ir todo para B, que está
        // muito abaixo do alvo, sem que nada precise ser vendido.
        let s = strategy(vec![("A", 0.5), ("B", 0.5)], RebalanceMethod::ViaContribution);
        let values = HashMap::from([("A".to_string(), 900.0), ("B".to_string(), 100.0)]);
        let split = split_contribution(&s, &values, 1000.0, 100.0, true);
        assert!((split["B"] - 100.0).abs() < 1e-9);
        assert!(split["A"].abs() < 1e-9);
    }

    #[test]
    fn rebalanceamento_com_sobra_distribui_pelos_pesos() {
        // Déficit de B é 10; o aporte de 100 cobre e sobra 90, rateado 50/50.
        let s = strategy(vec![("A", 0.5), ("B", 0.5)], RebalanceMethod::ViaContribution);
        let values = HashMap::from([("A".to_string(), 550.0), ("B".to_string(), 450.0)]);
        let split = split_contribution(&s, &values, 1000.0, 100.0, true);
        let total: f64 = split.values().sum();
        assert!((total - 100.0).abs() < 1e-9, "o aporte inteiro precisa ser alocado");
        assert!(split["B"] > split["A"], "o subponderado recebe mais");
    }

    /// Dataset mínimo: dois ativos, preço constante, sem inflação nem CDI.
    fn dataset_plano(meses: &[&str], tickers: &[&str], preco: f64) -> Dataset {
        let mut ds = Dataset::default();
        for m in meses {
            for t in tickers {
                ds.tr.insert((m.to_string(), t.to_string()), preco);
            }
            ds.cdi.insert(m.to_string(), 1.0);
            ds.ipca.insert(m.to_string(), 1.0);
        }
        ds.months = meses.iter().map(|m| m.to_string()).collect();
        ds.months.sort();
        ds
    }

    #[test]
    fn posicoes_somam_o_patrimonio() {
        // Invariante: o patrimônio publicado tem de ser a soma das posições.
        // Sem isso, a contribuição individual de cada ativo (seção 20) não
        // reconciliaria com o resultado da carteira.
        let s = strategy(vec![("A", 0.5), ("B", 0.5)], RebalanceMethod::ViaContribution);
        let ds = dataset_plano(&["2006-01", "2006-02", "2006-03"], &["A", "B"], 10.0);
        let states = run(&s, &ds).expect("simulação");
        for st in &states {
            let soma: f64 = st.positions.iter().map(|p| p.value).sum();
            assert!((soma - st.value).abs() < 1e-6, "mês {}: {} != {}", st.month, soma, st.value);
        }
    }

    #[test]
    fn sem_valorizacao_o_patrimonio_iguala_o_aportado() {
        // Preço constante e nenhuma remuneração: patrimônio == total aportado.
        // Pega erro de dupla contagem de aporte, que foi como o bug das 173
        // unidades apareceu do lado do Python.
        let s = strategy(vec![("A", 1.0)], RebalanceMethod::None);
        let ds = dataset_plano(&["2006-01", "2006-02", "2006-03"], &["A"], 10.0);
        let states = run(&s, &ds).expect("simulação");
        let last = states.last().unwrap();
        assert!((last.value - last.contributed_cum).abs() < 1e-6);
        assert!((last.contributed_cum - 3000.0).abs() < 1e-6);
    }

    #[test]
    fn carteira_vazia_nao_quebra_o_rebalanceamento() {
        let s = strategy(vec![("A", 0.5), ("B", 0.5)], RebalanceMethod::ViaContribution);
        let split = split_contribution(&s, &HashMap::new(), 0.0, 100.0, true);
        let total: f64 = split.values().sum();
        assert!((total - 100.0).abs() < 1e-9);
    }
}
