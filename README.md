# 同城配送经营分析系统

基于 `FastAPI + SQLAlchemy + DuckDB + 原生前端` 的本地配送经营分析系统。

## 页面入口

| 页面 | 路由 | 说明 |
| --- | --- | --- |
| 全国总览 | `/` | 全国级经营概览、趋势、排名和分层 |
| 城市经营 | `/partner` | 单城市经营摘要、收益和直营专项入口 |
| 时段热力与履约 | `/partner/hourly` | 小时运力、热力、履约与 SLA |
| 主体分析 | `/partner/entities` | 商户、骑手、主体识别与名单明细 |
| 诊断预警 | `/alerts` | 风险加盟商、关注加盟商、健康度与波动预警 |

兼容入口：

- `/direct` 会跳转到 `/partner?section=direct`

## Windows 首次部署

本项目当前只支持 **Windows**。首次在新电脑使用时，按下面步骤执行：

1. 复制整个项目目录到新电脑
2. 双击运行 `00-初始化环境.bat`
3. 初始化成功后，双击运行 `02-一键启动看板.bat`
4. 如需导入业务数据，再运行：
   - `01-一键导入数据.bat`
   - `01-一键强制重建.bat`

### 初始化脚本会做什么

`00-初始化环境.bat` 会自动完成：

- 检查 Python 3.12 是否存在
- 缺失时自动下载安装 Python 3.12
- 创建项目虚拟环境 `.venv`
- 安装 `requirements.txt`
- 校验关键目录和关键文件
- 检查端口 `8090`
- 写入环境变量 `DELIVERY_DASHBOARD_PYTHON`

初始化日志：

- `logs\bootstrap_last.log`

## 常用批处理脚本

- `00-初始化环境.bat`：首次部署、环境检查与自动安装
- `01-一键导入数据.bat`：按文件去重导入数据
- `01-一键强制重建.bat`：忽略去重并强制重建当前文件对应月份
- `02-一键启动看板.bat`：启动本地看板服务
- `03-运行测试.bat`：运行自动化测试

这些脚本都会优先使用：

1. `DELIVERY_DASHBOARD_PYTHON`
2. 项目内 `.venv\Scripts\python.exe`
3. 系统中可用的 Python 3.12

## 命令行入口

```powershell
# 自动导入（文件未变化时跳过）
python main.py import --mode=auto

# 强制重建（忽略去重）
python main.py import --mode=force

# 启动服务
python main.py server --port 8090

# 开发模式
python main.py server --reload
```

## 默认端口

- 默认服务端口：`8090`

如果端口已占用，初始化脚本和启动脚本会给出提示。

## 数据目录说明

首次部署时 **不要求已有数据**，只有代码也可以先完成初始化并启动页面。

项目数据目录结构：

```text
data/
├─ orders_raw/      # 原始订单数据
├─ orders_stage/    # 订单预处理后的 stage 文件
├─ orders/          # 兼容旧目录
├─ riders/          # 骑手名册
├─ merchants/       # 商户名册
└─ partners/        # 合伙人名册
```

说明：

- `data/` 可以为空
- 没有原始业务数据时，页面可以启动，但不会显示真实业务结果
- 导入数据后，数据库会自动创建或更新

## GitHub 上传边界

仓库只上传代码和文档，不上传业务原始数据。

默认不随仓库分发的内容包括：

- 原始订单、骑手、商户、合伙人表格
- `data/orders_stage/`
- `db/*.duckdb`
- `db/*.duckdb.wal`
- `logs/`

首次在新电脑部署时，需要你自行放入数据文件后再导入。

## 目录结构

```text
delivery-dashboard/
├─ main.py
├─ app/
│  ├─ api.py
│  ├─ config.py
│  ├─ database.py
│  ├─ models.py
│  ├─ pipeline.py
│  ├─ services/
│  └─ static/
├─ config/
├─ docs/
├─ scripts/
├─ tests/
└─ requirements.txt
```

## 文档

`docs/` 目录中保留当前仍有效的文档，包括：

- 最新系统方案文档
- 5 页版 PRD
- 页面职责表
- 改版差异说明
- 字段字典
- 口径手册

## 运行测试

直接双击：

- `03-运行测试.bat`

或命令行执行：

```powershell
python -m unittest discover -s tests -p "test*.py"
```
