//! Carga do dataset preparado pelo Python.
//!
//! O motor não conhece fonte de dado, moeda nem calendário de bolsa: recebe um
//! painel mensal já homogêneo, em BRL, e uma tabela macro. Toda a sujeira de
//! integração fica do lado do Python, por decisão de arquitetura.

use anyhow::{Context, Result};
use serde::Deserialize;
use std::collections::HashMap;
use std::path::Path;

/// Mês no formato `AAAA-MM`, comparável e ordenável como texto.
pub type Month = String;

#[derive(Debug, Deserialize)]
struct PanelRow {
    month: String,
    ticker: String,
    #[allow(dead_code)]
    currency: String,
    #[allow(dead_code)]
    tr_local: f64,
    #[allow(dead_code)]
    fx: f64,
    tr_brl: f64,
}

#[derive(Debug, Deserialize)]
struct MacroRow {
    month: String,
    cdi_factor: f64,
    ipca_factor: f64,
}

#[derive(Debug, Default)]
pub struct Dataset {
    /// Índice de total return em BRL, por (mês, ticker).
    pub tr: HashMap<(Month, String), f64>,
    pub cdi: HashMap<Month, f64>,
    pub ipca: HashMap<Month, f64>,
    pub months: Vec<Month>,
}

impl Dataset {
    pub fn load(dir: &Path) -> Result<Self> {
        let mut ds = Dataset::default();

        let panel = dir.join("panel.csv");
        let mut rdr = csv::Reader::from_path(&panel)
            .with_context(|| format!("lendo {}", panel.display()))?;
        for row in rdr.deserialize::<PanelRow>() {
            let r = row?;
            ds.tr.insert((r.month, r.ticker), r.tr_brl);
        }

        let macro_path = dir.join("macro.csv");
        let mut rdr = csv::Reader::from_path(&macro_path)
            .with_context(|| format!("lendo {}", macro_path.display()))?;
        for row in rdr.deserialize::<MacroRow>() {
            let r = row?;
            ds.cdi.insert(r.month.clone(), r.cdi_factor);
            ds.ipca.insert(r.month, r.ipca_factor);
        }

        let mut months: Vec<Month> = ds.tr.keys().map(|(m, _)| m.clone()).collect();
        months.sort();
        months.dedup();
        ds.months = months;
        Ok(ds)
    }

    pub fn price(&self, month: &str, ticker: &str) -> Option<f64> {
        self.tr.get(&(month.to_string(), ticker.to_string())).copied()
    }

    /// Meses da janela pedida, em ordem. `start` e `end` vêm como `AAAA-MM-DD`.
    pub fn window(&self, start: &str, end: &str) -> Vec<Month> {
        let (a, b) = (&start[..7], &end[..7]);
        self.months
            .iter()
            .filter(|m| m.as_str() >= a && m.as_str() <= b)
            .cloned()
            .collect()
    }
}

/// Ticker reservado para a estratégia de renda fixa: não vem do painel, cresce
/// pelo fator do CDI do mês.
pub const CASH_TICKER: &str = "CDI";

pub fn year_of(month: &str) -> i32 {
    month[..4].parse().unwrap_or(0)
}

pub fn is_january(month: &str) -> bool {
    &month[5..7] == "01"
}
