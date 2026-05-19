# ODS-DWD-ADS 现有表说明

版本：v1.0  
适用范围：当前同城配送经营分析系统  
用途：解释当前 DuckDB 数据库中各层表的作用、字段含义、Power BI 使用建议和数据排查路径

---

## 1. 先纠正一个关键概念

ADS 不是原始表。

当前系统的数据分层是：

```text
ODS = 原始数据层
DWD = 标准明细层
ADS = 报表汇总层
```

可以这样理解：

```text
ODS：原材料
DWD：洗干净、配好字段、算好口径的一单一行明细
ADS：已经按页面需要汇总好的报表结果
```

完整数据流：

```text
原始 Excel / CSV
        ↓
ODS 原始层
        ↓
标准名单层
        ↓
DWD 标准订单明细层
        ↓
ADS 报表汇总层
        ↓
网页看板 / Power BI
```

做 Power BI 时的基本原则：

```text
能读 ADS 就读 ADS
必须看订单明细才读 DWD
不要直接用 ODS 做正式报表
```

---

## 2. 表分层总览

当前项目里的表可以分成 5 类。

| 类别 | 代表表 | 作用 |
| --- | --- | --- |
| 导入/质检控制表 | `ods_file_registry`、`etl_job_run`、`dqc_import_log` | 记录文件、批次、导入状态、异常 |
| ODS 原始层 | `ods_order_detail_raw`、`ods_rider_roster_raw`、`ods_merchant_roster_raw`、`ods_partner_roster_raw` | 保存导入后的原始数据 |
| 标准名单层 | `rider_roster`、`merchant_roster`、`partner_roster`、`partner_sla_config` | 清洗后的骑手、商家、合伙人主数据 |
| DWD 标准明细层 | `dwd_order_detail` | 一行一个标准订单，统一核心口径 |
| ADS 报表汇总层 | `ads_*` | 按页面、日期、小时、骑手、商家提前汇总好的指标 |

---

## 3. 导入 / 质检控制表

这些表不是业务分析主表，但用于追踪数据是怎么导入、有没有跳过、有没有异常。

### 3.1 `ods_file_registry`

文件登记表。

作用：

```text
记录每个导入文件的信息，用于文件去重、判断是否需要重新导入。
```

主要字段：

| 字段 | 含义 |
| --- | --- |
| `file_id` | 文件唯一 ID |
| `batch_id` | 导入批次 ID |
| `file_type` | 文件类型，例如订单、骑手、商家、合伙人 |
| `source_type` | 来源类型 |
| `file_path` | 原始文件路径 |
| `file_name` | 文件名 |
| `file_size` | 文件大小 |
| `sha256` | 文件哈希，用来判断文件是否变化 |
| `order_month` | 文件对应订单月份 |
| `stage_file_path` | 预处理后的 stage 文件路径 |
| `stage_status` | stage 处理状态 |
| `imported_at` | 导入时间 |
| `status` | 导入状态 |
| `error_message` | 错误信息 |

什么时候看它：

```text
普通导入为什么跳过文件
强制重建是否真的重新处理
某个文件是哪次导入进入系统的
```

---

### 3.2 `dqc_import_log`

导入运行日志表。

作用：

```text
记录一次导入任务的总体结果。
```

主要字段：

| 字段 | 含义 |
| --- | --- |
| `run_id` | 一次导入任务 ID |
| `started_at` | 开始时间 |
| `ended_at` | 结束时间 |
| `status` | 运行状态 |
| `total_files` | 扫描到的文件数 |
| `processed_files` | 实际处理文件数 |
| `skipped_files` | 跳过文件数 |
| `error_files` | 错误文件数 |
| `message` | 导入结果提示 |

什么时候看它：

```text
一键导入是否成功
为什么显示跳过
本次导入有没有报错文件
```

---

### 3.3 `etl_job_run`

ETL 任务批次表。

作用：

```text
记录一次完整数据处理任务，包括 ODS、DWD、ADS 重建。
```

主要字段：

| 字段 | 含义 |
| --- | --- |
| `run_id` | 任务 ID |
| `backend` | 数据底座，当前是 DuckDB |
| `status` | 任务状态 |
| `affected_months` | 本次影响月份 |
| `started_at` | 开始时间 |
| `ended_at` | 结束时间 |
| `total_seconds` | 总耗时 |
| `error_message` | 错误信息 |

