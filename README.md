# 同城配送经营分析系统

基于 `FastAPI + SQLAlchemy + DuckDB + 原生前端` 的本地经营分析系统。

## 页面结构（5 页架构）

| 页面 | 路由 | 说明 |
|------|------|------|
| 全国总览 | `/` | 全局经营数据总览 |
| 城市经营 | `/partner` | 合伙人视角经营分析，含直营专项 |
| 时段热力 | `/partner/hourly` | 分时段订单分布与履约分析 |
| 主体分析 | `/partner/entities` | 商家、骑手、合伙人详情分析 |
| 诊断预警 | `/alerts` | 异常订单、履约问题预警 |

兼容入口：

- `/direct` → 跳转至 `/partner?section=direct`（直营专项）

## 快速启动

### Windows 批处理入口

```
01-一键导入数据.bat   # 自动导入数据（按文件哈希去重）
01-一键强制重建.bat   # 强制重建所有月份数据
02-一键启动看板.bat   # 启动看板服务（默认端口 8090）
03-运行测试.bat       # 运行单元测试
```

### 命令行方式

```bash
# 数据导入
python main.py import --mode=auto    # 自动模式：文件未变化时跳过
python main.py import --mode=force   # 强制模式：忽略去重重建

# 启动服务
python main.py server --port=8090    # 默认端口 8090
python main.py server --reload        # 启用热重载开发模式
```

## 核心业务口径

| 指标 | 定义 |
|------|------|
| 主统计日期 | 按下单日期统计 |
| 有效订单 | 完成订单 + 支付后取消且支付到取消时长 > 阈值 |
| 超时取消 | 下单到取消时长 > 阈值分钟 |
| 完成率 | 完成订单 / 总订单 |
| 取消率 | 取消订单 / 总订单 |
| 有效订单完成率 | 完成订单 / 有效订单 |
| 有效订单取消率 | 有效取消订单 / 有效订单 |
| 经营利润 | 合伙人收入总额 - 合伙人补贴总额 |
| 订单均价 | 实付金额 / 完成订单数（按实际收款 `amount_paid` 计算） |

## 项目结构

```
delivery-dashboard/
├── main.py                 # 入口：import / server 命令
├── app/
│   ├── api.py              # FastAPI 接口层
│   ├── models.py           # 数据库模型
│   ├── pipeline.py         # 数据导入与聚合管道
│   ├── config.py           # 配置管理
│   ├── database.py         # 数据库连接
│   ├── services/           # 业务逻辑服务
│   └── static/              # 前端静态资源
│       ├── admin.html       # 全国总览
│       ├── partner.html     # 城市经营
│       ├── hourly.html      # 时段热力
│       ├── entities.html    # 主体分析
│       ├── alerts.html      # 诊断预警
│       ├── controllers/     # 页面控制器
│       ├── modules/         # 业务模块
│       └── ui/              # UI 组件
├── config/                  # YAML 配置文件
├── scripts/                 # 辅助脚本
├── tests/                   # 单元测试
└── docs/                    # 项目文档
```

## 数据目录

```
data/
├── orders_raw/     # 原始订单数据
├── riders/         # 骑手数据
├── merchants/      # 商家数据
├── partners/       # 合伙人数据
├── orders/         # 兼容旧目录
└── orders_stage/   # 中间处理文件
```

## 文档

`docs/` 目录包含：

- **方案文档**：最新系统架构与设计
- **5 页版 PRD**：页面职责表、改版差异说明
- **口径手册**：完整业务指标定义
- **字段字典**：数据库字段说明

## GitHub 上传规则

**上传**：代码、配置、启动脚本、文档

**不上传**：原始数据、stage 中间文件、DuckDB 数据库文件、日志

```bash
# 推送前检查
git status
# 确认无原始数据、stage、数据库、日志文件
```
