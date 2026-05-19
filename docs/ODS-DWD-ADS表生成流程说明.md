# ODS-DWD-ADS 表生成流程说明

版本：v1.0

日期：2026-05-07

适用项目：同城配送经营分析系统

## 1. 这份文档说明什么

这份文档专门说明当前项目里的数据表和中间文件是怎么生成的。

简单说，当前系统不是直接把 Excel 或 CSV 放到网页上展示，而是通过一条自动化数据链路生成看板数据：

```text
原始订单 / 名单文件
  -> Python 导入程序
  -> Stage 临时标准文件
  -> DuckDB ODS 原始数据层
  -> DuckDB 标准名单表
  -> DuckDB DWD 标准明细层
  -> DuckDB ADS 报表汇总层
  -> 网页看板 / Power BI
```

其中：

- ODS 是原始数据层，尽量保留导入后的原始数据。
- DWD 是标准明细层，把订单、骑手、商家、合伙人匹配好，并补齐计算字段。
- ADS 是报表汇总层，按页面需要提前汇总好，网页和 Power BI 优先读取这一层。

## 2. 生成入口在哪里

当前数据生成主要通过以下入口触发。

### 2.1 普通导入

双击：

```text
01-一键导入数据.bat
```

或命令行执行：

```bash
python main.py import --mode=auto
```

普通导入会检查文件 SHA。如果同一个文件已经成功导入过，并且文件内容没有变化，就会跳过。

适合日常新增或替换数据后导入。

### 2.2 强制重建

双击：

```text
01-一键强制重建.bat
```

或命令行执行：

```bash
python main.py import --mode=force
```

强制重建会忽略“文件未变化就跳过”的判断，重新处理当前扫描到的文件，并重建这些文件对应月份的 DWD 和 ADS。

适合以下场景：

- 代码逻辑修过了，但原始文件没变。
- 骑手姓名、商家名称、有效订单、补贴等口径修正后，需要让旧月份重新生效。
- 普通导入显示 skipped，但你确认需要重新生成结果。

## 3. 原始文件放在哪里

当前项目会扫描配置里定义的数据目录。常见原始文件包括：

| 文件类型 | 内容 | 作用 |
|---|---|---|
| 订单明细 | 每一笔订单的订单号、时间、骑手、商家、金额、状态等 | 所有指标的主来源 |
| 帮手 / 骑手信息表 | 骑手 ID、骑手姓名、入职时间、在职状态等 | 匹配骑手姓名、全职兼职、新骑手 |
| 商户 / 商家信息表 | 商家 ID、商户名称、注册时间、状态等 | 匹配商户名称、新商家、商家名单 |
| 合伙人信息表 | 合伙人 ID、名称、省市区、区域等 | 匹配区域、全国排名、城市经营 |

注意：

- 原始文件不是最终报表数据。
- 原始文件导入后，会被写入 DuckDB 数据库。
- 网页看板读取的是 DuckDB 里的标准表和汇总表。

## 4. 总体生成流程

当前主流程在代码里由 `import_all(...)` 串起来，核心步骤如下。

### 4.1 第一步：初始化数据库

程序先执行数据库初始化：

```text
init_database(settings)
```

它会确保 DuckDB 数据库文件和必要表结构存在。

数据库文件通常是：

```text
db/delivery_analysis.duckdb
```

如果数据库不存在，首次导入会自动创建。

### 4.2 第二步：扫描原始文件

程序扫描订单、骑手、商家、合伙人等原始文件。

扫描到的文件会被记录到文件注册表：

```text
ods_file_registry
```

注册内容包括：

- 文件路径
- 文件类型
- 文件 SHA256
- 导入状态
- 对应月份
- stage 文件路径
- run_id

为什么要记录 SHA？

因为这样可以判断“这个文件是不是已经成功导入过”。如果文件没变，普通导入就可以跳过，避免重复导入。

### 4.3 第三步：订单文件预处理成 Stage

订单原始文件可能是 Excel，也可能是 CSV，而且列名可能不完全一致。