什么时候看它：

```text
确认本次重建影响了哪些月份
确认 DWD / ADS 是否真的重建过
```

---

### 3.4 `etl_stage_metrics`

ETL 阶段耗时表。

作用：

```text
记录导入过程中每个阶段的输入行数、输出行数和耗时。
```

主要字段：

| 字段 | 含义 |
| --- | --- |
| `stage_id` | 阶段 ID |
| `run_id` | 所属任务 ID |
| `stage_name` | 阶段名称 |
| `started_at` | 阶段开始时间 |
| `ended_at` | 阶段结束时间 |
| `duration_seconds` | 阶段耗时 |
| `input_rows` | 输入行数 |
| `output_rows` | 输出行数 |
| `status` | 阶段状态 |
| `detail` | 阶段详情 |

什么时候看它：

```text
导入慢在哪里
哪一步输入/输出行数异常
```

---

### 3.5 `etl_publish_version`

数据发布版本表。

作用：

```text
记录当前可用的数据版本。
```

主要字段：

| 字段 | 含义 |
| --- | --- |
| `data_version` | 数据版本号 |
| `run_id` | 来源任务 ID |
| `latest_ready_month` | 最新可用月份 |
| `published_at` | 发布时间 |
| `status` | 发布状态 |

什么时候看它：

```text
确认页面/Power BI 读的是不是最新数据版本
```

---

### 3.6 `dqc_abnormal_orders`

异常订单记录表。

作用：

```text
记录导入或清洗时发现的异常订单。
```

主要字段：

| 字段 | 含义 |
| --- | --- |
| `abnormal_id` | 异常记录 ID |
| `batch_id` | 批次 ID |
| `order_id` | 订单编号，程序内部标准字段名，订单唯一主键 |
| `file_name` | 来源文件 |
| `abnormal_type` | 异常类型 |
| `abnormal_detail` | 异常详情 |
| `created_at` | 记录时间 |

什么时候看它：

```text
订单缺关键字段
订单状态无法识别
导入结果和原始表对不上
```

---

## 4. ODS 原始数据层

ODS 是原始数据层。

特点：

```text
保留原始字段
字段可能还是文本
时间/金额未必已经完全标准化
适合追溯，不适合直接做正式报表
```

---

### 4.1 `ods_order_detail_raw`

原始订单明细表。

作用：

```text
保存导入后的订单明细原始字段，是排查订单源数据问题的第一层。
```

主要字段：

| 字段 | 含义 |
| --- | --- |
| `raw_id` | 原始行 ID |
| `file_registry_id` | 来源文件 ID |
| `batch_id` | 导入批次 |
| `row_number` | 原始文件行号 |
| `order_month` | 订单月份 |
| `imported_at` | 导入时间 |
| `order_id` | 订单编号，程序内部标准字段名，订单唯一主键 |
| `partner_id` | 合伙人 ID |
| `partner_name` | 合伙人名称 |
| `merchant_id` | 商家 ID |
| `merchant_name` | 商家名称 |
| `shop_name` | 商户名称 / 店铺名称 |
| `user_id` | 用户 ID |
| `rider_id` | 骑手 ID / 配送员 ID |
| `rider_name` | 骑手姓名 |
| `employment_status` | 在职状态 |
| `order_status` | 订单状态 |
| `customer_service_id` | 客服 ID |
| `order_source` | 订单来源 |
| `added_at` | 原始下单时间 |
| `pay_time` | 支付时间 |
| `accept_time` | 接单时间 |
| `cancel_time` | 取消时间 |
| `complete_time` | 完成时间 |
| `order_price` | 订单价格，原始文本 |
| `amount_payable` | 应付金额，原始文本 |
| `amount_paid` | 实付金额，原始文本 |
| `hq_discount_amount` | 总部优惠/补贴原始值 |
| `discount_amount` | 优惠金额原始值 |
| `rider_income` | 骑手提成，原始文本 |
| `partner_income` | 合伙人收入，原始文本 |
| `coupon_id` | 优惠券 ID |
| `marketing_coupon_id` | 营销券 ID |
| `raw_payload` | 原始行完整内容 |

用途：

