# 同城配送经营分析系统

基于 `Python + FastAPI + DuckDB + Power BI/网页看板` 的本地配送经营分析系统。

当前数据链路：

```text
原始订单/名单文件
-> Python 导入
-> DuckDB ODS/DWD/ADS
-> 网页看板
-> Power BI Parquet 成品层
```

## 2019 Demo Dataset

This project includes a synthetic one-month demo mode for resume and interview demos.

Use:

```text
05-demo-2019-import.bat
06-demo-2019-start.bat
05-生成并导入2019演示数据.bat
06-启动2019演示看板.bat
```

Demo scope:

- Month: 2019-05
- Partners: 12
- Riders: 120
- Merchants: 192
- Orders: about 10,000

Demo files are generated under:

```text
demo_data/2019/
db/demo_2019.duckdb
exports/demo2019_powerbi_parquet/
```

The demo data is synthetic and is ignored by Git.

## 页面入口

| 页面 | 路由 | 说明 |
| --- | --- | --- |
| 全国总览 | `/` | 全国级经营概览、趋势、排名和分层 |
| 城市经营 | `/partner` | 单城市经营摘要、收益和直营专项入口 |
| 时段热力与履约 | `/partner/hourly` | 小时运力、热力、履约与 SLA |
| 主体分析 | `/partner/entities` | 商户、骑手、订单来源、主体识别与名单明细 |
| 诊断预警 | `/alerts` | 风险、关注、健康度与波动预警 |

兼容入口：

- `/direct` 会跳转到 `/partner?section=direct`

## Windows 首次部署

当前项目主要支持 Windows 本地使用。

1. 复制整个项目目录到新电脑。
2. 双击运行 `00-初始化环境.bat`。
3. 初始化成功后，双击 `02-一键启动看板.bat`。
4. 如需导入数据，运行 `01-一键导入数据.bat`。
5. 如果代码逻辑修过但原始文件没变，运行 `01-一键强制重建.bat`。

初始化脚本会自动：

- 检查 Python 3.12。
- 创建 `.venv`。
- 安装 `requirements.txt`。
- 检查目录、配置和端口。

## 常用命令

```powershell
# 普通导入，文件未变化时会跳过
python main.py import --mode=auto

# 强制重建，忽略文件去重并重建当前文件对应月份
python main.py import --mode=force

# 只导出 Power BI Parquet 成品层
python main.py export-powerbi

# 启动网页看板
python main.py server --port 8090

# 运行测试
python -m unittest discover -s tests -p "test*.py"
```

## 常用批处理脚本

| 脚本 | 作用 |
| --- | --- |
| `00-初始化环境.bat` | 首次部署、环境检查与自动安装 |
| `01-一键导入数据.bat` | 普通导入数据 |
| `01-一键强制重建.bat` | 强制重建当前文件对应月份 |
| `02-一键启动看板.bat` | 启动本地网页看板 |
| `03-运行测试.bat` | 运行自动化测试 |
| `04-导出PowerBI-Parquet.bat` | 手动导出 Power BI Parquet 成品层 |

## Power BI Parquet 成品层

导入成功后会自动导出：

```text
exports/powerbi_parquet/
```

Power BI 建议读取这些 Parquet 文件，而不是直接连接 DuckDB 数据库文件。这样可以减少：

- DuckDB 文件锁。
- ODBC 驱动问题。
- Power BI 刷新占用数据库。
- 多电脑路径不一致。

手动导出：

```powershell
python main.py export-powerbi
```

或双击：

```text
04-导出PowerBI-Parquet.bat
```

详细说明见：

- `docs/Python+DuckDB+Parquet+PowerBI重构方案.md`

## 数据目录

```text
data/
├── orders_raw/      # 原始订单数据
├── orders_stage/    # 订单预处理后的 stage 文件
├── orders/          # 兼容旧目录
├── riders/          # 骑手/帮手名单
├── merchants/       # 商家/商户名单
└── partners/        # 合伙人名单
```

首次部署时 `data/` 可以为空。没有业务数据时，页面可以启动，但不会显示真实业务结果。

## GitHub 上传边界

仓库只上传代码和文档，不上传业务原始数据和生成结果。

默认不上传：

- `data/`
- `db/*.duckdb`
- `db/*.duckdb.wal`
- `logs/`
- `exports/`

## 文档

主要文档在 `docs/` 目录：

- `Python+DuckDB+Parquet+PowerBI重构方案.md`
- `Python+DuckDB+PowerBI直连重构方案.md`
- `ODS-DWD-ADS现有表说明.md`
- `ODS-DWD-ADS表生成流程说明.md`
- `同城配送经营分析系统-字段字典-v1.md`
- `同城配送经营分析系统-项目完整口径手册-v1.md`

## 默认端口

网页看板默认端口：

```text
8090
```
