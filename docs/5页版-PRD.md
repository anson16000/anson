# 5页版 PRD

## 1. 目标

在现有 3 页母版基础上，正式演进为 5 页结构，并把小时能力、主体能力、诊断能力从原页面平滑独立出去。

## 2. 页面与路由

| 页面 | 路由 |
|---|---|
| 全国总览 | `/` |
| 城市经营 | `/partner` |
| 时段热力与履约 | `/partner/hourly` |
| 主体分析 | `/partner/entities` |
| 诊断预警 | `/alerts` |

兼容路由：

- `/direct` -> `/partner?section=direct`

## 3. 页面模块

### 3.1 全国总览

- 经营结论
- 一级 KPI
- 全国趋势
- 区域排名
- 加盟商日均单量分层
- 新合伙人表现

### 3.2 城市经营

- 经营摘要
- 经营收益
- 直营专项摘要
- 问题摘要入口

### 3.3 时段热力与履约

- 履约摘要
- 小时运力
- 热力图
- 准时率
- SLA 履约率 / 超时率

### 3.4 主体分析

- 主体摘要
- 新骑手 / 新商家贡献摘要
- 用户主体识别
- 骑手提成明细
- 名单明细

### 3.5 诊断预警

- 风险与关注摘要
- 关注加盟商
- 风险加盟商
- 健康度评分详情
- 波动预警

## 4. 字段与口径

- 主指标统一：
  - 总订单、有效订单、完成订单、取消订单、完成率、活跃骑手数、新骑手数、活跃商家数、新商家数、总部补贴、合伙人补贴
- `merchant_like_threshold` 只存在于主体分析页
- 查询上限固定为 31 天
- 高峰在线骑手数统一口径为：
  - 高峰接单骑手数
- 经营利润：
  - 合伙人收入总额 - 合伙人补贴总额

## 5. 接口映射

### 全国总览

- `GET /api/v1/meta`
- `GET /api/v1/admin/metrics`

### 城市经营

- `GET /api/v1/partner/{partner_id}/overview`
- `GET /api/v1/partner/{partner_id}/daily`
- `GET /api/v1/direct/cancel-daily`

### 时段热力与履约

- `GET /api/v1/partner/{partner_id}/overview`
- `GET /api/v1/partner/{partner_id}/hourly`
- `GET /api/v1/partner/{partner_id}/sla`

### 主体分析

- `GET /api/v1/partner/{partner_id}/overview`
- `GET /api/v1/partner/{partner_id}/new-riders`
- `GET /api/v1/partner/{partner_id}/new-merchants`
- `GET /api/v1/partner/{partner_id}/riders`
- `GET /api/v1/partner/{partner_id}/merchants`
- `GET /api/v1/partner/{partner_id}/merchant-like-users`
- `GET /api/v1/partner/{partner_id}/income/riders`

### 诊断预警

- `GET /api/v1/admin/metrics`
- `GET /api/v1/admin/health`
- `GET /api/v1/admin/partners/fluctuation`

## 6. 验收重点

- 5 个页面都可访问
- `/direct` 只做兼容跳转
- `merchant_like_threshold` 只在主体分析页生效
- 名单筛选只影响名单
- 所有页面继续限制最多 31 天
- 既有业务口径不变，只改变页面归属与层级