```text
核对原始订单是否导入
核对骑手ID、商家ID是否来自订单明细
排查字段映射是否错
重建 DWD
```

不建议：

```text
不要直接拿这张表做 Power BI 正式报表。
```

---

### 4.2 `ods_rider_roster_raw`

原始骑手/帮手名单表。

作用：

```text
保存原始帮手信息表。
```

主要字段：

| 字段 | 含义 |
| --- | --- |
| `raw_id` | 原始行 ID |
| `file_registry_id` | 来源文件 ID |
| `batch_id` | 导入批次 |
| `row_number` | 原始文件行号 |
| `imported_at` | 导入时间 |
| `rider_id` | 骑手 ID / 帮手 id |
| `rider_name` | 骑手姓名 / 帮手姓名 |
| `hire_date` | 入职/注册日期，原始文本 |
| `status` | 在职状态 |
| `partner_name` | 所属合伙人 |
| `region` | 所属区域 |
| `raw_payload` | 原始行完整内容 |

当前匹配口径：

```text
帮手id = 骑手ID
帮手姓名 = 骑手姓名
```

用途：

```text
排查骑手ID和骑手姓名是否来自帮手信息表
重建标准骑手名单 rider_roster
```

---

### 4.3 `ods_merchant_roster_raw`

原始商家/商户名单表。

作用：

```text
保存原始商户信息表。
```

主要字段：

| 字段 | 含义 |
| --- | --- |
| `raw_id` | 原始行 ID |
| `file_registry_id` | 来源文件 ID |
| `batch_id` | 导入批次 |
| `row_number` | 原始文件行号 |
| `imported_at` | 导入时间 |
| `merchant_id` | 商家 ID |
| `merchant_name` | 商家名称 |
| `shop_name` | 商户名称 / 店铺名称 |
| `partner_name` | 所属合伙人 |
| `region` | 所属区域 |
| `register_date` | 注册日期，原始文本 |
| `status` | 商家状态 |
| `raw_payload` | 原始行完整内容 |

当前匹配口径：

```text
商家ID = 商家ID
商户名称优先用于页面展示
```

用途：

```text
排查商家ID、商家名称、商户名称是否匹配正确
重建标准商家名单 merchant_roster
```

---

### 4.4 `ods_partner_roster_raw`

原始合伙人名单表。

作用：

```text
保存原始合伙人信息。
```

主要字段：

| 字段 | 含义 |
| --- | --- |
| `raw_id` | 原始行 ID |
| `file_registry_id` | 来源文件 ID |
| `batch_id` | 导入批次 |
| `row_number` | 原始文件行号 |
| `imported_at` | 导入时间 |
| `partner_id` | 合伙人 ID |
| `partner_name` | 合伙人名称 |
| `open_date` | 开城日期，原始文本 |
| `region_raw` | 原始区域字段 |
| `status` | 合伙人状态 |
| `raw_payload` | 原始行完整内容 |

用途：

```text
重建标准合伙人名单 partner_roster
解析省、市、区县
判断新合伙人
```

---

## 5. 标准名单层

标准名单层是清洗后的主数据层。

作用：

```text
把原始名单里的文本日期、区域、名称等整理成可关联、可分析的标准字段。
```

---

### 5.1 `rider_roster`

标准骑手名单。

作用：

```text
给订单明细补齐骑手姓名、入职日期、在职状态。
```

字段：

| 字段 | 含义 |
| --- | --- |
| `rider_id` | 骑手 ID，主键 |
| `rider_name` | 骑手姓名 |
| `hire_date` | 入职/注册日期 |
| `status` | 在职状态 |
| `partner_name` | 所属合伙人 |
| `region` | 所属区域 |
| `last_updated_at` | 最近更新时间 |

用于：

```text
骑手姓名匹配
新骑手判断
全职/兼职识别
骑手名单展示
```

---

### 5.2 `merchant_roster`

标准商家名单。

作用：

```text
给订单明细补齐商家名称、商户名称、注册日期。
```

字段：

| 字段 | 含义 |
| --- | --- |
| `merchant_id` | 商家 ID，主键 |
| `merchant_name` | 商家名称 |
| `shop_name` | 商户名称 / 店铺名称 |
| `partner_name` | 所属合伙人 |
| `region` | 所属区域 |
| `register_date` | 注册日期 |
| `status` | 商家状态 |
| `last_updated_at` | 最近更新时间 |