程序会先把订单文件预处理成标准 CSV，也就是 Stage 文件。

Stage 文件通常放在：

```text
data/orders_stage/
```

Stage 的作用：

- 把 Excel / CSV 统一成标准 CSV。
- 修正明显的编码和列名问题。
- 为后续 DuckDB 批量读取做准备。
- 避免每次都直接读复杂 Excel。

如果原始订单文件没变，普通导入可能复用已有 Stage 文件。

### 4.4 第四步：加载订单 Stage 到临时表

程序会用 DuckDB 的 CSV 读取能力读取 Stage 文件。

中间会进入临时表：

```text
stg_order_raw
```

这个表主要是导入过程中的临时承接，不是给网页直接看的正式层。

在这一步，程序会做字段映射。

例如原始文件里可能叫：

- 配送员id
- 骑手ID
- 帮手id

系统会按字段映射规则统一成标准字段。

### 4.5 第五步：写入 ODS 原始数据层

Stage 订单数据会被合并到：

```text
ods_order_detail_raw
```

如果这次导入影响了某个月，程序会先删除该月旧的 ODS 订单，再写入新订单。

这样做的原因：

- 避免同一个月重复导入造成重复订单。
- 保证一个月的数据以当前最新文件为准。
- 后续 DWD / ADS 可以基于该月重新生成。

### 4.6 第六步：导入名单原始层

骑手、商家、合伙人名单文件也会先进入 ODS 原始名单层。

主要表包括：

```text
ods_rider_roster_raw
ods_merchant_roster_raw
ods_partner_roster_raw
```

这几张表保留的是名单文件导入后的原始形态。

它们的作用是：

- 保存原始名单来源。
- 支持后续重新生成标准名单表。
- 方便排查“姓名为什么没匹配上”“商户名称为什么不对”等问题。

### 4.7 第七步：生成标准名单表

原始名单层会进一步整理成标准名单表：

```text
rider_roster
merchant_roster
partner_roster
```

这三张表是 DWD 匹配的基础。

标准名单表会做：

- ID 标准化
- 姓名 / 名称清洗
- 注册或入职日期解析
- 在职状态识别
- 区域拆分
- 去重和最新记录选择

例如：

- 帮手信息表中的“帮手id”会作为骑手 ID。
- 帮手信息表中的“帮手姓名”会作为骑手姓名。
- 商户信息表中的“商家ID”会作为商家 ID。
- 商户信息表中的“商户名称”会作为商家名称展示。

## 5. ODS 表是怎么生成的

ODS 是原始数据层。它的原则是：尽量保留导入后的原始数据，不在这一层做太多业务计算。

### 5.1 `ods_file_registry`

生成方式：

```text
扫描原始文件时自动写入
```

作用：

- 记录每个文件是否导入过。
- 记录文件 SHA。
- 支持 auto 模式跳过未变化文件。
- 支持 force 模式忽略去重重新导入。

常见字段含义：

| 字段 | 含义 |
|---|---|
| file_path | 原始文件路径 |
| file_type | 文件类型，例如 orders、riders、merchants、partners |
| sha256 | 文件内容指纹 |
| status | 文件处理状态 |
| order_month | 订单文件对应月份 |
| stage_path | 订单 Stage 文件路径 |
| run_id | 本次导入批次 ID |

### 5.2 `ods_order_detail_raw`

生成方式：

```text
订单原始文件 -> Stage CSV -> stg_order_raw -> ods_order_detail_raw
```

作用：

- 保存订单明细原始层。
- 是 DWD 订单明细的来源。
- 用于排查原始订单字段是否存在、订单号是否导入、骑手 ID 是否正确。

常见字段含义：

