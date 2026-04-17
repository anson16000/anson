# 同城配送经营分析系统（DuckDB 版）

项目根目录：`F:\codex\delivery-dashboard`  
本地数据库文件：`F:\codex\delivery-dashboard\db\delivery_analysis.duckdb`

## 目录说明

```text
delivery-dashboard
  app/
  config/
  data/
    orders_raw/      # 原始订单文件（xls/xlsx/csv）
    orders_stage/    # 程序自动生成或复用的标准 CSV
    orders/          # 兼容旧目录，订单也可以继续放这里
    riders/
    merchants/
    partners/
  db/
  docs/
  logs/
  scripts/
  main.py
  01-一键导入数据.bat
  02-一键启动看板.bat
```

## 日常使用

1. 更新数据：双击 `01-一键导入数据.bat`
2. 打开看板：双击 `02-一键启动看板.bat`
3. 浏览器地址：`http://127.0.0.1:8090`

## 命令行运行

```bash
python main.py import --mode=auto
python main.py server --port=8090
```

## 页面入口

- 全国页：`http://127.0.0.1:8090/`
- 单城市页：`http://127.0.0.1:8090/partner`
- 直营页：`http://127.0.0.1:8090/direct`

## 当前导入链路

1. `PREPROCESS`：订单 Excel 自动转标准 CSV 到 `data/orders_stage`
2. `LOAD_STAGE`：DuckDB 原生读取 CSV 进入阶段表
3. `MERGE_ODS`：按 `order_month` 增量写入 ODS
4. `BUILD_DWD_ADS`：仅重建受影响月份的 DWD/ADS
5. `PUBLISH`：发布数据版本，页面只读取已发布版本

## 核心口径

- 主统计日期：按下单日期
- 有效订单：完成订单 + 支付后取消且支付到取消时长大于 5 分钟
- 超时取消：下单到取消时长大于 5 分钟
- 新骑手：按骑手入职时间
- 新商家：按商家注册时间
- 新合伙人：按合伙人开城/成立时间
- 补贴归属：
  - 总部优惠金额且无营销优惠券 ID：总部补贴
  - 总部优惠金额且有营销优惠券 ID：合伙人补贴
  - 优惠金额：合伙人补贴

## 文档位置

项目方案、口径手册、字段字典和优化清单统一放在：`F:\codex\delivery-dashboard\docs`
