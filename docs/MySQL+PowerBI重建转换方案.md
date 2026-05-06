# MySQL + Power BI 重建转换方案

版本：v1.0  
适用场景：用 `订单明细表 + MySQL + Power BI` 重建当前同城配送经营分析看板  
目标读者：业务负责人、数据分析人员、初学者、后续实施工程师

---

## 1. 这份文档解决什么问题

当前系统是：

```text
原始订单 / 骑手 / 商家 / 合伙人表格
        ↓
Python 导入与清洗
        ↓
DuckDB 数据库
        ↓
FastAPI 接口
        ↓
网页看板
```

如果改成 `MySQL + Power BI`，推荐改成：

```text
原始订单 / 骑手 / 商家 / 合伙人表格
        ↓
导入 MySQL 原始层 ODS
        ↓
MySQL 清洗匹配成 DWD 标准订单明细
        ↓
MySQL 汇总成 ADS 指标表
        ↓
Power BI 连接 MySQL 展示 5 页报表
```

一句话理解：

- Excel / CSV 是原材料。
- MySQL 是仓库和加工车间。
- Power BI 是展示大屏。

不要让 Power BI 直接承担所有计算。更稳的方式是：

```text
MySQL 负责把数据算准
Power BI 负责把结果展示清楚
```

---

## 2. 为什么要分 ODS / DWD / ADS 三层

### 2.1 如果直接把订单明细导入 Power BI，会有什么问题

直接做也能出图，但后续容易出这些问题：

- 字段名可能变化，例如“配送员id”“骑手ID”“帮手id”含义相同但名字不同。
- 骑手姓名、商家名称可能需要从名单表补齐。
- 有效订单、新骑手、新商家、补贴、利润等口径容易每张图各算各的。
- 数据量变大后，Power BI 每次直接扫明细会变慢。
- 后续口径调整时，需要到很多页面里逐个修改 DAX 或图表设置。

### 2.2 三层结构的作用

| 层级 | 名称 | 作用 | 类比 |
| --- | --- | --- | --- |
| ODS | 原始数据层 | 尽量保留原始数据，方便追溯 | 原料仓库 |
| DWD | 标准明细层 | 清洗字段、匹配名称、统一订单口径 | 加工后的标准明细 |
| ADS | 应用汇总层 | 按页面需要提前汇总好指标 | 给报表直接用的成品 |

推荐数据流：

```text
ods_order_detail_raw
        ↓
dwd_order_detail
        ↓
ads_partner_day_metrics / ads_partner_hour_metrics / ads_rider_day_metrics / ads_merchant_day_metrics
        ↓
Power BI
```

---

## 3. 原始表准备

至少准备 4 类原始表。

### 3.1 订单明细表

订单明细表是一切指标的核心，一行代表一个订单。

建议至少包含：

| 字段 | 说明 |
| --- | --- |
| 订单ID | 每个订单唯一标识 |
| 下单时间 | 用户创建订单时间 |
| 支付时间 | 用户支付时间 |
| 接单时间 | 骑手接单时间 |
| 完成时间 | 订单完成时间 |
| 取消时间 | 订单取消时间 |
| 订单状态 | 用于判断完成、取消 |
| 合伙人ID | 订单所属合伙人 |
| 合伙人名称 | 订单所属合伙人名称 |
| 商家ID | 商家唯一标识 |
| 商家名称 | 商家名称 |
| 商户名称 / 店铺名称 | 优先用于展示的店铺名 |
| 骑手ID / 配送员ID | 骑手唯一标识 |
| 骑手姓名 / 配送员姓名 | 骑手姓名 |
| 订单来源 | 渠道来源 |
| 实付金额 | 用户实际支付金额 |
| 骑手提成 | 骑手收入/提成 |
| 合伙人收入 | 合伙人收入 |
| 总部补贴 | 总部补贴金额 |
| 合伙人补贴 | 合伙人补贴金额 |

### 3.2 骑手信息表 / 帮手信息表

当前口径：

```text
帮手id = 骑手ID
帮手姓名 = 骑手姓名
```

建议字段：

| 字段 | 说明 |
| --- | --- |
| 骑手ID / 帮手id | 与订单明细中的骑手ID匹配 |
| 骑手姓名 / 帮手姓名 | 页面展示名称 |
| 入职时间 / 注册时间 | 判断新骑手 |
| 在职状态 | 判断全职 / 兼职 |
| 所属区域 | 辅助分析 |

### 3.3 商家信息表 / 商户信息表

当前口径：

```text
商家ID = 商家ID
商户名称优先作为页面展示名称
```

建议字段：

| 字段 | 说明 |
| --- | --- |
| 商家ID | 与订单明细中的商家ID匹配 |
| 商家名称 | 备用展示名 |
| 商户名称 / 店铺名称 | 优先展示名 |
| 注册时间 | 判断新商家 |
| 商家状态 | 判断是否正常 |
| 所属合伙人 | 辅助匹配 |

### 3.4 合伙人信息表

建议字段：

| 字段 | 说明 |
| --- | --- |
| 合伙人ID | 与订单明细中的合伙人ID匹配 |
| 合伙人名称 | 页面展示名称 |
| 省 | 区域筛选 |
| 市 | 区域筛选 |
| 区县 | 区域筛选 |
| 开城时间 | 判断新合伙人 |
| 状态 | 是否正常运营 |

---

## 4. MySQL 数据库设计

### 4.1 建库

```sql
CREATE DATABASE IF NOT EXISTS delivery_analysis
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE delivery_analysis;
```

为什么用 `utf8mb4`：

- 支持中文。
- 支持特殊符号。
- 避免骑手姓名、商户名称乱码。

---

## 5. ODS 原始层建表

ODS 层建议尽量贴近原始表，但字段名要标准化。

### 5.1 原始订单明细表

