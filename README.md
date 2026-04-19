# 同城配送经营分析系统

这是一个基于 `FastAPI + SQLAlchemy + DuckDB + 原生前端` 的本地经营分析系统。当前项目已经稳定为 5 页结构：

- 全国总览：`/`
- 城市经营：`/partner`
- 时段热力与履约：`/partner/hourly`
- 主体分析：`/partner/entities`
- 诊断预警：`/alerts`

兼容入口：

- `/direct` 会跳转到城市经营页中的直营专项区域：`/partner?section=direct`

## 当前运行方式

默认服务端口：

- `8090`

常用命令：

```bash
python main.py import --mode=auto
python main.py import --mode=force
python main.py server --port=8090
```

Windows 批处理入口：

- `01-一键导入数据.bat`
- `01-一键强制重建.bat`
- `02-一键启动看板.bat`
- `03-运行测试.bat`

## 导入模式

- `auto`
  - 按文件哈希去重
  - 原始文件未变化时会直接跳过
- `force`
  - 忽略“已成功导入”去重
  - 重新处理当前文件并重建受影响月份

## 数据目录边界

建议原始数据放在：

- `data/orders_raw/`
- `data/riders/`
- `data/merchants/`
- `data/partners/`

兼容旧目录：

- `data/orders/`

程序中间产物：

- `data/orders_stage/`

默认不上传以下内容到 GitHub：

- 原始订单、骑手、商家、合伙人表格
- `orders_stage` 中间文件
- DuckDB 数据库文件
- 日志文件

## 当前核心业务口径

- 主统计日期：按下单日期
- 有效订单：完成订单 + 支付后取消且支付到取消时长大于阈值分钟
- 超时取消：下单到取消时长大于阈值分钟
- 完成率：完成订单 / 总订单
- 取消率：取消订单 / 总订单
- 有效订单完成率：完成订单 / 有效订单
- 有效订单取消率：有效取消订单 / 有效订单
- 经营利润：合伙人收入总额 - 合伙人补贴总额
- 骑手提成：等同于骑手佣金
- 骑手单均提成：骑手提成总计 / 完成订单
- 高峰接单骑手数：当前正式替代“高峰在线骑手数”

## 当前文档

`docs/` 目录当前保留的核心文档包括：

- 最新主方案文档
- 5 页版 PRD / 页面职责表 / 改版差异说明
- 项目完整口径手册
- 字段字典

## GitHub 上传规则

适合上传到 GitHub 的内容：

- 代码
- 配置
- 启动脚本
- 文档

默认不上传：

- 原始数据
- stage 中间文件
- 数据库文件
- 日志

推送前请确认：

- `.gitignore` 仍然有效
- `git status` 中不包含原始数据、stage、数据库、日志