| 字段 | 含义 |
|---|---|
| order_id | 订单编号，程序内部标准字段名，订单唯一主键 |
| partner_id | 合伙人 ID |
| rider_id | 骑手 ID |
| rider_name | 订单里带的骑手姓名 |
| merchant_id | 商家 ID |
| merchant_name | 订单里带的商家名称 |
| order_status | 订单状态 |
| order_time | 下单时间 |
| pay_time | 支付时间 |
| accept_time | 接单时间 |
| complete_time | 完成时间 |
| cancel_time | 取消时间 |
| order_source | 订单来源 |
| amount 字段 | 订单金额、补贴、提成等金额字段 |

### 5.3 `ods_rider_roster_raw`

生成方式：

```text
帮手 / 骑手信息表 -> ods_rider_roster_raw
```

作用：

- 保存骑手名单原始导入结果。
- 后续生成 `rider_roster`。

常见字段含义：

| 字段 | 含义 |
|---|---|
| rider_id | 骑手 ID，来自帮手 id |
| rider_name | 骑手姓名，来自帮手姓名 |
| hire_date | 入职 / 注册时间 |
| employment_status | 在职状态 |
| employment_type | 全职 / 兼职识别结果 |

### 5.4 `ods_merchant_roster_raw`

生成方式：

```text
商户 / 商家信息表 -> ods_merchant_roster_raw
```

作用：

- 保存商家名单原始导入结果。
- 后续生成 `merchant_roster`。

常见字段含义：

| 字段 | 含义 |
|---|---|
| merchant_id | 商家 ID |
| merchant_name | 商户名称 / 商家名称 |
| register_date | 注册时间 |
| merchant_type | 商户类型 |
| status | 商户状态 |
| balance | 余额 |

### 5.5 `ods_partner_roster_raw`

生成方式：

```text
合伙人信息表 -> ods_partner_roster_raw
```

作用：

- 保存合伙人名单原始导入结果。
- 后续生成 `partner_roster`。

常见字段含义：

| 字段 | 含义 |
|---|---|
| partner_id | 合伙人 ID |
| partner_name | 合伙人名称 |
| region_raw | 原始区域文本 |
| province | 省份 |
| city | 城市 |
| district | 区县 |

## 6. 标准名单表是怎么生成的

标准名单表不是原始文件，而是从 ODS 名单原始层清洗出来的。

### 6.1 `rider_roster`

来源：

```text
ods_rider_roster_raw
```

生成方式：

- 清洗骑手 ID。
- 清洗骑手姓名。
- 解析入职时间。
- 识别在职状态。
- 识别全职 / 兼职。
- 同一个骑手多条记录时，保留更适合匹配的最新记录。

用途：

- 给 DWD 匹配骑手姓名。
- 判断新骑手。
- 判断全职 / 兼职。
- 支持主体分析骑手名单。
- 支持小时运力全职 / 兼职拆分。

### 6.2 `merchant_roster`

来源：

```text
ods_merchant_roster_raw
```

生成方式：

- 清洗商家 ID。
- 清洗商户名称。
- 解析注册时间。
- 清洗商户类型、状态、余额等字段。
- 同一个商家多条记录时，保留更适合匹配的最新记录。

用途：

- 给 DWD 匹配商户名称。
- 判断新商家。
- 支持商家名单。
- 支持商家完成单量分析。
- 支持用户主体识别。

### 6.3 `partner_roster`

来源：

```text
ods_partner_roster_raw
```

生成方式：

- 清洗合伙人 ID。
- 清洗合伙人名称。
- 从原始区域字段中拆分省、市、区县。
- 生成标准区域字段。

用途：

- 给订单匹配合伙人名称和区域。
- 支持全国总览的省市区筛选。
- 支持区域排名。
- 支持诊断预警。

## 7. DWD 表是怎么生成的

DWD 是标准明细层。它是从 ODS 订单明细和标准名单表生成的。

当前核心 DWD 表是：

```text
dwd_order_detail
```

### 7.1 `dwd_order_detail` 的来源

生成来源：

```text
ods_order_detail_raw
  + rider_roster
  + merchant_roster
  + partner_roster
  -> dwd_order_detail
```

### 7.2 `dwd_order_detail` 做了什么

它主要做四件事。

第一，统一字段。

例如：

