---
name: americas-wacc
description: Build WACC parameter tables and nominal/real WACC outputs for Canada, Brazil, Argentina, Chile, and Peru using Damodaran-style methodology and repository files (`ICR_table.csv`, `betaemerg.xls`, `betaRest.xls`). Use this skill when user asks to estimate country WACC, assemble required inputs, map ICR to project spread, or generate consistent financing assumptions (local vs FX debt, VAT/WHT gross-up, inflation-adjusted discount rate).
---

# Americas WACC

Use this skill to produce a complete, auditable WACC workflow for the five focus countries in the Americas.

## Workflow

1. Collect per-country inputs following `references/data_collection_guide.md`.
2. Query Damodaran country data from `https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html` and capture at minimum: `Total ERP`, `Sovereign CDS`, `Adj. spread`, `Corporate Tax Rate`, `Moody's rating`.
3. Build or update an input JSON based on `references/input_template.json`.
4. Run the calculator script to produce nominal and real WACC outputs.
5. Render the final answer using the **two required summary tables** from `references/data_collection_guide.md`.


## Start Conditions (先收集最小输入再计算)

Ask user for only these **must-provide** items before first run:
- Country list (default: Canada, Brazil, Argentina, Chile, Peru)
- Capital structure: `equity_ratio`, `debt_ratio`
- Debt mix: `local_debt_ratio`, `fx_debt_ratio`
- Project risk proxy: each country provide `icr` **or** `project_credit_spread`
- Switches: `apply_vat`, `apply_wht`, `apply_fx_hedge`

Then auto-collect or prefill the rest (with source citation):
- `local_10y_bond_rate`: Trading Economics
- `total_erp`, `sovereign_default_spread_local`, `corporate_tax_rate`, `Moody's rating`: Damodaran ctryprem
- `vat`, `withholding_tax`: PwC Tax Summaries
- `VAT_ctry.csv`: country switch for VAT inclusion in FX debt return
- `WHT_ctry.csv`: country-level WHT defaults/constraints to prevent missing WHT
- `inflation_rate`: official CPI YoY sources
- `unlevered_beta`: repository beta workbooks (`betaemerg.xls`, `betaRest.xls`)
- `usd_10y_bond_rate`: market data source used by the analyst team

If user does not provide country list, use the 5-country default.
If user does not provide debt/equity mix, block calculation and ask one concise follow-up.

## Required Inputs

For each country, provide:
- `total_erp`
- `unlevered_beta`
- `local_10y_bond_rate`
- `sovereign_default_spread_local` (priority: Sovereign CDS; fallback: Adj. spread)
- `corporate_tax_rate`
- `inflation_rate`
- `icr` **or** `project_credit_spread`

Optional but recommended:
- `vat`
- `withholding_tax`

Global assumptions:
- `equity_ratio`, `debt_ratio`
- `local_debt_ratio`, `fx_debt_ratio`
- `apply_vat`, `apply_wht`, `apply_fx_hedge`, `enforce_country_wht`
- `usd_10y_bond_rate`
- `us_sovereign_default_spread` (used for FX base rate)
- `usd_equity_rf_rate` (default to `usd_10y_bond_rate`, used in Ke)

## Script Usage

Run from repo root:

```bash
python americas-wacc/scripts/calc_wacc.py \
  --input americas-wacc/references/input_template.json \
  --icr-table ICR_table.csv \
  --vat-country-table VAT_ctry.csv \
  --wht-country-table WHT_ctry.csv
```

To write output:

```bash
python americas-wacc/scripts/calc_wacc.py \
  --input <your-input>.json \
  --icr-table ICR_table.csv \
  --output <result>.json
```

## Output Expectations

Ke 的无风险利率统一使用 10 年美债（`usd_equity_rf_rate`，默认取 `usd_10y_bond_rate`）。
外币基准利率使用 `usd_10y_bond_rate - us_sovereign_default_spread`（美国主权违约利差）。
Kd2 分母使用并行税口径：`1 - WHT - VAT_fx`。

Always include:
- 输出末尾必须附“数据来源引用”清单（含 URL、日期、字段位置映射）
- 表 1（股权侧参数与贡献）：`国家 / Rf(10Y美债) / ERP+CRP / 无杠杆Beta / 杠杆Beta / Ke / 股权资本 / 股权贡献`
- 表 2（债权侧参数与贡献）：`国家 / 本币比例 / 主权违约利差 / 本国10Y / 本币基准 / 项目信用利差 / 本币融资利率 / 外币基准 / 外币融资利率 / 营业税 / 预提税 / 汇率对冲成本 / 本币债权回报率 / 外币债权回报率 / 债权资本 / 公司所得税 / 债权贡献`
- 关键假设：资本结构、本外币债务比例、VAT/WHT 是否计入、是否计入汇率对冲
- 一段国家特例说明（尤其阿根廷）

## Resources

- `scripts/calc_wacc.py`: deterministic calculator for the full formula chain.
- `references/data_collection_guide.md`: required output table format, data sourcing and field definitions.
- `references/input_template.json`: ready-to-edit input payload template.


## Source Citation Requirements

In every final output, append a **数据来源引用** section at the end.

Required format:
1. Use IDs like `[SRC-1]`, `[SRC-2]`
2. For each metric, include: `字段名 / 数值 / 来源名称 / URL / 数据日期 / 在输出中的位置`
3. Position must be explicit, e.g. `表1-加拿大-Rf(10Y美债)` or `表2-巴西-主权违约利差`.
4. If one source supports multiple fields, still list each field-position mapping separately.

If source date is unknown, mark as `日期待核验` and keep URL mandatory.


## Anti-lazy WHT checklist

Before final answer, verify for each country:
1. `inputs_used.wht_source` is not `disabled` when WHT is enabled.
2. `inputs_used.wht_applied` is present and comes from `WHT_ctry.csv` when `enforce_country_wht=true`.
3. `source_refs` includes WHT entry with table position mapping.
