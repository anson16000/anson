# Python + DuckDB + Power BI 直连重构方案

版本：v1.0  
适用场景：保留当前 Python + DuckDB 数据底座，让 Power BI 直接读取 DuckDB 标准表  
目标读者：业务负责人、数据分析人员、Power BI 报表制作人员、后续实施工程师

---

## 1. 这条路线解决什么问题

当前项目已经有一套完整的数据链路：

```text
原始订单 / 骑手 / 商家 / 合伙人表格
        ↓
Python 导入、清洗、匹配
        ↓
DuckDB 数据库
        ↓
ODS / DWD / ADS 分层表
        ↓
FastAPI + 网页看板
```

如果目标是用 Power BI 承接展示层，最少重写的路线不是新建 MySQL，而是：

```text
原始表格
        ↓
沿用当前 Python 导入和重建
        ↓
沿用当前 DuckDB 数据库
        ↓
Power BI 通过 ODBC 直连 DuckDB
        ↓
Power BI 重建 5 页报表
```

一句话：

```text
Python + DuckDB 继续负责把数据算准
Power BI 负责把结果展示清楚
```

这条路线适合当前项目的原因：

- 当前项目已经使用 DuckDB，不需要重新设计 MySQL 数据库。
- 当前 ODS / DWD / ADS 口径已经沉淀在 Python 和 DuckDB 中。
- Power BI 可以通过 ODBC 读取 DuckDB 表或 SQL 查询。
- 第一阶段可以优先读取 ADS 汇总表，避免 Power BI 直接扫大明细。

---

## 2. 和 MySQL / Parquet 方案怎么选

| 方案 | 优点 | 缺点 | 适合场景 |
| --- | --- | --- | --- |
| Power BI 直连 DuckDB | 复用当前系统最多，不需要导出中间文件，不需要新数据库服务 | 依赖 ODBC 驱动，文件锁和刷新流程要管好 | 本机、小团队、当前系统平滑过渡 |
| DuckDB 导出 Parquet 给 Power BI | 文件稳定、Power BI 读取轻、避免直接读数据库锁冲突 | 多一步导出，文件路径和版本要管理 | 稳定报表、共享文件夹、网盘同步 |
| MySQL + Power BI | 多人协作和权限更好，数据库服务成熟 | 需要重建表结构和 SQL，迁移成本更高 | 多人长期使用、服务化部署 |
| SQL Server + Power BI | 微软生态最顺，Gateway 和权限成熟 | 比本地 DuckDB 重，需要安装数据库服务 | Windows 环境、企业级 Power BI |

当前建议：

```text
第一优先：Power BI 直连 DuckDB，快速复用当前数据底座
第二选择：如果直连刷新或文件锁不稳定，再改成 DuckDB 导出 Parquet
第三选择：如果需要多人、权限、服务器，再考虑 SQL Server 或 MySQL
```

---

## 3. 当前系统哪些可以复用

### 3.1 可以直接复用的能力

| 能力 | 当前系统已有情况 | Power BI 直连时怎么用 |
| --- | --- | --- |
| 原始文件导入 | Python 已支持订单、骑手、商家、合伙人导入 | 继续用当前导入脚本 |
| 强制重建 | `import --mode=force` 已支持 | 修改口径后重建 DuckDB |
| 字段映射 | 已处理订单、骑手、商家、合伙人字段别名 | 继续复用 |
| 骑手匹配 | DWD 中已有骑手 ID / 姓名回退逻辑 | Power BI 直接读 DWD 或 ADS |
| 商家匹配 | 商家 ID、商家名称、商户名称已标准化 | Power BI 直接展示 |
| 有效订单 | 已在 DWD/ADS 中统一计算 | Power BI 不重复定义底层口径 |
| 新骑手/新商家 | 已按窗口期计算 | Power BI 直接使用字段 |
| 小时运力 | 已有接单骑手数、人效、全职/兼职拆分 | Power BI 读取小时表 |
| 主体分析 | 骑手、商家、商家型用户、订单来源已有接口逻辑 | 优先读取 DWD/ADS，必要时补视图 |
| 诊断预警 | 风险、关注、波动已有查询逻辑 | 可转成 DuckDB 视图或 Power BI 查询 |

### 3.2 不建议第一阶段重写的部分

第一阶段不要重写：

- 原始文件扫描逻辑。
- 字段映射逻辑。
- DWD 构建 SQL。
- ADS 汇总逻辑。
- 有效订单、新主体、补贴、利润、骑手提成等核心口径。

第一阶段只做：

```text
让 Power BI 能稳定读取当前 DuckDB 中的标准结果表
```