```sql
CREATE TABLE IF NOT EXISTS ods_order_detail_raw (
  order_id              VARCHAR(64) PRIMARY KEY COMMENT '订单ID',
  order_month           CHAR(7) COMMENT '订单月份，例如 2026-03',
  partner_id            VARCHAR(64) COMMENT '合伙人ID',
  partner_name          VARCHAR(255) COMMENT '合伙人名称',
  merchant_id           VARCHAR(64) COMMENT '商家ID',
  merchant_name         VARCHAR(255) COMMENT '商家名称',
  shop_name             VARCHAR(255) COMMENT '商户名称/店铺名称',
  user_id               VARCHAR(64) COMMENT '用户ID',
  rider_id              VARCHAR(64) COMMENT '骑手ID/配送员ID',
  rider_name            VARCHAR(255) COMMENT '骑手姓名',
  employment_status     VARCHAR(64) COMMENT '在职状态',
  province              VARCHAR(64) COMMENT '省',
  city                  VARCHAR(64) COMMENT '市',
  district              VARCHAR(64) COMMENT '区县',
  order_status          VARCHAR(64) COMMENT '订单状态',
  customer_service_id   VARCHAR(64) COMMENT '客服ID',
  order_source          VARCHAR(128) COMMENT '订单来源',
  create_time           DATETIME COMMENT '下单时间',
  pay_time              DATETIME COMMENT '支付时间',
  accept_time           DATETIME COMMENT '接单时间',
  cancel_time           DATETIME COMMENT '取消时间',
  complete_time         DATETIME COMMENT '完成时间',
  order_price           DECIMAL(12,2) DEFAULT 0 COMMENT '订单价格',
  amount_payable        DECIMAL(12,2) DEFAULT 0 COMMENT '应付金额',
  amount_paid           DECIMAL(12,2) DEFAULT 0 COMMENT '实付金额',
  rider_income          DECIMAL(12,2) DEFAULT 0 COMMENT '骑手提成',
  partner_income        DECIMAL(12,2) DEFAULT 0 COMMENT '合伙人收入',
  hq_subsidy_amount     DECIMAL(12,2) DEFAULT 0 COMMENT '总部补贴',
  partner_subsidy_amount DECIMAL(12,2) DEFAULT 0 COMMENT '合伙人补贴',
  coupon_id             VARCHAR(128) COMMENT '优惠券ID',
  marketing_coupon_id   VARCHAR(128) COMMENT '营销券ID',
  imported_at           DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '导入时间',
  INDEX idx_ods_order_month (order_month),
  INDEX idx_ods_partner_date (partner_id, create_time),
  INDEX idx_ods_rider (rider_id),
  INDEX idx_ods_merchant (merchant_id)
) COMMENT='ODS 原始订单明细表';
```

### 5.2 骑手名单表

```sql
CREATE TABLE IF NOT EXISTS rider_roster (
  rider_id       VARCHAR(64) PRIMARY KEY COMMENT '骑手ID/帮手id',
  rider_name     VARCHAR(255) COMMENT '骑手姓名/帮手姓名',
  hire_date      DATE COMMENT '入职/注册日期',
  status         VARCHAR(64) COMMENT '状态',
  partner_name   VARCHAR(255) COMMENT '所属合伙人',
  region         VARCHAR(255) COMMENT '所属区域',
  updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_rider_name (rider_name)
) COMMENT='标准骑手名单';
```

### 5.3 商家名单表

```sql
CREATE TABLE IF NOT EXISTS merchant_roster (
  merchant_id     VARCHAR(64) PRIMARY KEY COMMENT '商家ID',
  merchant_name   VARCHAR(255) COMMENT '商家名称',
  shop_name       VARCHAR(255) COMMENT '商户名称/店铺名称',
  partner_name    VARCHAR(255) COMMENT '所属合伙人',
  region          VARCHAR(255) COMMENT '所属区域',
  register_date   DATE COMMENT '注册日期',
  status          VARCHAR(64) COMMENT '状态',
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_merchant_name (merchant_name),
  INDEX idx_shop_name (shop_name)
) COMMENT='标准商家名单';
```

### 5.4 合伙人名单表

```sql
CREATE TABLE IF NOT EXISTS partner_roster (
  partner_id     VARCHAR(64) PRIMARY KEY COMMENT '合伙人ID',
  partner_name   VARCHAR(255) COMMENT '合伙人名称',
  open_date      DATE COMMENT '开城日期',
  province       VARCHAR(64) COMMENT '省',
  city           VARCHAR(64) COMMENT '市',
  district       VARCHAR(64) COMMENT '区县',
  status         VARCHAR(64) COMMENT '状态',
  updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_partner_region (province, city, district)
) COMMENT='标准合伙人名单';
```

---

## 6. 导入原始数据到 MySQL

### 6.1 小白推荐方式

如果你不会写程序，先用数据库工具导入：

- Navicat
- DBeaver
- MySQL Workbench

流程：

```text
打开 MySQL 工具
  ↓
连接数据库 delivery_analysis
  ↓
选择目标表
  ↓
导入 Excel / CSV
  ↓
手动映射字段
  ↓
确认行数
```

### 6.2 导入后必须检查

每次导入后先查行数：

```sql
SELECT COUNT(*) AS order_rows FROM ods_order_detail_raw;
SELECT COUNT(*) AS rider_rows FROM rider_roster;
SELECT COUNT(*) AS merchant_rows FROM merchant_roster;
SELECT COUNT(*) AS partner_rows FROM partner_roster;
```

再查关键 ID 是否存在：

```sql
SELECT *
FROM rider_roster
WHERE rider_id IN ('71640', '88326');

SELECT *
FROM ods_order_detail_raw
WHERE rider_id IN ('71640', '88326');
```

为什么要检查：

- 避免把用户 ID 当骑手 ID。
- 避免骑手姓名、商户名称匹配错。
- 避免导入时 Excel 把 ID 当数字导致前导 0 丢失。

---

## 7. DWD 标准订单明细表

DWD 是最关键的一张表，Power BI 和后续 ADS 都应以它为准。

### 7.1 DWD 建表

