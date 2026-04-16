---
name: americas-wacc
description: Build WACC parameter tables and nominal/real WACC outputs for Canada, Brazil, Argentina, Chile, and Peru using Damodaran-style methodology and repository files (`ICR_table.csv`, `betaemerg.xls`, `betaRest.xls`). Use this skill when user asks to estimate country WACC, assemble required inputs, map ICR to project spread, or generate consistent financing assumptions (local vs FX debt, VAT/WHT gross-up, inflation-adjusted discount rate).
---

# Americas WACC

Use this skill to produce a complete, auditable WACC workflow for the five focus countries in the Americas.

## Workflow

1. Collect per-country inputs following `references/data_collection_guide.md`.
2. Build or update an input JSON based on `references/input_template.json`.
3. Run the calculator script to produce nominal and real WACC outputs.
4. Return a clear table with assumptions, country inputs, and key outputs.

## Required Inputs

For each country, provide:
- `risk_free_rate`
- `total_erp`
- `unlevered_beta`
- `local_10y_bond_rate`
- `sovereign_default_spread_local`
- `corporate_tax_rate`
- `inflation_rate`
- `icr` **or** `project_credit_spread`

Optional but recommended:
- `vat`
- `withholding_tax`
- `sovereign_default_spread_usd`

Global assumptions:
- `equity_ratio`, `debt_ratio`
- `local_debt_ratio`, `fx_debt_ratio`
- `apply_vat`, `apply_wht`, `apply_fx_hedge`
- `usd_10y_bond_rate`

## Script Usage

Run from repo root:

```bash
python americas-wacc/scripts/calc_wacc.py \
  --input americas-wacc/references/input_template.json \
  --icr-table ICR_table.csv
```

To write output:

```bash
python americas-wacc/scripts/calc_wacc.py \
  --input <your-input>.json \
  --icr-table ICR_table.csv \
  --output <result>.json
```

## Output Expectations

Always include:
- Levered beta, required equity return, and equity contribution
- Local/FX base rates and financing rates
- Required local/FX debt returns after tax gross-up switches
- Debt contribution, nominal WACC, and real WACC
- A short note for country-specific handling (especially Argentina)

## Resources

- `scripts/calc_wacc.py`: deterministic calculator for the full formula chain.
- `references/data_collection_guide.md`: data sourcing and field definitions.
- `references/input_template.json`: ready-to-edit input payload template.
