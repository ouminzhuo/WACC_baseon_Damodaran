# Americas WACC 数据采集指南（2026-04）

## 国家范围
- 加拿大（Canada）
- 巴西（Brazil）
- 阿根廷（Argentina）
- 智利（Chile）
- 秘鲁（Peru）


## 0) 先向用户收集的最小参数（必须）
1. 国家列表（不填则默认：加拿大、巴西、阿根廷、智利、秘鲁）
2. 资本结构：`equity_ratio`、`debt_ratio`
3. 债务币种结构：`local_debt_ratio`、`fx_debt_ratio`
4. 项目风险参数：每个国家至少给 `icr` 或 `project_credit_spread` 之一
5. 计算开关：`apply_vat`、`apply_wht`、`apply_fx_hedge`、`enforce_country_wht`

> 若第 2/3/4 项缺失，不应直接计算，应先追问补齐。

## 0.1) 可由技能自动查询/回填的参数
- `local_10y_bond_rate`：Trading Economics
- `total_erp`、`sovereign_default_spread_local`、`corporate_tax_rate`、`Moody's rating`：Damodaran ctryprem
- `vat`、`withholding_tax`：PwC Tax Summaries
- `inflation_rate`：官方 CPI YoY
- `unlevered_beta`：`betaemerg.xls` / `betaRest.xls`
- `usd_10y_bond_rate`：团队约定市场数据源

## 一、输出格式（必须按此两张汇总表输出）

### 表 1：股权侧参数与贡献
| 国家 | 无风险收益率 (Rf) | 市场风险溢价 (ERP+CRP) | 无杠杆 Beta | 杠杆贝塔 Beta | 股权回报率要求 | 股权资本 | 股权贡献 |
|---|---:|---:|---:|---:|---:|---:|---:|

### 表 2：债权侧参数与贡献
| 国家 | 本币比例 | 主权违约利差 | 本国十年国债利率 | 本币融资基准利率 | 项目信用利差 | 本币融资利率 | 外币融资基准利率 | 外币融资利率 | 营业税 | 预提税 | 汇率对冲成本 | 本币债权回报率要求 | 外币债权回报率要求 | 债权资本 | 公司所得税 | 债权贡献 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|

## 二、仓库内数据
- `VAT_ctry.csv`：国家维度规则，提供 `include_vat_in_local_debt` 和 `include_vat_in_fx_debt`。
- `WHT_ctry.csv`：国家维度规则，提供各国 WHT 取值并用于校验。
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
> 3. 外币融资基准利率计算时，使用“美国主权违约利差”（`us_sovereign_default_spread`）。

### 3) PwC Tax Summaries
- 用途：VAT / WHT 标准税率与税务注释。

### 4) 各国统计局或可信统计源
- 用途：CPI YoY（用于真实 WACC）。

## 四、建议录入字段（每个国家）
- total_erp
- unlevered_beta
- local_10y_bond_rate
- sovereign_default_spread_local
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

- 营业税方法：`VAT = S × VAT_ori`。
- 本币债权使用 `S_local=include_vat_in_local_debt`；外币债权使用 `S_fx=include_vat_in_fx_debt`。

- 股权侧无风险利率口径：`Ke` 中的 `Rf` 统一取 10 年美债利率（USD），不取本币10Y。
- 杠杆 Beta：`βL = βU × [1 + (1-Tc) × D/E]`
- `Ke = Rf_US10Y + βL × ERP_total`
- 本币基准：`local_base = local_10y - sovereign_spread_local`
- 外币基准：`fx_base = usd_10y - us_sovereign_default_spread`
- 项目利差：来自 `ICR_table.csv` 或外部已知值
- 对冲成本：`hedge = local_base - fx_base + 1.5%`
- 外币债权回报率（Kd2）分母采用并行税口径：`1 - WHT - VAT_fx`
- 名义 WACC：`WACC_nominal = Equity_contribution + Debt_contribution`
- 真实 WACC：`WACC_real = (1+WACC_nominal)/(1+inflation)-1`



## 七、最终输出的来源引用（必须附在结尾）

在两张汇总表后，必须增加“数据来源引用”章节，建议格式：

| 引用ID | 字段 | 国家 | 数值 | 来源 | URL | 数据日期 | 输出位置 |
|---|---|---|---:|---|---|---|---|
| SRC-1 | Rf(10Y美债) | 加拿大 | 4.30% | UST 10Y | <url> | 2026-04-16 | 表1-加拿大-Rf(10Y美债) |
| SRC-2 | Total ERP | 巴西 | x.xx% | Damodaran ctyprem | <url> | 2026-01 | 表1-巴西-ERP+CRP |

要求：
1. 每个关键字段都要能追溯到至少一个引用ID。
2. 输出位置必须写到“表名-国家-字段”。
3. 若日期不确定，填“日期待核验”，但 URL 不能省略。
4. Damodaran、Trading Economics、PwC 等来源可复用，但字段映射不可省略。


## 八、WHT 防偷懒约束

- 建议默认 `enforce_country_wht = true`。
- 开启时，模型必须从 `WHT_ctry.csv` 读取国家 WHT；缺失国家条目应直接报错。
- 输出中需体现 `wht_source`，并在“数据来源引用”中列出该字段位置。


## 九、WHT 在线更新要求

- `WHT_ctry.csv` 必须包含 `source_url` 与 `collected_on`。
- 默认仅使用最近 `max_wht_age_days`（默认90天）内的数据；超期则应先刷新。
- 可用 `americas-wacc/scripts/refresh_wht_table.py` 写入最新在线查询值。
