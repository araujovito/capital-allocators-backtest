//! Definição declarativa de uma estratégia.
//!
//! Nenhum ticker, índice ou país é hard-coded no motor. A estratégia chega de fora,
//! em TOML, e o motor apenas a executa.

use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct StrategyFile {
    pub strategy: Strategy,
}

#[derive(Debug, Deserialize)]
pub struct Strategy {
    pub name: String,
    pub start: String,
    pub end: String,
    pub base_currency: String,
    pub contribution: Contribution,
    pub rebalance: Rebalance,
    pub dividends: DividendPolicy,
    /// Pesos-alvo por ticker. Devem somar 1.0.
    pub weights: Vec<Weight>,
}

#[derive(Debug, Deserialize)]
pub struct Weight {
    pub ticker: String,
    pub weight: f64,
}

#[derive(Debug, Deserialize)]
pub struct Contribution {
    pub amount: f64,
    pub frequency: Frequency,
    /// `nominal` mantém o valor fixo; `real` corrige pelo índice de inflação.
    pub mode: ContributionMode,
    /// Índice usado para corrigir o aporte no modo `real`.
    pub inflation_index: Option<String>,
    /// Periodicidade do reajuste. Anual evita lookahead: o IPCA do mês corrente
    /// ainda não foi divulgado no dia do aporte.
    pub adjustment: Option<Frequency>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ContributionMode {
    Nominal,
    Real,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Frequency {
    Monthly,
    Annual,
}

#[derive(Debug, Deserialize)]
pub struct Rebalance {
    /// `none`, ou reequilíbrio direcionando os aportes aos subponderados.
    pub method: RebalanceMethod,
    pub frequency: Option<Frequency>,
    /// Rebalanceamento com venda dispara IR e distorce a comparação com o CDI.
    #[serde(default)]
    pub allow_selling: bool,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RebalanceMethod {
    None,
    ViaContribution,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DividendPolicy {
    /// Reinveste no próprio ativo pagador, na data de pagamento, líquido de retenção.
    Reinvest,
    /// Acumula em caixa remunerado.
    ToCash,
}

impl Strategy {
    /// Os pesos precisam somar 1.0 dentro de uma tolerância mínima.
    pub fn validate(&self) -> anyhow::Result<()> {
        let total: f64 = self.weights.iter().map(|w| w.weight).sum();
        if (total - 1.0).abs() > 1e-6 {
            anyhow::bail!("pesos somam {total}, esperado 1.0");
        }
        Ok(())
    }
}