用于：

```text
商家名称匹配
商户名称展示
新商家判断
商家名单展示
```

---

### 5.3 `partner_roster`

标准合伙人名单。

作用：

```text
给订单明细补齐合伙人名称和省、市、区县。
```

字段：

| 字段 | 含义 |
| --- | --- |
| `partner_id` | 合伙人 ID，主键 |
| `partner_name` | 合伙人名称 |
| `open_date` | 开城日期 |
| `region_raw` | 原始区域字段 |
| `province` | 省 |
| `city` | 市 |
| `district` | 区县 |
| `status` | 合伙人状态 |
| `last_updated_at` | 最近更新时间 |

用于：

```text
区域筛选
全国排名
城市经营
新合伙人判断
```

---

### 5.4 `partner_sla_config`

合伙人 SLA 配置表。

作用：

```text
配置某个合伙人的 SLA 履约分钟数。
```

字段：

| 字段 | 含义 |
| --- | --- |
| `partner_id` | 合伙人 ID |
| `sla_minutes` | SLA 分钟数，默认 30 |
| `effective_date` | 生效日期 |
| `updated_at` | 更新时间 |

用于：

```text
时段热力与履约
SLA 履约率
SLA 超时率
```

---

## 6. DWD 标准明细层

### 6.1 `dwd_order_detail`

这是整个系统最核心的表。

作用：

```text
一行一个标准订单，是所有经营分析口径的统一明细底座。
```

这张表已经完成：

```text
字段清洗
ID 匹配
名称补齐
日期转换
金额转换
订单状态判断
新骑手/新商家判断
有效订单判断
补贴归属计算
```

---

### 6.2 主键和批次字段

| 字段 | 含义 |
| --- | --- |
| `order_id` | 订单编号，程序内部标准字段名，主键 |
| `batch_id` | 数据重建批次 |
| `order_month` | 订单月份，用于按月重建 |

---

### 6.3 合伙人字段

| 字段 | 含义 |
| --- | --- |
| `partner_id` | 合伙人 ID |
| `partner_name` | 合伙人名称 |
| `province` | 省 |
| `city` | 市 |
| `district` | 区县 |

用于：

```text
全国总览
城市经营
区域排名
合伙人筛选
```

---

### 6.4 商家字段

| 字段 | 含义 |
| --- | --- |
| `merchant_id` | 商家 ID |
| `merchant_name` | 商家名称 |
| `shop_name` | 商户名称 / 店铺名称 |
| `user_id` | 下单用户 ID |

用于：

```text
商家名单
商户名称展示
商家型用户识别
订单来源分析
新商家分析
```

---

### 6.5 骑手字段

| 字段 | 含义 |
| --- | --- |
| `rider_id` | 骑手 ID |
| `rider_name` | 骑手姓名 |
| `employment_status` | 原始在职状态 |
| `employment_type` | 系统识别后的骑手类型，`fulltime` / `parttime` / 空 |

用于：

```text
骑手名单
骑手提成
新骑手分析
小时运力全职/兼职拆分
```

---

### 6.6 时间字段

| 字段 | 含义 |
| --- | --- |
| `create_time` | 下单时间 |
| `pay_time` | 支付时间 |
| `accept_time` | 接单时间 |
| `cancel_time` | 取消时间 |
| `complete_time` | 完成时间 |
| `order_date` | 订单日期，主统计日期 |
| `order_hour` | 下单小时 |
| `accept_hour` | 接单小时 |

用于：

```text
日趋势
小时热力图
接单骑手数
SLA 履约
取消时长计算
```

---

### 6.7 订单状态字段

| 字段 | 含义 |
| --- | --- |
| `order_status` | 原始订单状态 |
| `customer_service_id` | 客服 ID |
| `order_source` | 订单来源 |
| `is_paid` | 是否支付 |
| `is_completed` | 是否完成 |
| `is_cancelled` | 是否取消 |
| `pay_cancel_minutes` | 支付到取消的分钟数 |
| `order_elapsed_minutes_to_cancel` | 下单到取消的分钟数 |

---

### 6.8 核心口径字段