```sql
CREATE TABLE IF NOT EXISTS dwd_order_detail (
  order_id              VARCHAR(64) PRIMARY KEY,
  order_month           CHAR(7),
  partner_id            VARCHAR(64),
  partner_name          VARCHAR(255),
  merchant_id           VARCHAR(64),
  merchant_name         VARCHAR(255),
  shop_name             VARCHAR(255),
  user_id               VARCHAR(64),
  rider_id              VARCHAR(64),
  rider_name            VARCHAR(255),
  employment_status     VARCHAR(64),
  employment_type       VARCHAR(32),
  province              VARCHAR(64),
  city                  VARCHAR(64),
  district              VARCHAR(64),
  order_status          VARCHAR(64),
  customer_service_id   VARCHAR(64),
  order_source          VARCHAR(128),
  create_time           DATETIME,
  pay_time              DATETIME,
  accept_time           DATETIME,
  cancel_time           DATETIME,
  complete_time         DATETIME,
  order_date            DATE,
  order_hour            INT,
  accept_hour           INT,
  is_paid               TINYINT DEFAULT 0,
  is_completed          TINYINT DEFAULT 0,
  is_cancelled          TINYINT DEFAULT 0,
  pay_cancel_minutes    DECIMAL(12,4),
  is_valid_order        TINYINT DEFAULT 0,
  is_valid_cancel_order TINYINT DEFAULT 0,
  is_new_rider_order    TINYINT DEFAULT 0,
  is_new_merchant_order TINYINT DEFAULT 0,
  is_new_partner_order  TINYINT DEFAULT 0,
  has_coupon_order      TINYINT DEFAULT 0,
  order_price           DECIMAL(12,2) DEFAULT 0,
  amount_payable        DECIMAL(12,2) DEFAULT 0,
  amount_paid           DECIMAL(12,2) DEFAULT 0,
  rider_income          DECIMAL(12,2) DEFAULT 0,
  partner_income        DECIMAL(12,2) DEFAULT 0,
  hq_subsidy_amount     DECIMAL(12,2) DEFAULT 0,
  partner_subsidy_amount DECIMAL(12,2) DEFAULT 0,
  INDEX idx_dwd_date (order_date),
  INDEX idx_dwd_partner_date (partner_id, order_date),
  INDEX idx_dwd_rider_date (rider_id, order_date),
  INDEX idx_dwd_merchant_date (merchant_id, order_date),
  INDEX idx_dwd_region (province, city, district)
) COMMENT='DWD 标准订单明细宽表';
```

### 7.2 DWD 重建 SQL

下面示例假设有效取消阈值是 `5 分钟`，新骑手/新商家窗口是 `30 天`。

```sql
TRUNCATE TABLE dwd_order_detail;

INSERT INTO dwd_order_detail (
  order_id,
  order_month,
  partner_id,
  partner_name,
  merchant_id,
  merchant_name,
  shop_name,
  user_id,
  rider_id,
  rider_name,
  employment_status,
  employment_type,
  province,
  city,
  district,
  order_status,
  customer_service_id,
  order_source,
  create_time,
  pay_time,
  accept_time,
  cancel_time,
  complete_time,
  order_date,
  order_hour,
  accept_hour,
  is_paid,
  is_completed,
  is_cancelled,
  pay_cancel_minutes,
  is_valid_order,
  is_valid_cancel_order,
  is_new_rider_order,
  is_new_merchant_order,
  is_new_partner_order,
  has_coupon_order,
  order_price,
  amount_payable,
  amount_paid,
  rider_income,
  partner_income,
  hq_subsidy_amount,
  partner_subsidy_amount
)
SELECT
  o.order_id,
  DATE_FORMAT(COALESCE(o.create_time, o.pay_time, o.complete_time), '%Y-%m') AS order_month,
  o.partner_id,
  COALESCE(p.partner_name, o.partner_name, o.partner_id) AS partner_name,
  o.merchant_id,
  COALESCE(m.merchant_name, o.merchant_name, o.merchant_id) AS merchant_name,
  COALESCE(m.shop_name, o.shop_name, m.merchant_name, o.merchant_name, o.merchant_id) AS shop_name,
  o.user_id,
  o.rider_id,
  COALESCE(r.rider_name, o.rider_name, o.rider_id) AS rider_name,
  COALESCE(o.employment_status, r.status) AS employment_status,
  CASE
    WHEN COALESCE(o.employment_status, r.status) LIKE '%全职%' THEN 'fulltime'
    WHEN COALESCE(o.employment_status, r.status) LIKE '%兼职%' THEN 'parttime'
    ELSE NULL
  END AS employment_type,
  COALESCE(p.province, o.province) AS province,
  COALESCE(p.city, o.city) AS city,
  COALESCE(p.district, o.district) AS district,
  o.order_status,
  o.customer_service_id,
  COALESCE(NULLIF(o.order_source, ''), '未知') AS order_source,
  o.create_time,
  o.pay_time,
  o.accept_time,
  o.cancel_time,
  o.complete_time,
  DATE(COALESCE(o.create_time, o.pay_time, o.complete_time, o.cancel_time)) AS order_date,
  HOUR(o.create_time) AS order_hour,
  HOUR(o.accept_time) AS accept_hour,
  CASE WHEN o.pay_time IS NOT NULL THEN 1 ELSE 0 END AS is_paid,
  CASE
    WHEN o.complete_time IS NOT NULL THEN 1
    WHEN o.order_status LIKE '%完成%' THEN 1
    ELSE 0
  END AS is_completed,
  CASE
    WHEN o.cancel_time IS NOT NULL THEN 1
    WHEN o.order_status LIKE '%取消%' THEN 1
    ELSE 0
  END AS is_cancelled,
  CASE
    WHEN o.pay_time IS NOT NULL AND o.cancel_time IS NOT NULL
    THEN TIMESTAMPDIFF(SECOND, o.pay_time, o.cancel_time) / 60.0
    ELSE NULL
  END AS pay_cancel_minutes,
  CASE
    WHEN o.complete_time IS NOT NULL OR o.order_status LIKE '%完成%' THEN 1
    WHEN o.pay_time IS NOT NULL
      AND o.cancel_time IS NOT NULL
      AND TIMESTAMPDIFF(SECOND, o.pay_time, o.cancel_time) / 60.0 > 5
    THEN 1
    ELSE 0
  END AS is_valid_order,
  CASE
    WHEN (o.cancel_time IS NOT NULL OR o.order_status LIKE '%取消%')
      AND o.pay_time IS NOT NULL
      AND o.cancel_time IS NOT NULL
      AND TIMESTAMPDIFF(SECOND, o.pay_time, o.cancel_time) / 60.0 > 5
    THEN 1
    ELSE 0
  END AS is_valid_cancel_order,
  CASE
    WHEN r.hire_date IS NOT NULL
      AND DATE(COALESCE(o.create_time, o.pay_time, o.complete_time, o.cancel_time)) BETWEEN r.hire_date AND DATE_ADD(r.hire_date, INTERVAL 30 DAY)
    THEN 1 ELSE 0
  END AS is_new_rider_order,
  CASE
    WHEN m.register_date IS NOT NULL
      AND DATE(COALESCE(o.create_time, o.pay_time, o.complete_time, o.cancel_time)) BETWEEN m.register_date AND DATE_ADD(m.register_date, INTERVAL 30 DAY)
    THEN 1 ELSE 0
  END AS is_new_merchant_order,
  CASE
    WHEN p.open_date IS NOT NULL
      AND DATE(COALESCE(o.create_time, o.pay_time, o.complete_time, o.cancel_time)) BETWEEN p.open_date AND DATE_ADD(p.open_date, INTERVAL 30 DAY)
    THEN 1 ELSE 0
  END AS is_new_partner_order,
  CASE
    WHEN COALESCE(o.coupon_id, '') <> '' OR COALESCE(o.marketing_coupon_id, '') <> '' THEN 1
    ELSE 0
  END AS has_coupon_order,
  COALESCE(o.order_price, 0),
  COALESCE(o.amount_payable, 0),
  COALESCE(o.amount_paid, 0),
  COALESCE(o.rider_income, 0),
  COALESCE(o.partner_income, 0),
  COALESCE(o.hq_subsidy_amount, 0),
  COALESCE(o.partner_subsidy_amount, 0)
FROM ods_order_detail_raw o
LEFT JOIN rider_roster r ON r.rider_id = o.rider_id
LEFT JOIN merchant_roster m ON m.merchant_id = o.merchant_id
LEFT JOIN partner_roster p ON p.partner_id = o.partner_id
WHERE o.order_id IS NOT NULL
  AND TRIM(o.order_id) <> '';
```