---

## 4. 推荐总体架构

```text
data/
  orders_raw/
  riders/
  merchants/
  partners/

        ↓

Python 导入脚本
  01-一键导入数据.bat
  01-一键强制重建.bat
  python main.py import --mode=auto
  python main.py import --mode=force

        ↓

DuckDB 数据库
  db/delivery_analysis.duckdb

        ↓

Power BI Desktop
  通过 DuckDB ODBC DSN 读取
  优先读取 ADS 表
  少量读取 DWD 明细表

        ↓

Power BI 报表
  全国总览
  城市经营
  时段热力与履约
  主体分析
  诊断预警
```

---

## 5. Power BI 如何直连 DuckDB

### 5.1 连接方式

Power BI Desktop 本身没有内置 DuckDB 专用连接器时，可以使用通用 ODBC 方式。

推荐连接方式：

```text
DuckDB ODBC Driver
        ↓
Windows ODBC 数据源 DSN
        ↓
Power BI Desktop - 获取数据 - ODBC
        ↓
选择 DuckDB 表或输入 SQL
```

### 5.2 安装 DuckDB ODBC 驱动

基本步骤：

```text
1. 下载 DuckDB ODBC Driver 64 位版本
2. 安装到 Windows
3. 打开 ODBC 数据源管理器 64 位
4. 新建 System DSN 或 User DSN
5. 选择 DuckDB Driver
6. 配置 DuckDB 数据库文件路径
```

建议使用 64 位驱动，因为 Power BI Desktop 通常是 64 位。驱动位数不匹配时，Power BI 可能看不到 DSN。

### 5.3 推荐 DSN 配置

建议 DSN 名称：

```text
DeliveryDuckDB
```

数据库文件路径：

```text
F:\codex\delivery-dashboard\db\delivery_analysis.duckdb
```

如果部署到其他电脑，建议路径尽量固定，例如：

```text
D:\delivery-dashboard\db\delivery_analysis.duckdb
```

或使用同步盘固定目录：

```text
H:\BaiduSyncdisk\...\delivery-dashboard\db\delivery_analysis.duckdb
```

但要注意：DuckDB 文件放在网盘同步目录时，可能出现文件锁、同步冲突或刷新读到半同步文件的问题。

---

## 6. Power BI 连接步骤

### 6.1 Power BI Desktop 读取 DuckDB

操作步骤：

```text
1. 打开 Power BI Desktop
2. 点击 获取数据
3. 选择 ODBC
4. 选择 DSN：DeliveryDuckDB
5. 连接
6. 在导航器中选择需要的表
7. 点击 转换数据 或 加载
```

### 6.2 推荐使用 SQL 查询方式

Power BI 连接 ODBC 时，可以直接选择表，也可以输入 SQL。

更推荐输入 SQL，原因是：

- 可以只取需要字段。
- 可以先限制日期范围。
- 可以避免 Power BI 一开始加载太多明细。
- 可以把复杂逻辑留在 DuckDB 侧。

示例：

```sql
SELECT
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
  active_riders,
  active_merchants,
  new_riders,
  new_merchants,
  hq_subsidy_total,
  partner_subsidy_total
FROM ads_partner_day_metrics;
```

小时表：

```sql
SELECT
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
  efficiency,
  fulltime_efficiency,
  parttime_efficiency
FROM ads_partner_hour_metrics;
```

---

## 7. 推荐 Power BI 读取哪些表

### 7.1 第一阶段优先读取 ADS 表

第一阶段不要让 Power BI 大量直接扫 `dwd_order_detail`。

优先读取：

```text
ads_partner_day_metrics
ads_partner_hour_metrics
ads_partner_rider_day_metrics
ads_partner_merchant_day_metrics
rider_roster
merchant_roster
partner_roster
```

原因：

- ADS 已经按页面场景汇总。
- Power BI 加载更快。
- 指标口径更稳定。
- 报表模型更简单。

### 7.2 什么时候读取 DWD 明细

只有这些场景建议读取 `dwd_order_detail`：

- 需要周期内去重活跃骑手。
- 需要周期内去重活跃商家。
- 需要订单来源分析。
- 需要商家型用户识别。
- 需要排查数据明细。

如果 DWD 行数很大，建议不要整表加载，而是建立 DuckDB 视图或用 SQL 只取必要字段。

---

## 8. 建议增加 DuckDB 视图

虽然第一阶段可以直接读表，但更推荐给 Power BI 准备一批“报表视图”。

视图命名建议：

```text
pbi_admin_overview
pbi_partner_day
pbi_partner_hourly
pbi_rider_day
pbi_merchant_day
pbi_order_source
pbi_alerts_partner
```