| 字段 | 含义 |
| --- | --- |
| `is_valid_order` | 是否有效订单 |
| `is_valid_cancel_order` | 是否有效取消订单 |
| `is_new_rider_order` | 是否新骑手订单 |
| `is_new_merchant_order` | 是否新商家订单 |
| `is_new_partner_order` | 是否新合伙人订单 |
| `service_online_flag` | 是否客服在线时段订单 |
| `is_timeout_cancel` | 是否超时取消 |
| `is_not_timeout_cancel` | 是否非超时取消 |
| `is_unaccepted_cancel` | 是否无人接取消 |
| `is_accepted_cancel` | 是否接单后取消 |
| `is_rider_noliability_cancel` | 是否骑手无责取消 |
| `has_coupon_order` | 是否券单 |
| `is_cross_day_order` | 是否跨天订单 |

核心口径：

```text
有效订单 = 完成订单 + 支付后取消且 pay_cancel_minutes > 阈值 的订单
```

当前默认阈值通常是：

```text
5 分钟
```

---

### 6.9 金额字段

| 字段 | 含义 |
| --- | --- |
| `order_price` | 订单价格 |
| `amount_payable` | 应付金额 |
| `amount_paid` | 实付金额 |
| `rider_income` | 骑手提成 |
| `partner_income` | 合伙人收入 |
| `coupon_id` | 优惠券 ID |
| `marketing_coupon_id` | 营销券 ID |
| `hq_discount_raw_amount` | 原始总部优惠金额 |
| `discount_raw_amount` | 原始优惠金额 |
| `hq_subsidy_amount` | 系统计算后的总部补贴 |
| `partner_subsidy_amount` | 系统计算后的合伙人补贴 |

用于：

```text
经营收益
骑手提成
补贴统计
经营利润
优惠金额分析
```

---

## 7. ADS 报表汇总层

ADS 是给网页和 Power BI 直接使用的汇总表。

```text
DWD = 一单一行
ADS = 按页面需要提前汇总好的结果
```

---

### 7.1 ADS 通用字段

多数 ADS 表都有这些字段：

| 字段 | 含义 |
| --- | --- |
| `metric_key` | 汇总行唯一键 |
| `order_month` | 订单月份 |
| `batch_id` | 数据重建批次 |
| `date` | 统计日期 |
| `partner_id` | 合伙人 ID |
| `partner_name` | 合伙人名称 |

---

### 7.2 `ads_admin_day_metrics`

全国/区域日汇总表。

粒度：

```text
某一天 + 某省/市/区县
```

字段：

| 字段 | 含义 |
| --- | --- |
| `date` | 日期 |
| `province` | 省 |
| `city` | 市 |
| `district` | 区县 |
| `total_orders` | 总订单 |
| `valid_orders` | 有效订单 |
| `completed_orders` | 完成订单 |
| `cancelled_orders` | 取消订单 |
| `completion_rate` | 完成率 |
| `active_partners` | 活跃合伙人数 |
| `new_partners` | 新合伙人数 |
| `active_merchants` | 活跃商家数 |
| `new_merchants` | 新商家数 |
| `active_riders` | 活跃骑手数 |
| `new_riders` | 新骑手数 |
| `hq_subsidy_total` | 总部补贴合计 |
| `partner_subsidy_total` | 合伙人补贴合计 |

用途：

```text
全国总览
全国趋势
区域趋势
```

---

### 7.3 `ads_admin_partner_metrics`

全国视角下的合伙人日汇总表。

粒度：

```text
某一天 + 某合伙人
```

字段：

| 字段 | 含义 |
| --- | --- |
| `partner_id` | 合伙人 ID |
| `partner_name` | 合伙人名称 |
| `province` | 省 |
| `city` | 市 |
| `district` | 区县 |
| `is_new_partner` | 是否新合伙人 |
| `total_orders` | 总订单 |
| `valid_orders` | 有效订单 |
| `completed_orders` | 完成订单 |
| `cancelled_orders` | 取消订单 |
| `completion_rate` | 完成率 |
| `active_merchants` | 活跃商家数 |
| `new_merchants` | 新商家数 |
| `active_riders` | 活跃骑手数 |
| `new_riders` | 新骑手数 |
| `hq_subsidy_total` | 总部补贴 |
| `partner_subsidy_total` | 合伙人补贴 |

用途：