---

## 8. 核心指标口径

### 8.1 主指标

| 指标 | 计算规则 |
| --- | --- |
| 总订单 | `COUNT(*)` |
| 完成订单 | `SUM(is_completed)` |
| 取消订单 | `SUM(is_cancelled)` |
| 有效订单 | `SUM(is_valid_order)` |
| 有效取消订单 | `SUM(is_valid_cancel_order)` |
| 完成率 | `完成订单 / 总订单` |
| 有效订单完成率 | `完成订单 / 有效订单` |
| 取消率 | `取消订单 / 总订单` |
| 活跃骑手数 | 完成订单中的骑手 ID 去重数 |
| 新骑手数 | 完成订单且 `is_new_rider_order = 1` 的骑手 ID 去重数 |
| 活跃商家数 | 完成订单中的商家 ID 去重数 |
| 新商家数 | 完成订单且 `is_new_merchant_order = 1` 的商家 ID 去重数 |
| 总部补贴 | `SUM(hq_subsidy_amount)` |
| 合伙人补贴 | `SUM(partner_subsidy_amount)` |
| 骑手提成 | 完成订单的 `SUM(rider_income)` |
| 经营利润 | 合伙人收入总额 - 合伙人补贴总额 |

### 8.2 有效订单口径

```text
有效订单 = 完成订单 + 有效取消订单
```

有效取消订单：

```text
订单已取消
并且订单已支付
并且支付时间到取消时间 > 有效取消阈值
```

当前默认阈值：

```text
5 分钟
```

注意：

- 正好 5 分钟不算有效取消。
- 未支付取消不算有效订单。
- 如果后续业务改阈值，只需要重算 DWD / ADS。

### 8.3 新骑手 / 新商家

```text
新骑手订单 = 订单日期 - 骑手入职日期 在 0 到 30 天内
新商家订单 = 订单日期 - 商家注册日期 在 0 到 30 天内
```

### 8.4 小时运力

| 指标 | 计算规则 |
| --- | --- |
| 接单骑手数 | 按 `accept_hour` 对骑手 ID 去重 |
| 全职接单骑手数 | `employment_type = fulltime` 且按 `accept_hour` 去重 |
| 兼职接单骑手数 | `employment_type = parttime` 且按 `accept_hour` 去重 |
| 人效 | 完成订单 / 接单骑手数 |
| 全职人效 | 全职完成订单 / 全职接单骑手数 |
| 兼职人效 | 兼职完成订单 / 兼职接单骑手数 |

---

## 9. ADS 汇总表

### 9.1 合伙人日汇总表

```sql
CREATE TABLE IF NOT EXISTS ads_partner_day_metrics (
  metric_key             VARCHAR(200) PRIMARY KEY,
  order_month            CHAR(7),
  partner_id             VARCHAR(64),
  partner_name           VARCHAR(255),
  date                   DATE,
  province               VARCHAR(64),
  city                   VARCHAR(64),
  district               VARCHAR(64),
  total_orders           INT DEFAULT 0,
  valid_orders           INT DEFAULT 0,
  completed_orders       INT DEFAULT 0,
  cancelled_orders       INT DEFAULT 0,
  completion_rate        DECIMAL(12,4) DEFAULT 0,
  cancel_rate            DECIMAL(12,4) DEFAULT 0,
  active_riders          INT DEFAULT 0,
  new_riders             INT DEFAULT 0,
  active_merchants       INT DEFAULT 0,
  new_merchants          INT DEFAULT 0,
  hq_subsidy_total       DECIMAL(12,2) DEFAULT 0,
  partner_subsidy_total  DECIMAL(12,2) DEFAULT 0,
  rider_commission_total DECIMAL(12,2) DEFAULT 0,
  partner_income_total   DECIMAL(12,2) DEFAULT 0,
  business_profit        DECIMAL(12,2) DEFAULT 0,
  INDEX idx_ads_partner_day (partner_id, date),
  INDEX idx_ads_region_day (province, city, district, date)
) COMMENT='合伙人日经营指标';
```