- 把各种原始时间字段统一成 timestamp / date / hour。
- 把金额文本转成数字。
- 把订单状态转成标准判断字段。

第二，匹配主体。

例如：

- 用 rider_id 匹配 rider_roster。
- 用 merchant_id 匹配 merchant_roster。
- 用 partner_id 匹配 partner_roster。

第三，补齐展示名称。

骑手姓名优先级：

```text
rider_roster.rider_name
  -> dwd_order_detail 中订单自带 rider_name
  -> rider_id
```

商家名称优先级：

```text
merchant_roster.merchant_name / 商户名称
  -> dwd_order_detail 中订单自带 merchant_name
  -> merchant_id
```

第四，计算业务标记。

例如：

- 是否完成订单
- 是否取消订单
- 是否有效取消订单
- 是否有效订单
- 是否新骑手订单
- 是否新商家订单
- 是否新合伙人订单
- 是否超时
- 是否服务在线
- 是否补贴订单
- 是否全职 / 兼职骑手

### 7.3 `dwd_order_detail` 常见字段含义

| 字段 | 含义 |
|---|---|
| order_id | 订单编号，程序内部标准字段名，订单唯一主键 |
| order_date | 订单日期 |
| order_hour | 下单小时 |
| accept_hour | 接单小时 |
| order_month | 订单月份 |
| partner_id | 合伙人 ID |
| partner_name | 合伙人名称 |
| province | 省份 |
| city | 城市 |
| district | 区县 |
| rider_id | 骑手 ID |
| rider_name | 骑手姓名 |
| employment_type | 全职 / 兼职 |
| merchant_id | 商家 ID |
| merchant_name | 商户名称 |
| user_id | 用户 ID |
| order_source | 订单来源 |
| is_completed | 是否完成订单 |
| is_cancelled | 是否取消订单 |
| is_valid_cancel_order | 是否有效取消订单 |
| is_valid_order | 是否有效订单 |
| is_new_rider_order | 是否新骑手订单 |
| is_new_merchant_order | 是否新商家订单 |
| hq_subsidy_amount | 总部补贴金额 |
| partner_subsidy_amount | 合伙人补贴金额 |
| rider_commission_amount | 骑手提成 |
| coupon_amount | 优惠金额 |

### 7.4 为什么 DWD 很重要

DWD 是口径层。

如果网页、Power BI、临时 SQL 都直接从 ODS 原始表计算，很容易出现：

- 字段名称不一致。
- 骑手姓名匹配不一致。
- 商家名称匹配不一致。
- 有效订单口径不一致。
- 不同页面算出来的数据不一样。

所以当前项目先生成 DWD，再从 DWD 生成 ADS。

## 8. ADS 表是怎么生成的

ADS 是报表汇总层。它全部从 `dwd_order_detail` 汇总生成。

生成逻辑是：

```text
dwd_order_detail
  -> 按日期 / 合伙人 / 小时 / 骑手 / 商家 / 用户等维度 group by
  -> 写入 ADS 汇总表
```

网页看板多数接口读取 ADS，是因为 ADS 已经提前算好，查询更快、更稳定。

### 8.1 `ads_admin_day_metrics`

来源：

```text
dwd_order_detail
```

生成方式：

按日期、省、市、区县汇总。

用途：

- 全国总览
- 全国趋势
- 区域排名
- 全国级 KPI

常见字段：

| 字段 | 含义 |
|---|---|
| date | 日期 |
| province | 省份 |
| city | 城市 |
| district | 区县 |
| total_orders | 总订单 |
| valid_orders | 有效订单 |
| completed_orders | 完成订单 |
| cancelled_orders | 取消订单 |
| active_rider_count | 活跃骑手数 |
| active_merchant_count | 活跃商家数 |
| new_rider_count | 新骑手数 |
| new_merchant_count | 新商家数 |
| hq_subsidy_amount | 总部补贴 |
| partner_subsidy_amount | 合伙人补贴 |

### 8.2 `ads_admin_partner_metrics`

来源：