```text
全国总览排名
区域排名
合伙人分层
新合伙人表现
诊断预警候选对象
```

---

### 7.4 `ads_partner_day_metrics`

单合伙人日经营汇总表。

粒度：

```text
某一天 + 某合伙人
```

字段：

| 字段 | 含义 |
| --- | --- |
| `partner_id` | 合伙人 ID |
| `partner_name` | 合伙人名称 |
| `date` | 日期 |
| `province` | 省 |
| `city` | 市 |
| `district` | 区县 |
| `total_orders` | 总订单 |
| `valid_orders` | 有效订单 |
| `completed_orders` | 完成订单 |
| `cancelled_orders` | 取消订单 |
| `completion_rate` | 完成率 |
| `cancel_rate` | 取消率 |
| `active_merchants` | 活跃商家数 |
| `new_merchants` | 新商家数 |
| `active_riders` | 活跃骑手数 |
| `new_riders` | 新骑手数 |
| `new_rider_orders` | 新骑手订单 |
| `old_rider_orders` | 老骑手订单 |
| `new_merchant_orders` | 新商家订单 |
| `old_merchant_orders` | 老商家订单 |
| `hq_subsidy_total` | 总部补贴 |
| `partner_subsidy_total` | 合伙人补贴 |

用途：

```text
城市经营
全国总览部分趋势
Power BI 主经营事实表
```

---

### 7.5 `ads_partner_hour_metrics`

合伙人小时汇总表。

粒度：

```text
某一天 + 某合伙人 + 某小时
```

当前模型字段：

| 字段 | 含义 |
| --- | --- |
| `partner_id` | 合伙人 ID |
| `date` | 日期 |
| `hour` | 小时 |
| `completed_orders` | 完成订单 |
| `cancelled_orders` | 取消订单 |
| `cancel_rate` | 取消率 |

说明：

```text
当前网页小时接口还会从 DWD 动态计算更多字段：
总订单、有效订单、接单骑手数、全职/兼职接单骑手数、人效、SLA 等。
如果 Power BI 需要这些字段，建议增加 pbi_partner_hourly 视图或扩展 ADS 表。
```

用途：

```text
时段热力与履约
小时趋势
小时取消率
```

---

### 7.6 `ads_partner_rider_day_metrics`

合伙人骑手日汇总表。

粒度：

```text
某一天 + 某合伙人 + 某骑手
```

字段：

| 字段 | 含义 |
| --- | --- |
| `partner_id` | 合伙人 ID |
| `rider_id` | 骑手 ID |
| `rider_name` | 骑手姓名 |
| `date` | 日期 |
| `completed_orders` | 完成订单 |
| `cancelled_orders` | 取消订单 |
| `is_new_rider` | 是否新骑手 |

用途：

```text
主体分析
骑手名单
骑手每天完成单量
骑手单量分层
新骑手分析
```

---

### 7.7 `ads_partner_merchant_day_metrics`

合伙人商家日汇总表。

粒度：

```text
某一天 + 某合伙人 + 某商家
```

字段：

| 字段 | 含义 |
| --- | --- |
| `partner_id` | 合伙人 ID |
| `merchant_id` | 商家 ID |
| `merchant_name` | 商家名称 |
| `date` | 日期 |
| `completed_orders` | 完成订单 |
| `cancelled_orders` | 取消订单 |
| `is_new_merchant` | 是否新商家 |
| `hq_subsidy_total` | 总部补贴 |
| `partner_subsidy_total` | 合伙人补贴 |

用途：

```text
主体分析
商家名单
新商家贡献
商家经营分析
```

---

### 7.8 `ads_partner_user_merchant_metrics`

用户-商家型识别汇总表。

粒度：

```text
某一天 + 某合伙人 + 某用户
```

字段：

| 字段 | 含义 |
| --- | --- |
| `partner_id` | 合伙人 ID |
| `user_id` | 用户 ID |
| `date` | 日期 |
| `total_orders` | 用户总订单 |
| `completed_orders` | 用户完成订单 |
| `cancelled_orders` | 用户取消订单 |

用途：

```text
主体分析里的用户主体识别
商家型用户识别
```

注意：

```text
商家型用户阈值只应该影响主体分析页的用户主体识别模块。
```

---

## 8. 直营专项 ADS 表