好处：

- Power BI 只读 `pbi_` 视图，不直接依赖底层表结构。
- 后续底层字段变化时，只改视图，Power BI 不一定要大改。
- 可以在视图里提前修正字段名、空值和展示名称。

示例：

```sql
CREATE OR REPLACE VIEW pbi_partner_day AS
SELECT
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
  partner_subsidy_total
FROM ads_partner_day_metrics;
```

小时运力视图：

```sql
CREATE OR REPLACE VIEW pbi_partner_hourly AS
SELECT
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
  efficiency,
  fulltime_efficiency,
  parttime_efficiency,
  completion_rate,
  cancel_rate
FROM ads_partner_hour_metrics;
```

订单来源视图：

```sql
CREATE OR REPLACE VIEW pbi_order_source AS
SELECT
  partner_id,
  partner_name,
  order_date AS date,
  COALESCE(NULLIF(order_source, ''), '未知') AS order_source,
  COUNT(*) AS total_orders,
  SUM(CASE WHEN is_valid_order THEN 1 ELSE 0 END) AS valid_orders,
  SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) AS completed_orders,
  SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END) AS cancelled_orders
FROM dwd_order_detail
WHERE order_date IS NOT NULL
GROUP BY
  partner_id,
  partner_name,
  order_date,
  COALESCE(NULLIF(order_source, ''), '未知');
```

---

## 9. Power BI 数据模型

### 9.1 推荐模型

建议采用星型模型：

```text
维度表：
  partner_roster
  rider_roster
  merchant_roster
  日期表

事实表：
  pbi_partner_day 或 ads_partner_day_metrics
  pbi_partner_hourly 或 ads_partner_hour_metrics
  pbi_rider_day 或 ads_partner_rider_day_metrics
  pbi_merchant_day 或 ads_partner_merchant_day_metrics
  pbi_order_source
```

### 9.2 推荐关系

| 事实表 | 字段 | 维度表 | 字段 | 关系 |
| --- | --- | --- | --- | --- |
| pbi_partner_day | partner_id | partner_roster | partner_id | 多对一 |
| pbi_partner_hourly | partner_id | partner_roster | partner_id | 多对一 |
| pbi_rider_day | rider_id | rider_roster | rider_id | 多对一 |
| pbi_merchant_day | merchant_id | merchant_roster | merchant_id | 多对一 |
| 各事实表 | date | 日期表 | date | 多对一 |

### 9.3 日期表

Power BI 中建议新建日期表：

```DAX
日期表 =
CALENDAR(
    MIN(pbi_partner_day[date]),
    MAX(pbi_partner_day[date])
)
```

再增加年月字段：

```DAX
年月 = FORMAT('日期表'[Date], "yyyy-MM")
```

```DAX
月份 = MONTH('日期表'[Date])
```

```DAX
日 = DAY('日期表'[Date])
```

---

## 10. Power BI 常用 DAX

### 10.1 全国 / 城市主指标

```DAX
总订单 =
SUM(pbi_partner_day[total_orders])
```

```DAX
有效订单 =
SUM(pbi_partner_day[valid_orders])
```

```DAX
完成订单 =
SUM(pbi_partner_day[completed_orders])
```