```sql
TRUNCATE TABLE ads_partner_day_metrics;

INSERT INTO ads_partner_day_metrics (
  metric_key,
  order_month,
  partner_id,
  partner_name,
  date,
  province,
  city,
  district,
  total_orders,
  valid_orders,
  completed_orders,
  cancelled_orders,
  completion_rate,
  cancel_rate,
  active_riders,
  new_riders,
  active_merchants,
  new_merchants,
  hq_subsidy_total,
  partner_subsidy_total,
  rider_commission_total,
  partner_income_total,
  business_profit
)
SELECT
  CONCAT('partner_day|', COALESCE(partner_id, 'UNKNOWN'), '|', order_date),
  DATE_FORMAT(order_date, '%Y-%m'),
  COALESCE(partner_id, 'UNKNOWN'),
  MAX(partner_name),
  order_date,
  MAX(province),
  MAX(city),
  MAX(district),
  COUNT(*),
  SUM(is_valid_order),
  SUM(is_completed),
  SUM(is_cancelled),
  ROUND(SUM(is_completed) / NULLIF(COUNT(*), 0), 4),
  ROUND(SUM(is_cancelled) / NULLIF(COUNT(*), 0), 4),
  COUNT(DISTINCT CASE WHEN is_completed = 1 THEN rider_id END),
  COUNT(DISTINCT CASE WHEN is_completed = 1 AND is_new_rider_order = 1 THEN rider_id END),
  COUNT(DISTINCT CASE WHEN is_completed = 1 THEN merchant_id END),
  COUNT(DISTINCT CASE WHEN is_completed = 1 AND is_new_merchant_order = 1 THEN merchant_id END),
  ROUND(SUM(hq_subsidy_amount), 2),
  ROUND(SUM(partner_subsidy_amount), 2),
  ROUND(SUM(CASE WHEN is_completed = 1 THEN rider_income ELSE 0 END), 2),
  ROUND(SUM(CASE WHEN is_completed = 1 THEN partner_income ELSE 0 END), 2),
  ROUND(
    SUM(CASE WHEN is_completed = 1 THEN partner_income ELSE 0 END)
    - SUM(partner_subsidy_amount),
    2
  )
FROM dwd_order_detail
WHERE order_date IS NOT NULL
GROUP BY COALESCE(partner_id, 'UNKNOWN'), order_date;
```

### 9.2 合伙人小时汇总表

```sql
CREATE TABLE IF NOT EXISTS ads_partner_hour_metrics (
  metric_key                         VARCHAR(220) PRIMARY KEY,
  order_month                        CHAR(7),
  partner_id                         VARCHAR(64),
  partner_name                       VARCHAR(255),
  date                               DATE,
  hour                               INT,
  total_orders                       INT DEFAULT 0,
  completed_orders                   INT DEFAULT 0,
  cancelled_orders                   INT DEFAULT 0,
  valid_orders                       INT DEFAULT 0,
  accepted_rider_count               INT DEFAULT 0,
  fulltime_accepted_rider_count      INT DEFAULT 0,
  parttime_accepted_rider_count      INT DEFAULT 0,
  fulltime_completed_orders          INT DEFAULT 0,
  parttime_completed_orders          INT DEFAULT 0,
  efficiency                         DECIMAL(12,4) DEFAULT 0,
  fulltime_efficiency                DECIMAL(12,4) DEFAULT 0,
  parttime_efficiency                DECIMAL(12,4) DEFAULT 0,
  INDEX idx_ads_partner_hour (partner_id, date, hour)
) COMMENT='合伙人小时运力指标';
```

```sql
TRUNCATE TABLE ads_partner_hour_metrics;

INSERT INTO ads_partner_hour_metrics (
  metric_key,
  order_month,
  partner_id,
  partner_name,
  date,
  hour,
  total_orders,
  completed_orders,
  cancelled_orders,
  valid_orders,
  accepted_rider_count,
  fulltime_accepted_rider_count,
  parttime_accepted_rider_count,
  fulltime_completed_orders,
  parttime_completed_orders,
  efficiency,
  fulltime_efficiency,
  parttime_efficiency
)
SELECT
  CONCAT('partner_hour|', COALESCE(o.partner_id, 'UNKNOWN'), '|', o.order_date, '|', o.order_hour),
  DATE_FORMAT(o.order_date, '%Y-%m'),
  COALESCE(o.partner_id, 'UNKNOWN'),
  MAX(o.partner_name),
  o.order_date,
  o.order_hour,
  COUNT(*),
  SUM(o.is_completed),
  SUM(o.is_cancelled),
  SUM(o.is_valid_order),
  COALESCE(a.accepted_rider_count, 0),
  COALESCE(a.fulltime_accepted_rider_count, 0),
  COALESCE(a.parttime_accepted_rider_count, 0),
  SUM(CASE WHEN o.is_completed = 1 AND o.employment_type = 'fulltime' THEN 1 ELSE 0 END),
  SUM(CASE WHEN o.is_completed = 1 AND o.employment_type = 'parttime' THEN 1 ELSE 0 END),
  ROUND(SUM(o.is_completed) / NULLIF(COALESCE(a.accepted_rider_count, 0), 0), 4),
  ROUND(SUM(CASE WHEN o.is_completed = 1 AND o.employment_type = 'fulltime' THEN 1 ELSE 0 END) / NULLIF(COALESCE(a.fulltime_accepted_rider_count, 0), 0), 4),
  ROUND(SUM(CASE WHEN o.is_completed = 1 AND o.employment_type = 'parttime' THEN 1 ELSE 0 END) / NULLIF(COALESCE(a.parttime_accepted_rider_count, 0), 0), 4)
FROM dwd_order_detail o
LEFT JOIN (
  SELECT
    partner_id,
    order_date,
    accept_hour,
    COUNT(DISTINCT rider_id) AS accepted_rider_count,
    COUNT(DISTINCT CASE WHEN employment_type = 'fulltime' THEN rider_id END) AS fulltime_accepted_rider_count,
    COUNT(DISTINCT CASE WHEN employment_type = 'parttime' THEN rider_id END) AS parttime_accepted_rider_count
  FROM dwd_order_detail
  WHERE accept_hour IS NOT NULL
    AND rider_id IS NOT NULL
  GROUP BY partner_id, order_date, accept_hour
) a
  ON a.partner_id = o.partner_id
 AND a.order_date = o.order_date
 AND a.accept_hour = o.order_hour
WHERE o.order_date IS NOT NULL
  AND o.order_hour IS NOT NULL
GROUP BY o.partner_id, o.order_date, o.order_hour, a.accepted_rider_count, a.fulltime_accepted_rider_count, a.parttime_accepted_rider_count;
```