这些表是直营专项分析使用的汇总表。当前 `/direct` 不再作为正式主页面，但这些表仍可作为城市经营里的直营专项数据来源。

---

### 8.1 `ads_direct_cancel_day_metrics`

直营取消日指标表。

粒度：

```text
某一天 + 某合伙人
```

字段：

| 字段 | 含义 |
| --- | --- |
| `completed_orders` | 完成订单 |
| `valid_orders` | 有效订单 |
| `valid_cancel_orders` | 有效取消订单 |
| `valid_cancel_rate` | 有效取消率 |
| `unaccepted_timeout_online_cancel_orders` | 客服在线、超时、无人接取消 |
| `unaccepted_timeout_offline_cancel_orders` | 客服离线、超时、无人接取消 |
| `unaccepted_timeout_cancel_orders` | 超时无人接取消 |
| `unaccepted_not_timeout_cancel_orders` | 未超时无人接取消 |
| `unaccepted_cancel_orders` | 无人接取消 |
| `accepted_noliability_cancel_orders` | 接单后无责取消 |
| `unpaid_cancel_orders` | 未支付取消 |
| `total_orders` | 总订单 |
| `unaccepted_timeout_online_cancel_rate` | 客服在线超时无人接取消率 |

用途：

```text
直营取消分析
诊断取消问题
```

---

### 8.2 `ads_direct_hour_metrics`

直营小时指标表。

粒度：

```text
某一天 + 某合伙人 + 某小时
```

字段：

| 字段 | 含义 |
| --- | --- |
| `unpaid_orders` | 未支付订单 |
| `unaccepted_cancel_orders` | 无人接取消 |
| `accepted_cancel_orders` | 接单后取消 |
| `delivered_orders` | 送达/完成订单 |
| `total_orders` | 总订单 |
| `valid_orders` | 有效订单 |
| `valid_cancel_orders` | 有效取消订单 |
| `valid_cancel_rate` | 有效取消率 |
| `accepted_rider_count` | 接单骑手数 |
| `parttime_completed_orders` | 兼职完成订单 |
| `parttime_rider_count` | 兼职骑手数 |
| `fulltime_completed_orders` | 全职完成订单 |
| `fulltime_rider_count` | 全职骑手数 |
| `parttime_efficiency` | 兼职人效 |
| `fulltime_efficiency` | 全职人效 |

用途：

```text
直营小时运力
全职/兼职效率分析
```

---

### 8.3 `ads_direct_new_rider_metrics`

直营新骑手明细汇总。

粒度：

```text
某合伙人 + 某新骑手
```

字段：

| 字段 | 含义 |
| --- | --- |
| `rider_id` | 骑手 ID |
| `rider_name` | 骑手姓名 |
| `hire_date` | 入职日期 |
| `total_orders` | 总订单 |
| `completed_orders` | 完成订单 |

用途：

```text
直营新骑手表现
新骑手完成单量
```

---

### 8.4 `ads_direct_new_merchant_metrics`

直营新商家明细汇总。

粒度：

```text
某合伙人 + 某新商家
```

字段：

| 字段 | 含义 |
| --- | --- |
| `merchant_id` | 商家 ID |
| `merchant_name` | 商家名称 |
| `shop_name` | 商户名称 |
| `register_date` | 注册日期 |
| `total_orders` | 总订单 |
| `completed_orders` | 完成订单 |
| `completion_rate` | 完成率 |

用途：

```text
直营新商家表现
新商家贡献
```

---

### 8.5 `ads_direct_merchant_day_metrics`

直营商家日对比表。

粒度：

```text
某一天 + 某合伙人 + 某商家
```

字段：

| 字段 | 含义 |
| --- | --- |
| `merchant_id` | 商家 ID |
| `merchant_name` | 商家名称 |
| `shop_name` | 商户名称 |
| `date` | 日期 |
| `unaccepted_cancel_orders` | 无人接取消订单 |
| `unaccepted_cancel_amount_paid` | 无人接取消实付金额 |
| `accepted_cancel_orders` | 接单后取消订单 |
| `accepted_cancel_amount_paid` | 接单后取消实付金额 |
| `completed_orders` | 完成订单 |
| `completed_amount_paid` | 完成订单实付金额 |
| `total_orders` | 总订单 |
| `completion_rate` | 完成率 |
| `avg_amount_paid` | 平均实付金额 |

