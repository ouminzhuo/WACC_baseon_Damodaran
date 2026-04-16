# Americas WACC 数据采集指南（2026-04）

## 国家范围
- 加拿大（Canada）
- 巴西（Brazil）
- 阿根廷（Argentina）
- 智利（Chile）
- 秘鲁（Peru）

## 一、输出格式（必须按此两张汇总表输出）

### 表 1：股权侧参数与贡献
| 国家 | 无风险收益率 (Rf) | 市场风险溢价 (ERP+CRP) | 无杠杆 Beta | 杠杆贝塔 Beta | 股权回报率要求 | 股权资本 | 股权贡献 |
|---|---:|---:|---:|---:|---:|---:|---:|

### 表 2：债权侧参数与贡献
| 国家 | 本币比例 | 主权违约利差 | 本国十年国债利率 | 本币融资基准利率 | 项目信用利差 | 本币融资利率 | 外币融资基准利率 | 外币融资利率 | 营业税 | 预提税 | 汇率对冲成本 | 本币债权回报率要求 | 外币债权回报率要求 | 债权资本 | 公司所得税 | 债权贡献 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|

## 二、仓库内数据
- `ICR_table.csv`：ICR 区间 → 评级与项目利差（Spread）。
- `betaemerg.xls`：巴西、阿根廷、智利、秘鲁等新兴市场行业 Beta（Industry Averages）。
- `betaRest.xls`：加拿大等非新兴市场行业 Beta。

## 三、外部数据源与查询口径

### 1) Trading Economics
- 用途：各国 10 年期国债收益率（Rf / 本币10Y）。

### 2) Damodaran 国家风险表（必填）
- **URL：** https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html
- 必查字段：
  - `Total ERP`（直接作为 ERP+CRP）
  - `Sovereign CDS`（若有，优先作为主权违约利差）
  - `Adj. spread`（若无 Sovereign CDS，则用 Adj. spread）
  - `Corporate Tax Rate`
  - `Moody's rating`（用于说明风险评级来源）

> 主权违约利差取值规则：
> 1. 优先 `Sovereign CDS`
> 2. 无 CDS 时使用 `Adj. spread`

### 3) PwC Tax Summaries
- 用途：VAT / WHT 标准税率与税务注释。

### 4) 各国统计局或可信统计源
- 用途：CPI YoY（用于真实 WACC）。

## 四、建议录入字段（每个国家）
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

## 五、阿根廷特例
- 若本币债券失真，优先按美元融资逻辑处理：
  - 使用美元基准利率
  - 主权利差采用美元口径
  - 在结果说明中标注“本币市场失真处理”

## 六、公式约定
- 杠杆 Beta：`βL = βU × [1 + (1-Tc) × D/E]`
- `Ke = Rf + βL × ERP_total`
- 本币基准：`local_base = local_10y - sovereign_spread_local`
- 外币基准：`fx_base = usd_10y - sovereign_spread_usd`
- 项目利差：来自 `ICR_table.csv` 或外部已知值
- 对冲成本：`hedge = local_base - fx_base + 1.5%`
- 名义 WACC：`WACC_nominal = Equity_contribution + Debt_contribution`
- 真实 WACC：`WACC_real = (1+WACC_nominal)/(1+inflation)-1`