```DAX
取消订单 =
SUM(pbi_partner_day[cancelled_orders])
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

### 10.2 小时运力

```DAX
接单骑手数 =
SUM(pbi_partner_hourly[accepted_rider_count])
```

```DAX
全职接单骑手数 =
SUM(pbi_partner_hourly[fulltime_accepted_rider_count])
```

```DAX
兼职接单骑手数 =
SUM(pbi_partner_hourly[parttime_accepted_rider_count])
```

```DAX
人效 =
DIVIDE(
    SUM(pbi_partner_hourly[completed_orders]),
    SUM(pbi_partner_hourly[accepted_rider_count])
)
```

```DAX
全职人效 =
DIVIDE(
    SUM(pbi_partner_hourly[fulltime_completed_orders]),
    SUM(pbi_partner_hourly[fulltime_accepted_rider_count])
)
```

```DAX
兼职人效 =
DIVIDE(
    SUM(pbi_partner_hourly[parttime_completed_orders]),
    SUM(pbi_partner_hourly[parttime_accepted_rider_count])
)
```

### 10.3 收益

```DAX
合伙人收入 =
SUM(pbi_partner_day[partner_income_total])
```

```DAX
合伙人补贴 =
SUM(pbi_partner_day[partner_subsidy_total])
```

```DAX
经营利润 =
[合伙人收入] - [合伙人补贴]
```

---

## 11. 5 页报表映射

### 11.1 全国总览

读取：

```text
pbi_partner_day
partner_roster
日期表
```

展示：

- 一级 KPI。
- 全国趋势。
- 区域排名。
- 加盟商分层。
- 新合伙人表现。

### 11.2 城市经营

读取：

```text
pbi_partner_day
partner_roster
```

展示：

- 经营摘要。
- 经营收益。
- 日单量统计。
- 有效订单统计。
- 直营专项摘要入口。

### 11.3 时段热力与履约

读取：

```text
pbi_partner_hourly
```

展示：

- 小时订单。
- 接单骑手数。
- 全职 / 兼职接单骑手数。
- 人效、全职人效、兼职人效。
- 小时热力图。
- 取消率、履约率。

### 11.4 主体分析

读取：

```text
pbi_order_source
pbi_rider_day
pbi_merchant_day
rider_roster
merchant_roster
```

展示：

- 主体摘要。
- 订单来源分析。
- 商家名单。
- 骑手名单。
- 骑手单量分层。
- 骑手提成明细。
- 新骑手 / 新商家贡献。
- 用户主体识别。

### 11.5 诊断预警

读取：

```text
pbi_partner_day
pbi_alerts_partner
```

展示：

- 关注合伙人。
- 风险合伙人。
- 波动预警。
- 健康度评分。
- 问题清单。

---

## 12. 刷新流程

### 12.1 手动刷新流程

推荐固定顺序：

```text
1. 放入新的订单、骑手、商家、合伙人文件
2. 关闭 Power BI 正在刷新中的查询
3. 运行 01-一键导入数据.bat
4. 如代码或口径刚修改，运行 01-一键强制重建.bat
5. 等 Python 导入完成
6. 确认没有导入进程正在写 DuckDB
7. 打开 Power BI
8. 点击刷新
9. 检查 5 页数据
```

### 12.2 为什么刷新前要注意文件锁

DuckDB 是单文件数据库。它适合分析，但要注意：

- 多个读取通常没问题。
- 多进程同时写同一个 DuckDB 文件不适合作为默认模式。
- Power BI 刷新时如果 Python 正在重建表，可能读到锁冲突或旧数据。
- Python 导入时如果 Power BI 长时间占用文件，也可能影响写入。

推荐原则：

```text
Python 写库时，Power BI 不刷新
Power BI 刷新时，Python 不导入
```

### 12.3 网页服务和 Power BI 同时使用

如果当前 FastAPI 网页服务也在读取 DuckDB，通常可以和 Power BI 一起读取。  
但如果要执行导入或强制重建，建议：

```text
先关闭网页服务
再执行导入/强制重建
导入完成后再启动网页服务或刷新 Power BI
```

这样最稳。

---

## 13. Power BI Service 定时刷新说明

Power BI Desktop 本地直连 DuckDB 相对容易。  
Power BI Service 云端定时刷新会更麻烦，因为：

- 云端不能直接访问你本机的 DuckDB 文件。
- 需要安装并配置 On-premises Data Gateway。
- Gateway 机器上也必须安装 64 位 DuckDB ODBC 驱动。
- Gateway 机器上的 DSN 名称和 Power BI 文件中使用的连接要一致。
- DuckDB 文件路径必须是 Gateway 机器能访问的稳定路径。

如果只是你自己本地看报表：

```text
Power BI Desktop + DuckDB ODBC 直连即可
```

如果要发布到 Power BI Service 并自动刷新：

```text
优先评估 Parquet + SharePoint/OneDrive
或 SQL Server / MySQL / Fabric
```

---

## 14. 路径和多电脑使用建议

### 14.1 本机使用

建议固定路径：

```text
F:\codex\delivery-dashboard\db\delivery_analysis.duckdb
```

Power BI、ODBC DSN、导入脚本都指向同一份文件。

### 14.2 其他电脑使用

如果换电脑，必须同步：

- 项目代码。
- `db/delivery_analysis.duckdb`。
- DuckDB ODBC 驱动。
- Power BI 报表文件。
- DSN 配置。

建议每台电脑保持同样目录结构，例如：

```text
D:\delivery-dashboard\db\delivery_analysis.duckdb
```

否则 Power BI 可能找不到数据库文件。

### 14.3 网盘同步目录

可以放在百度网盘、OneDrive、SharePoint 同步目录，但要小心：

- DuckDB 文件同步期间不要打开 Power BI 刷新。
- 不要两台电脑同时写同一个 DuckDB 文件。
- 同步未完成时，Power BI 可能读到旧文件或损坏状态。

更稳做法：

```text
本机导入和重建
完成后复制 DuckDB 文件到共享目录
Power BI 只读取共享目录中的稳定副本
```

---

## 15. 适合和不适合场景

### 15.1 适合

适合：

- 本机使用。
- 小团队使用。
- 数据按天或按月批量刷新。
- 主要做经营分析，不需要实时写入。
- 希望最大化复用当前 Python + DuckDB 项目。
- 不想维护 MySQL / SQL Server 数据库服务。

### 15.2 不适合

不适合：

- 多人同时写库。
- 大量用户同时访问。
- 企业级权限管理。
- 严格的 Power BI Service 定时刷新。
- 需要稳定数据库服务对外提供连接。

这些场景更建议：

```text
SQL Server + Power BI
MySQL + Power BI
Microsoft Fabric + Power BI
```

---

## 16. 实施阶段建议

### 阶段 1：验证 Power BI 能连上 DuckDB

目标：

```text
Power BI 通过 ODBC 读取 ads_partner_day_metrics
```

验收：

```text
能看到表字段
能加载数据
能做一个总订单卡片
```

### 阶段 2：建立 pbi_ 视图

目标：

```text
Power BI 只读取 pbi_ 开头的报表视图
```

验收：

```text
pbi_partner_day 可用
pbi_partner_hourly 可用
pbi_order_source 可用
```

### 阶段 3：重建 5 页 Power BI 报表

目标：

```text
全国总览、城市经营、时段热力、主体分析、诊断预警都能展示
```

### 阶段 4：固化刷新流程

目标：

```text
导入数据、重建 DuckDB、刷新 Power BI 的顺序固定
```

### 阶段 5：评估是否改 Parquet 或数据库服务

如果发现 ODBC 直连不稳定，再切换：

```text
DuckDB -> Parquet -> Power BI
```

如果需要多人和定时刷新，再切换：

```text
SQL Server / MySQL / Fabric -> Power BI
```

---

## 17. 验收清单

### 17.1 连接验收

| 检查项 | 通过标准 |
| --- | --- |
| DuckDB ODBC 驱动安装 | Windows ODBC 管理器能看到 DuckDB Driver |
| DSN 配置 | DSN 能指向 `delivery_analysis.duckdb` |
| Power BI 连接 | Power BI 能通过 ODBC 打开表列表 |
| 表加载 | 至少能加载 `ads_partner_day_metrics` |

### 17.2 数据验收

| 检查项 | 通过标准 |
| --- | --- |
| 总订单 | Power BI 与当前网页看板一致 |
| 完成订单 | Power BI 与当前网页看板一致 |
| 取消订单 | Power BI 与当前网页看板一致 |
| 有效订单 | Power BI 与当前网页看板一致 |
| 骑手/商家名称 | 不出现明显 ID/名称错配 |

### 17.3 页面验收

| 页面 | 验收点 |
| --- | --- |
| 全国总览 | KPI、趋势、排名能显示 |
| 城市经营 | 选择合伙人后有经营摘要 |
| 时段热力与履约 | 小时运力、全职/兼职接单骑手数、人效能显示 |
| 主体分析 | 订单来源、商家名单、骑手名单、提成能显示 |
| 诊断预警 | 风险、关注、波动能显示 |

### 17.4 刷新验收

```text
先导入新数据
再刷新 Power BI
Power BI 显示最新数据版本
刷新过程中没有 DuckDB 文件锁错误
```

---

## 18. 最终建议

对当前项目来说，Power BI 直连 DuckDB 是一条很好的过渡路线：

```text
改动少
复用多
上线快
成本低
```

但它不是企业级终局方案。

推荐实际路线：

```text
第一阶段：Power BI 直连 DuckDB，快速跑通
第二阶段：如果直连稳定，就继续使用
第三阶段：如果刷新或共享遇到问题，改成 DuckDB 导出 Parquet
第四阶段：如果未来多人协作和权限要求提高，再迁移到 SQL Server / MySQL / Fabric
```

一句话：

```text
先用 DuckDB 直连把 Power BI 报表做起来，再根据真实使用问题决定是否升级架构。
```

---

## 19. 参考资料

- DuckDB ODBC 官方文档：`https://duckdb.org/docs/current/clients/odbc/overview.html`
- DuckDB 并发与文件锁说明：`https://duckdb.org/docs/current/connect/concurrency.html`
- Microsoft Power Query ODBC 连接器文档：`https://learn.microsoft.com/en-us/power-query/connectors/odbc`
- Microsoft Power BI 通用 ODBC 连接说明：`https://learn.microsoft.com/en-us/power-bi/connect-data/desktop-connect-using-generic-interfaces`