```text
dwd_order_detail
```

生成方式：

按日期、合伙人汇总。

用途：

- 合伙人排名
- 加盟商分层
- 关注加盟商
- 风险加盟商
- 新合伙人表现

常见字段：

| 字段 | 含义 |
|---|---|
| date | 日期 |
| partner_id | 合伙人 ID |
| partner_name | 合伙人名称 |
| province / city / district | 区域 |
| total_orders | 总订单 |
| valid_orders | 有效订单 |
| completed_orders | 完成订单 |
| cancelled_orders | 取消订单 |
| active_rider_count | 活跃骑手数 |
| active_merchant_count | 活跃商家数 |
| subsidy 字段 | 补贴金额 |

### 8.3 `ads_partner_day_metrics`

来源：

```text
dwd_order_detail
```

生成方式：

按日期、合伙人汇总。

用途：

- 城市经营页经营摘要
- 经营收益
- 日趋势
- 诊断预警的部分指标

它和 `ads_admin_partner_metrics` 很像，但更偏城市经营页使用。

### 8.4 `ads_partner_hour_metrics`

来源：

```text
dwd_order_detail
```

生成方式：

按日期、合伙人、小时汇总。

用途：

- 时段热力与履约
- 小时运力
- 热力图
- 准时率 / SLA
- 高峰接单骑手数
- 全职 / 兼职接单骑手数
- 全职 / 兼职人效

常见字段：

| 字段 | 含义 |
|---|---|
| date | 日期 |
| partner_id | 合伙人 ID |
| hour | 小时 |
| total_orders | 总订单 |
| completed_orders | 完成订单 |
| valid_orders | 有效订单 |
| accepted_rider_count | 接单骑手数 |
| fulltime_accepted_rider_count | 全职接单骑手数 |
| parttime_accepted_rider_count | 兼职接单骑手数 |
| efficiency | 总人效 |
| fulltime_efficiency | 全职人效 |
| parttime_efficiency | 兼职人效 |
| timeout_orders | 超时订单 |
| sla_timeout_rate | SLA 超时率 |

### 8.5 `ads_partner_rider_day_metrics`

来源：

```text
dwd_order_detail
```

生成方式：

按日期、合伙人、骑手汇总。

用途：

- 主体分析骑手名单
- 骑手每日完成单量
- 骑手完成总订单
- 是否达标
- 骑手单量分层
- 骑手提成明细

常见字段：

| 字段 | 含义 |
|---|---|
| date | 日期 |
| partner_id | 合伙人 ID |
| rider_id | 骑手 ID |
| rider_name | 骑手姓名 |
| completed_orders | 当日完成单量 |
| total_orders | 当日总订单 |
| valid_orders | 当日有效订单 |
| cancelled_orders | 当日取消订单 |
| rider_commission_amount | 当日骑手提成 |
| is_new_rider | 是否新骑手 |

### 8.6 `ads_partner_merchant_day_metrics`

来源：

```text
dwd_order_detail
```

生成方式：

按日期、合伙人、商家汇总。

用途：

- 主体分析商家名单
- 新商家分析
- 商家完成单量分析

常见字段：

| 字段 | 含义 |
|---|---|
| date | 日期 |
| partner_id | 合伙人 ID |
| merchant_id | 商家 ID |
| merchant_name | 商户名称 |
| completed_orders | 当日完成单量 |
| total_orders | 当日总订单 |
| valid_orders | 当日有效订单 |
| cancelled_orders | 当日取消订单 |
| is_new_merchant | 是否新商家 |

### 8.7 `ads_partner_user_merchant_metrics`

来源：

```text
dwd_order_detail
```

生成方式：

按合伙人、用户、商家等维度汇总。

用途：

- 用户主体识别
- 商家型用户判断
- 主体分析页中的用户主体识别模块

注意：

`merchant_like_threshold` 只应该影响用户主体识别模块，不应该影响商家名单、骑手名单、订单来源等模块。

### 8.8 直营专项 ADS 表

来源：