### 9.3 骑手日汇总表

```sql
CREATE TABLE IF NOT EXISTS ads_rider_day_metrics (
  metric_key             VARCHAR(220) PRIMARY KEY,
  order_month            CHAR(7),
  partner_id             VARCHAR(64),
  partner_name           VARCHAR(255),
  rider_id               VARCHAR(64),
  rider_name             VARCHAR(255),
  date                   DATE,
  completed_orders       INT DEFAULT 0,
  total_orders           INT DEFAULT 0,
  cancelled_orders       INT DEFAULT 0,
  rider_commission_total DECIMAL(12,2) DEFAULT 0,
  is_new_rider           TINYINT DEFAULT 0,
  INDEX idx_ads_rider_day (partner_id, rider_id, date)
) COMMENT='骑手日指标';
```

```sql
TRUNCATE TABLE ads_rider_day_metrics;

INSERT INTO ads_rider_day_metrics
SELECT
  CONCAT('rider_day|', COALESCE(partner_id, 'UNKNOWN'), '|', COALESCE(rider_id, 'UNKNOWN'), '|', order_date),
  DATE_FORMAT(order_date, '%Y-%m'),
  COALESCE(partner_id, 'UNKNOWN'),
  MAX(partner_name),
  COALESCE(rider_id, 'UNKNOWN'),
  MAX(rider_name),
  order_date,
  SUM(is_completed),
  COUNT(*),
  SUM(is_cancelled),
  ROUND(SUM(CASE WHEN is_completed = 1 THEN rider_income ELSE 0 END), 2),
  MAX(is_new_rider_order)
FROM dwd_order_detail
WHERE order_date IS NOT NULL
  AND rider_id IS NOT NULL
GROUP BY partner_id, rider_id, order_date;
```

### 9.4 商家日汇总表

```sql
CREATE TABLE IF NOT EXISTS ads_merchant_day_metrics (
  metric_key        VARCHAR(220) PRIMARY KEY,
  order_month       CHAR(7),
  partner_id        VARCHAR(64),
  partner_name      VARCHAR(255),
  merchant_id       VARCHAR(64),
  merchant_name     VARCHAR(255),
  shop_name         VARCHAR(255),
  date              DATE,
  completed_orders  INT DEFAULT 0,
  total_orders      INT DEFAULT 0,
  cancelled_orders  INT DEFAULT 0,
  is_new_merchant   TINYINT DEFAULT 0,
  INDEX idx_ads_merchant_day (partner_id, merchant_id, date)
) COMMENT='商家日指标';
```

```sql
TRUNCATE TABLE ads_merchant_day_metrics;

INSERT INTO ads_merchant_day_metrics
SELECT
  CONCAT('merchant_day|', COALESCE(partner_id, 'UNKNOWN'), '|', COALESCE(merchant_id, 'UNKNOWN'), '|', order_date),
  DATE_FORMAT(order_date, '%Y-%m'),
  COALESCE(partner_id, 'UNKNOWN'),
  MAX(partner_name),
  COALESCE(merchant_id, 'UNKNOWN'),
  MAX(merchant_name),
  MAX(shop_name),
  order_date,
  SUM(is_completed),
  COUNT(*),
  SUM(is_cancelled),
  MAX(is_new_merchant_order)
FROM dwd_order_detail
WHERE order_date IS NOT NULL
  AND merchant_id IS NOT NULL
GROUP BY partner_id, merchant_id, order_date;
```

---

## 10. Power BI 数据模型设计

### 10.1 推荐导入哪些表

Power BI 首版建议连接这些表：

```text
partner_roster
rider_roster
merchant_roster
dwd_order_detail
ads_partner_day_metrics
ads_partner_hour_metrics
ads_rider_day_metrics
ads_merchant_day_metrics
```

### 10.2 关系模型

推荐关系：

| 从表 | 字段 | 到表 | 字段 | 关系 |
| --- | --- | --- | --- | --- |
| ads_partner_day_metrics | partner_id | partner_roster | partner_id | 多对一 |
| ads_partner_hour_metrics | partner_id | partner_roster | partner_id | 多对一 |
| ads_rider_day_metrics | rider_id | rider_roster | rider_id | 多对一 |
| ads_merchant_day_metrics | merchant_id | merchant_roster | merchant_id | 多对一 |
| dwd_order_detail | partner_id | partner_roster | partner_id | 多对一 |
| dwd_order_detail | rider_id | rider_roster | rider_id | 多对一 |
| dwd_order_detail | merchant_id | merchant_roster | merchant_id | 多对一 |

建议再建一个日期表：

```DAX
日期表 =
CALENDAR(
    MIN(dwd_order_detail[order_date]),
    MAX(dwd_order_detail[order_date])
)
```

然后把日期表关联到各指标表的 `date` 或 `order_date`。

### 10.3 为什么要建日期表

日期表可以统一：

- 年月筛选
- 最近 7 天
- 最近 30 天
- 周趋势
- 月趋势
- 环比/同比

---

## 11. Power BI 常用 DAX 度量值

如果直接基于 `ads_partner_day_metrics` 做全国总览和城市经营，可以这样建度量值：

```DAX
总订单 =
SUM(ads_partner_day_metrics[total_orders])
```

```DAX
有效订单 =
SUM(ads_partner_day_metrics[valid_orders])
```

