# Americas WACC 数据采集指南（2026-04）

## 国家范围
- 加拿大（Canada）
- 巴西（Brazil）
- 阿根廷（Argentina）
- 智利（Chile）
- 秘鲁（Peru）

## 仓库内数据
- `ICR_table.csv`：ICR 区间 → 评级与项目利差（Spread）。
- `betaemerg.xls`：巴西、阿根廷、智利、秘鲁等新兴市场行业 Beta（Industry Averages）。
- `betaRest.xls`：加拿大等非新兴市场行业 Beta。

## 外部数据
1. Trading Economics：各国 10 年期国债收益率（Rf / 本币10Y）
2. Damodaran `ctryprem`：
   - Mature ERP
   - Country Risk Premium (CRP)
   - Sovereign default spread
   - Corporate Tax Rate
3. PwC Tax Summaries：VAT / WHT 标准税率与注释。
4. 各国统计局或可信统计源：CPI YoY（用于真实 WACC）。

## 建议录入字段（每个国家）
- risk_free_rate
- total_erp
- unlevered_beta
- local_10y_bond_rate
- sovereign_default_spread_local
- sovereign_default_spread_usd（可选，不填时默认等于 local）
- corporate_tax_rate
- vat
- withholding_tax
- inflation_rate
- `icr` 或 `project_credit_spread`（二选一）

## 阿根廷特例
- 若本币债券失真，优先按美元融资逻辑处理：
  - 使用美元基准利率
  - 主权利差采用美元口径
  - 在结果说明中标注“本币市场失真处理”

## 公式约定
- 杠杆 Beta：`βL = βU × [1 + (1-Tc) × D/E]`
- `Ke = Rf + βL × ERP_total`
- 本币基准：`local_base = local_10y - sovereign_spread_local`
- 外币基准：`fx_base = usd_10y - sovereign_spread_usd`
- 项目利差：来自 `ICR_table.csv` 或外部已知值
- 对冲成本：`hedge = local_base - fx_base + 1.5%`
- 名义 WACC：`WACC_nominal = Equity_contribution + Debt_contribution`
- 真实 WACC：`WACC_real = (1+WACC_nominal)/(1+inflation)-1`