```text
dwd_order_detail
```

生成方式：

按直营专项需要的维度汇总。

用途：

- 城市经营页里的直营专项摘要。
- 直营取消趋势。
- 直营小时数据。
- 直营订单来源。
- 直营优惠金额。

这类表服务于直营专项视角，不再作为独立 `/direct` 页面主入口。

## 9. 日志和版本表是怎么生成的

除了业务数据表，导入程序还会生成一些运行记录表。

### 9.1 `dqc_import_log`

生成方式：

```text
每次 import_all 执行时写入
```

作用：

- 记录本次导入是否成功。
- 记录处理文件数、跳过文件数、错误文件数。
- 记录受影响月份。
- 记录最新数据版本。

### 9.2 `etl_job_run`

生成方式：

```text
每次导入开始时创建，导入结束时更新
```

作用：

- 记录每次 ETL 任务批次。
- 记录 start/end 时间。
- 记录任务状态。

### 9.3 `etl_stage_metrics`

生成方式：

```text
每个阶段执行完成后写入耗时和行数
```

作用：

- 看每一步处理了多少行。
- 看预处理、ODS、DWD、ADS 哪一步慢。
- 排查导入卡在哪个阶段。

### 9.4 `etl_publish_version`

生成方式：

```text
DWD / ADS 重建成功后发布新版本
```

作用：

- 记录当前最新可用数据版本。
- 网页顶部显示的数据版本来自这里。
- 确保页面读取的是已发布的稳定结果。

## 10. 受影响月份是怎么判断的

系统不是每次都重算所有历史数据，而是只重建受影响月份。

### 10.1 订单文件影响月份

订单文件导入后，程序会根据订单日期或文件名推导月份。

例如：

```text
2026年3月订单明细.csv
```

通常会影响：

```text
2026-03
```

于是程序会重建：

```text
2026-03 的 DWD
2026-03 的 ADS
```

### 10.2 名单文件影响月份

名单文件本身不一定属于某一个订单月份。

如果骑手、商家、合伙人名单变化，可能会影响多个历史月份的名称匹配、区域匹配、新骑手 / 新商家判断。

所以当名单变化时，系统可能会扩展重建范围。

### 10.3 为什么不默认全量重建

因为历史月份多了以后，全量重建会变慢。

当前设计是：

- 普通导入：只处理变化文件和受影响月份。
- 强制重建：重新处理当前扫描到的文件，并重建它们对应月份。
- 不默认重建所有历史月份。

## 11. auto 和 force 的区别

### 11.1 auto 模式

命令：

```bash
python main.py import --mode=auto
```

行为：

- 检查文件 SHA。
- 如果文件已经成功导入过，并且内容没变，就跳过。
- 如果文件是新的或内容变化，就重新导入。

适合：

- 日常导入。
- 追加新月份。
- 替换了原始文件。

### 11.2 force 模式

命令：

```bash
python main.py import --mode=force
```

行为：

- 忽略“已成功导入且文件未变化”的跳过逻辑。
- 当前扫描到的文件重新走预处理、ODS、DWD、ADS。
- 重新发布数据版本。

适合：

- 修过代码逻辑。
- 修过字段匹配逻辑。
- 修过有效订单口径。
- 修过姓名清洗逻辑。
- 原始文件没变，但结果必须重新生成。

## 12. 网页看板是怎么拿到这些数据的

网页不是直接打开 Excel，也不是直接读取原始订单。

网页通过 FastAPI 接口读取 DuckDB 里的 DWD / ADS 表。

例如：

| 页面 | 主要接口 | 主要读取层 |
|---|---|---|
| 全国总览 | `/api/v1/admin/metrics` | ADS |
| 城市经营 | `/api/v1/partner/{partner_id}/overview` | ADS |
| 时段热力与履约 | `/api/v1/partner/{partner_id}/hourly` | ADS |
| 主体分析 | `/api/v1/partner/{partner_id}/riders`、`/merchants`、`/order-sources` | ADS + DWD |
| 诊断预警 | `/api/v1/admin/health`、`/fluctuation` | ADS |