```DAX
完成订单 =
SUM(ads_partner_day_metrics[completed_orders])
```

```DAX
取消订单 =
SUM(ads_partner_day_metrics[cancelled_orders])
```

```DAX
完成率 =
DIVIDE([完成订单], [总订单])
```

```DAX
有效订单完成率 =
DIVIDE([完成订单], [有效订单])
```

```DAX
取消率 =
DIVIDE([取消订单], [总订单])
```

```DAX
活跃骑手数 =
SUM(ads_partner_day_metrics[active_riders])
```

注意：如果按多天汇总，`active_riders` 直接相加可能会重复计算同一个骑手。  
如果你需要“某段时间内去重活跃骑手数”，建议用 DWD 明细算：

```DAX
周期活跃骑手数 =
CALCULATE(
    DISTINCTCOUNT(dwd_order_detail[rider_id]),
    dwd_order_detail[is_completed] = 1
)
```

```DAX
周期活跃商家数 =
CALCULATE(
    DISTINCTCOUNT(dwd_order_detail[merchant_id]),
    dwd_order_detail[is_completed] = 1
)
```

```DAX
骑手提成 =
SUM(ads_partner_day_metrics[rider_commission_total])
```

```DAX
经营利润 =
SUM(ads_partner_day_metrics[partner_income_total])
-
SUM(ads_partner_day_metrics[partner_subsidy_total])
```

小时运力：

```DAX
接单骑手数 =
SUM(ads_partner_hour_metrics[accepted_rider_count])
```

```DAX
全职接单骑手数 =
SUM(ads_partner_hour_metrics[fulltime_accepted_rider_count])
```

```DAX
兼职接单骑手数 =
SUM(ads_partner_hour_metrics[parttime_accepted_rider_count])
```

```DAX
人效 =
DIVIDE(
    SUM(ads_partner_hour_metrics[completed_orders]),
    SUM(ads_partner_hour_metrics[accepted_rider_count])
)
```

```DAX
全职人效 =
DIVIDE(
    SUM(ads_partner_hour_metrics[fulltime_completed_orders]),
    SUM(ads_partner_hour_metrics[fulltime_accepted_rider_count])
)
```

```DAX
兼职人效 =
DIVIDE(
    SUM(ads_partner_hour_metrics[parttime_completed_orders]),
    SUM(ads_partner_hour_metrics[parttime_accepted_rider_count])
)
```

---

## 12. 5 页 Power BI 报表设计

### 12.1 全国总览

数据来源：

```text
ads_partner_day_metrics
partner_roster
日期表
```

建议视觉对象：

- KPI 卡片：总订单、有效订单、完成订单、取消订单、完成率、活跃骑手、活跃商家、总部补贴、合伙人补贴。
- 折线图：日期维度下的总订单、有效订单、完成订单。
- 矩阵/表格：省、市、区县、合伙人排名。
- 分层表：加盟商日均单量分层。

筛选器：

- 日期
- 省
- 市
- 区县
- 合伙人

### 12.2 城市经营

数据来源：

```text
ads_partner_day_metrics
dwd_order_detail
partner_roster
```

建议视觉对象：

- 经营摘要卡片。
- 收益趋势：合伙人收入、合伙人补贴、经营利润。
- 日单量趋势。
- 有效订单 / 完成订单 / 取消订单对比。

说明：

- 城市经营页只看一个合伙人或少数合伙人的整体经营情况。
- 不建议在这一页深铺骑手名单、商家名单、主体识别。

### 12.3 时段热力与履约

数据来源：

```text
ads_partner_hour_metrics
dwd_order_detail
```

建议视觉对象：

- 小时订单折线图。
- 小时接单骑手数折线图。
- 全职 / 兼职接单骑手数对比。
- 人效、全职人效、兼职人效。
- 小时 x 日期热力矩阵。

矩阵示例：

```text
行：日期
列：小时
值：完成订单 / 取消订单 / 取消率
```

### 12.4 主体分析

数据来源：

```text
ads_rider_day_metrics
ads_merchant_day_metrics
dwd_order_detail
rider_roster
merchant_roster
```

建议视觉对象：

- 订单来源分析。
- 商家名单。
- 骑手名单。
- 骑手单量分层。
- 骑手提成明细。
- 新骑手 / 新商家趋势。
- 商家型用户识别。

商家型用户建议在 Power BI 里用参数或切片器实现阈值：

```text
商家型用户阈值默认 20 单
只影响主体分析页
不影响全国总览、城市经营、时段热力、诊断预警
```

### 12.5 诊断预警

数据来源：

```text
ads_partner_day_metrics
dwd_order_detail
```

建议视觉对象：

- 关注合伙人。
- 风险合伙人。
- 波动预警。
- 健康度评分。
- 问题清单。

波动预警示例：

```text
当前周期完成订单
对比基线周期完成订单
变化量
变化率
```

---

## 13. Power BI 筛选规则

建议所有页面统一保留：

- 日期筛选。
- 省 / 市 / 区县筛选。
- 合伙人筛选。

特殊筛选：

| 筛选项 | 所属页面 | 作用范围 |
| --- | --- | --- |
| 有效取消阈值 | 城市经营、时段热力、主体分析 | 影响有效订单相关计算，建议在 MySQL 重算或用 Power BI 参数控制 |
| 商家型用户阈值 | 主体分析 | 只影响商家型用户识别 |
| 骑手达标单量 / 天数 | 主体分析 | 只影响骑手名单达标判断 |

日期范围建议：

```text
单次分析尽量不超过 31 天
```

为什么：

- 方便和当前系统规则保持一致。
- 避免明细量大时 Power BI 页面变慢。
- 让页面趋势更聚焦。

---

## 14. 数据刷新流程

### 14.1 手工刷新流程

适合刚开始使用。

```text
1. 拿到新订单明细 / 名单表
2. 导入 MySQL ODS 表
3. 执行 DWD 重建 SQL
4. 执行 ADS 汇总 SQL
5. 打开 Power BI
6. 点击刷新
7. 检查页面数据
```

### 14.2 推荐做成存储过程