用途：

```text
直营商家对比
商家取消/完成表现
```

---

### 8.6 `ads_direct_order_source_day_metrics`

直营订单来源日指标表。

粒度：

```text
某一天 + 某合伙人 + 某订单来源
```

字段：

| 字段 | 含义 |
| --- | --- |
| `order_source` | 订单来源 |
| `date` | 日期 |
| `unpaid_orders` | 未支付订单 |
| `unaccepted_cancel_orders` | 无人接取消 |
| `accepted_cancel_orders` | 接单后取消 |
| `completed_orders` | 完成订单 |
| `total_orders` | 总订单 |

用途：

```text
订单来源对比
渠道质量分析
```

---

### 8.7 `ads_direct_coupon_metrics`

直营优惠券汇总表。

粒度：

```text
某一天 + 某合伙人 + 某优惠券
```

字段：

| 字段 | 含义 |
| --- | --- |
| `coupon_id` | 优惠券 ID |
| `marketing_coupon_id` | 营销券 ID |
| `coupon_order_count` | 券单数量 |
| `hq_discount_total` | 总部优惠合计 |
| `discount_total` | 普通优惠合计 |
| `total_discount` | 总优惠金额 |

用途：

```text
优惠金额统计
券单分析
补贴分析
```

---

## 9. Power BI 使用建议

### 9.1 优先读取 ADS

正式报表优先读：

```text
ads_partner_day_metrics
ads_partner_hour_metrics
ads_partner_rider_day_metrics
ads_partner_merchant_day_metrics
ads_admin_partner_metrics
```

原因：

```text
已经汇总好
加载快
口径稳定
不容易重复计算
```

---

### 9.2 必要时读取 DWD

这些场景再读 `dwd_order_detail`：

```text
订单来源分析
周期去重活跃骑手
周期去重活跃商家
商家型用户识别
明细排查
```

---

### 9.3 不建议直接读取 ODS

ODS 只用于：

```text
追溯原始数据
排查导入问题
重建 DWD / ADS
```

正式 Power BI 报表不建议直接读 ODS。

---

## 10. 数据问题排查路径

### 10.1 通用排查顺序

```text
页面数字不对
        ↓
先查 ADS，看汇总结果对不对
        ↓
ADS 不对，再查 DWD，看订单口径和匹配是否正确
        ↓
DWD 不对，再查 ODS，看原始字段是否导入错
        ↓
ODS 不对，再回原始 Excel / CSV
```

---

### 10.2 骑手姓名不对

排查顺序：

```text
dwd_order_detail.rider_id / rider_name
        ↓
rider_roster
        ↓
ods_order_detail_raw
        ↓
ods_rider_roster_raw
```

重点口径：

```text
帮手id = 骑手ID
帮手姓名 = 骑手姓名
```

---

### 10.3 商家名称不对

排查顺序：

```text
dwd_order_detail.merchant_id / merchant_name / shop_name
        ↓
merchant_roster
        ↓
ods_order_detail_raw
        ↓
ods_merchant_roster_raw
```

展示优先级建议：

```text
商户名称 / 店铺名称
商家名称
商家ID
```

---

### 10.4 完成订单不对

排查顺序：

```text
ads_partner_day_metrics.completed_orders
        ↓
dwd_order_detail.is_completed
        ↓
ods_order_detail_raw.order_status / complete_time
```

---

### 10.5 有效订单不对

排查顺序：

```text
ads_partner_day_metrics.valid_orders
        ↓
dwd_order_detail.is_valid_order
        ↓
dwd_order_detail.is_completed / is_cancelled / pay_cancel_minutes
        ↓
ods_order_detail_raw.pay_time / cancel_time
```

核心口径：

```text
有效订单 = 完成订单 + 支付后取消且 pay_cancel_minutes > 阈值 的订单
```

---

## 11. 一句话总结

```text
ODS：原始数据进来后先放这里，方便追溯。
DWD：把每一单清洗、匹配、计算好，是统一明细底座。
ADS：把 DWD 按页面需要提前汇总好，给网页和 Power BI 快速使用。
```

Power BI 最稳的使用方式：

```text
优先读 ADS
需要明细再读 DWD
不要直接读 ODS 做正式报表
```
