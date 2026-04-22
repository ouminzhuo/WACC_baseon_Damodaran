# WACC_baseon_Damodaran

## Americas WACC 变量与算法口径（与 `americas-wacc/scripts/calc_wacc.py` 一致）

本节描述当前实现中每个核心变量的计算方式与依赖字段。

### 1) 输入与口径约定

- 资本结构：
  - `equity_ratio = E/V`
  - `debt_ratio = D/V`
  - `local_debt_ratio` 与 `fx_debt_ratio` 为债务币种拆分（应满足两者合计为 1）
- 股权无风险利率：
  - `equity_rf = usd_equity_rf_rate`，若未提供则回退 `usd_10y_bond_rate`
- 美国主权违约利差：
  - `us_sovereign_default_spread` 用于外币基准利率（美元10Y减美国主权违约利差）
- 项目信用利差：
  - 若提供 `project_credit_spread` 则直接使用
  - 否则按 `icr` 在 `ICR_table.csv` 映射 `Spread is`
- WHT 约束：
  - `enforce_country_wht = true` 时，WHT 从 `WHT_ctry.csv` 强制读取（缺失即报错）
  - `allow_stale_wht = false` + `max_wht_age_days` 控制 WHT 数据时效性（超期拒绝计算）

### 2) 股权侧变量

- `beta_l`（杠杆 Beta）
  - `beta_l = unlevered_beta × [1 + (1 - corporate_tax_rate) × (debt_ratio / equity_ratio)]`

- `required_equity_return`（Ke）
  - `required_equity_return = equity_rf + beta_l × total_erp`

- `equity_contribution`（股权贡献）
  - `equity_contribution = equity_ratio × required_equity_return`

### 3) 债权基准与融资利率

- `local_base_rate`（本币融资基准）
  - `local_base_rate = local_10y_bond_rate - sovereign_default_spread_local`

- `fx_base_rate`（外币融资基准）
  - `fx_base_rate = usd_10y_bond_rate - us_sovereign_default_spread`

- `local_financing_rate`
  - `local_financing_rate = local_base_rate + project_credit_spread`

- `fx_financing_rate`
  - `fx_financing_rate = fx_base_rate + project_credit_spread`

### 4) 税项与对冲调整

- `vat_applied`
  - 若 `apply_vat = true`，则 `vat_applied = vat`；否则为 `0`

- `wht_applied`
  - 若 `apply_wht = true`，则 `wht_applied = withholding_tax`；否则为 `0`

- `vat_fx_applied`（外币债权 VAT）
  - 从 `VAT_ctry.csv` 读取国家开关 `include_vat_in_fx_debt`
  - 开关为真时：`vat_fx_applied = vat_applied`；否则 `vat_fx_applied = 0`

- `hedge_cost`
  - `hedge_cost = local_base_rate - fx_base_rate + 0.01 + 0.005`

- `required_local_debt_return`（Kd1）
  - `required_local_debt_return = local_financing_rate / (1 - vat_applied)`

- `required_fx_debt_return`（Kd2）
  - 采用并行税口径税因子：`fx_tax_factor = 1 - wht_applied - vat_fx_applied`
  - 若 `apply_fx_hedge = true`：
    - `required_fx_debt_return = (fx_financing_rate + hedge_cost) / fx_tax_factor`
  - 若 `apply_fx_hedge = false`：
    - `required_fx_debt_return = fx_financing_rate / fx_tax_factor`

### 5) WACC 合成

- `debt_contribution`
  - `debt_contribution = (1 - corporate_tax_rate) × [local_debt_ratio × required_local_debt_return + fx_debt_ratio × required_fx_debt_return] × debt_ratio`

- `wacc_nominal`
  - `wacc_nominal = equity_contribution + debt_contribution`

- `wacc_real`
  - `wacc_real = (1 + wacc_nominal) / (1 + inflation_rate) - 1`

### 6) 结果输出字段

每个国家输出：
- `inputs_used`
  - `spread_rating`
  - `project_credit_spread`
  - `equity_rf_used`
  - `us_sovereign_spread_used`
  - `vat_applied`
  - `vat_fx_rule_applied`
  - `vat_fx_applied`
  - `wht_applied`
  - `wht_source`
  - `wht_source_url`
  - `wht_collected_on`
- `outputs`
  - `levered_beta`
  - `required_equity_return`
  - `equity_contribution`
  - `local_base_rate`
  - `fx_base_rate`
  - `local_financing_rate`
  - `fx_financing_rate`
  - `hedge_cost`
  - `required_local_debt_return`
  - `required_fx_debt_return`
  - `debt_contribution`
  - `wacc_nominal`
  - `wacc_real`