可以把重建流程封装成：

```sql
CALL rebuild_delivery_dashboard();
```

存储过程内部做：

```text
重建 DWD
重建 ADS 合伙人日指标
重建 ADS 小时指标
重建 ADS 骑手日指标
重建 ADS 商家日指标
```

### 14.3 增量刷新建议

第一版可以全量重建。

数据量大以后再做增量：

```text
只重建受影响月份
只重建最近 31 天
只重建新增文件涉及的合伙人
```

不要第一版就做复杂增量，否则排查问题会变难。

---

## 15. 验收清单

### 15.1 数据导入验收

| 检查项 | 验收方式 |
| --- | --- |
| 订单行数一致 | Excel 行数与 `ods_order_detail_raw` 行数一致 |
| 骑手表导入成功 | `rider_roster` 行数大于 0 |
| 商家表导入成功 | `merchant_roster` 行数大于 0 |
| 合伙人表导入成功 | `partner_roster` 行数大于 0 |
| 中文不乱码 | 随机查骑手姓名、商户名称、合伙人名称 |

### 15.2 ID 匹配验收

```sql
SELECT rider_id, rider_name
FROM dwd_order_detail
WHERE rider_id IN ('71640', '88326')
GROUP BY rider_id, rider_name;
```

期望：

```text
71640 能匹配到正确骑手姓名
88326 能匹配到正确骑手姓名
```

商家检查：

```sql
SELECT merchant_id, merchant_name, shop_name
FROM dwd_order_detail
WHERE merchant_id IS NOT NULL
LIMIT 50;
```

期望：

```text
商家ID、商家名称、商户名称不串位
```

### 15.3 指标验收

找一个固定日期、固定合伙人，对比 Excel 筛选结果和 MySQL：

```sql
SELECT
  COUNT(*) AS total_orders,
  SUM(is_valid_order) AS valid_orders,
  SUM(is_completed) AS completed_orders,
  SUM(is_cancelled) AS cancelled_orders
FROM dwd_order_detail
WHERE partner_id = '628'
  AND order_date BETWEEN '2026-03-02' AND '2026-03-31';
```

期望：

```text
总订单一致
完成订单一致
取消订单一致
有效订单口径可解释
```

### 15.4 Power BI 页面验收

| 页面 | 验收点 |
| --- | --- |
| 全国总览 | KPI 卡片、趋势、区域排名有数据 |
| 城市经营 | 选择合伙人后经营摘要有数据 |
| 时段热力与履约 | 小时订单、接单骑手数、全职/兼职人效有数据 |
| 主体分析 | 商家名单、骑手名单、订单来源、骑手提成有数据 |
| 诊断预警 | 风险、关注、波动对象能展示 |

---

## 16. 推荐实施顺序

### 阶段 1：先把数据进 MySQL

目标：

```text
订单、骑手、商家、合伙人 4 类表都能导入
```

不要急着做 Power BI。

### 阶段 2：做 DWD 标准订单表

目标：

```text
ID 和名称匹配正确
核心订单状态判断正确
```

这是最重要的一步。

### 阶段 3：做 ADS 汇总表

目标：

```text
能按天、按小时、按骑手、按商家汇总
```

### 阶段 4：Power BI 做 5 页

推荐顺序：

```text
全国总览
城市经营
时段热力与履约
主体分析
诊断预警
```

### 阶段 5：做刷新和权限

目标：

```text
固定人员负责导入
固定流程刷新 MySQL
Power BI 定时刷新或手动刷新
```

---

## 17. 常见错误和排查

### 17.1 页面数字是 0

优先查：

```sql
SELECT COUNT(*) FROM dwd_order_detail;
SELECT MIN(order_date), MAX(order_date) FROM dwd_order_detail;
```

可能原因：

- DWD 没重建。
- 日期字段没有解析成功。
- Power BI 日期筛选选错范围。

### 17.2 骑手姓名显示成 ID

查：

```sql
SELECT o.rider_id, o.rider_name, r.rider_name AS roster_name
FROM ods_order_detail_raw o
LEFT JOIN rider_roster r ON r.rider_id = o.rider_id
WHERE o.rider_id IS NOT NULL
LIMIT 50;
```

可能原因：

- 骑手表没导入。
- 订单里的骑手 ID 字段取错。
- ID 被 Excel 转成数字或科学计数法。

### 17.3 商家名称不对

查：

```sql
SELECT
  o.merchant_id,
  o.merchant_name AS order_merchant_name,
  o.shop_name AS order_shop_name,
  m.merchant_name AS roster_merchant_name,
  m.shop_name AS roster_shop_name
FROM ods_order_detail_raw o
LEFT JOIN merchant_roster m ON m.merchant_id = o.merchant_id
WHERE o.merchant_id IS NOT NULL
LIMIT 50;
```

推荐展示优先级：

```text
商户名称 / 店铺名称
商家名称
商家ID
```

### 17.4 Power BI 刷新失败

常见原因：

- MySQL 服务没启动。
- 账号密码错。
- Power BI 没安装 MySQL Connector。
- 表结构改了但 Power BI 模型没刷新。
- 字段类型不一致，例如日期被当文本。

---

## 18. 最小可落地版本

如果你想最快跑起来，先只做这些：

### 必做表

```text
ods_order_detail_raw
rider_roster
merchant_roster
partner_roster
dwd_order_detail
ads_partner_day_metrics
ads_partner_hour_metrics
ads_rider_day_metrics
ads_merchant_day_metrics
```

### 必做页面

```text
全国总览
城市经营
时段热力与履约
主体分析
诊断预警
```

### 必验指标

```text
总订单
有效订单
完成订单
取消订单
完成率
活跃骑手数
活跃商家数
骑手提成
合伙人收入
经营利润
```

---

## 19. 最后建议

第一版不要追求一步到位。

最稳路线是：

```text
先让 MySQL 数据算准
再让 Power BI 页面好看
最后再做自动刷新和高级诊断
```

只要 DWD 这张标准订单明细表做准，后面无论是 Power BI、网页看板，还是其他分析工具，都能复用同一套数据底座。