为什么网页优先读 ADS？

因为 ADS 已经汇总好了，页面打开时不需要重新扫全部订单明细。

## 13. Power BI 应该读哪些表

如果用 Power BI 连接当前 DuckDB，建议优先读取 ADS 表。

推荐读取：

```text
ads_admin_day_metrics
ads_admin_partner_metrics
ads_partner_day_metrics
ads_partner_hour_metrics
ads_partner_rider_day_metrics
ads_partner_merchant_day_metrics
ads_partner_user_merchant_metrics
rider_roster
merchant_roster
partner_roster
```

只有当你需要钻取订单明细时，再读取：

```text
dwd_order_detail
```

不建议 Power BI 直接读取：

```text
ods_order_detail_raw
ods_rider_roster_raw
ods_merchant_roster_raw
ods_partner_roster_raw
```

原因：

- ODS 更接近原始数据，字段不适合直接展示。
- ODS 没有完整口径字段。
- 直接用 ODS 容易造成 Power BI 和网页口径不一致。

## 14. Power BI 刷新时要注意什么

DuckDB 是单文件数据库。

如果 Python 导入程序正在写入数据库，而 Power BI 同时刷新，可能会遇到文件锁问题。

建议流程：

```text
1. 关闭 Power BI 当前连接或停止刷新
2. 执行 01-一键导入数据.bat 或 01-一键强制重建.bat
3. 等导入完成
4. 再打开 Power BI 刷新数据
```

如果 Power BI 直连 DuckDB，建议使用只读 DSN。

当前推荐 DSN：

```text
DeliveryDuckDB
```

数据库路径：

```text
F:\codex\delivery-dashboard\db\delivery_analysis.duckdb
```

## 15. 如何排查某个数据为什么不对

建议按这个顺序查。

### 15.1 查原始文件是否有

先确认订单明细、骑手表、商家表里有没有这个 ID 或名称。

例如：

- 骑手 ID 是否在订单明细中出现。
- 骑手 ID 是否在帮手信息表中出现。
- 商家 ID 是否在商户信息表中出现。

### 15.2 查 ODS 是否导入

如果原始文件里有，但页面没有，查 ODS：

```sql
select *
from ods_order_detail_raw
where rider_id = '71640';
```

或：

```sql
select *
from ods_merchant_roster_raw
where merchant_id = '18117';
```

### 15.3 查标准名单是否匹配

查骑手标准名单：

```sql
select *
from rider_roster
where rider_id = '71640';
```

查商家标准名单：

```sql
select *
from merchant_roster
where merchant_id = '18117';
```

### 15.4 查 DWD 是否生成正确

查 DWD：

```sql
select rider_id, rider_name, merchant_id, merchant_name, order_date, is_completed
from dwd_order_detail
where rider_id = '71640';
```

如果 DWD 已经正确，说明清洗匹配层没有问题。

### 15.5 查 ADS 是否汇总正确

查骑手日汇总：

```sql
select date, rider_id, rider_name, completed_orders
from ads_partner_rider_day_metrics
where rider_id = '71640'
order by date;
```

如果 ADS 不对，说明汇总层生成有问题。

### 15.6 查接口或页面是否展示错误

如果 ADS 正确但页面不对，再查接口：

```text
/api/v1/partner/{partner_id}/riders
```

这时问题一般在 API 返回逻辑或前端展示逻辑。

## 16. 一句话总结

当前系统的数据不是手工生成的，而是由 Python 导入程序自动完成：

```text
原始文件
  -> Stage
  -> ODS 原始层
  -> 标准名单表
  -> DWD 标准明细层
  -> ADS 报表汇总层
  -> 网页 / Power BI 展示
```

如果只是原始文件变了，用普通导入。

如果代码逻辑变了但文件没变，用强制重建。

如果页面数据不对，按 ODS、标准名单、DWD、ADS、API、前端这个顺序排查，最快能定位问题在哪一层。
