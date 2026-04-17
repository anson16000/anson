from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    base = datetime(2026, 4, 1, 9, 0, 0)
    partners = [
        {"ID": "1", "合伙人公司名": "广东帮啦网络技术有限公司", "成立时间": "2026-03-20", "合伙人区域": "广东省-梅州市-梅江区", "状态": "开启"},
        {"ID": "2", "合伙人公司名": "山西亨派信息科技有限公司", "成立时间": "2025-12-01", "合伙人区域": "山西省-忻州市-原平市", "状态": "开启"},
    ]
    riders = [
        {"帮手ID": "3001", "帮手姓名": "张三", "入职时间": "2026-03-28", "状态": "正常", "所属合伙人": "广东帮啦网络技术有限公司", "区域": "广东省-梅州市-梅江区"},
        {"帮手ID": "3002", "帮手姓名": "李四", "入职时间": "2025-12-10", "状态": "正常", "所属合伙人": "山西亨派信息科技有限公司", "区域": "山西省-忻州市-原平市"},
    ]
    merchants = [
        {"商家ID": "1001", "商家名称": "测试商家A", "所属合伙人": "广东帮啦网络技术有限公司", "所属区域": "广东省-梅州市-梅江区", "注册时间": "2026-03-30", "状态": "正常"},
        {"商家ID": "1002", "商家名称": "测试商家B", "所属合伙人": "山西亨派信息科技有限公司", "所属区域": "山西省-忻州市-原平市", "注册时间": "2025-12-15", "状态": "正常"},
    ]

    orders: list[dict] = []
    for day in range(7):
        for hour in range(9, 22):
            order_time = base + timedelta(days=day, hours=(hour - 9))
            orders.append(
                {
                    "订单编号": f"ORD-{day}-{hour}-1",
                    "合伙人ID": "1",
                    "合伙人": "广东帮啦网络技术有限公司",
                    "商家ID": "1001",
                    "商家": "测试商家A",
                    "用户ID": f"U-{hour}",
                    "配送员ID": "3001",
                    "订单状态": "已送达",
                    "添加时间": order_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "支付时间": order_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "取消时间": "",
                    "完成时间": (order_time + timedelta(minutes=35)).strftime("%Y-%m-%d %H:%M:%S"),
                    "总部优惠金额": "1.2",
                    "营销优惠劵ID": "",
                    "优惠金额": "0.3",
                }
            )
            cancel_time = order_time + timedelta(minutes=10)
            orders.append(
                {
                    "订单编号": f"ORD-{day}-{hour}-2",
                    "合伙人ID": "2",
                    "合伙人": "山西亨派信息科技有限公司",
                    "商家ID": "1002",
                    "商家": "测试商家B",
                    "用户ID": f"U-{hour}-B",
                    "配送员ID": "3002",
                    "订单状态": "已取消（无责）",
                    "添加时间": order_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "支付时间": order_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "取消时间": cancel_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "完成时间": "",
                    "总部优惠金额": "0.6",
                    "营销优惠劵ID": "MK-1",
                    "优惠金额": "0.5",
                }
            )

    write_csv(ROOT / "data" / "partners" / "sample_partners.csv", partners)
    write_csv(ROOT / "data" / "riders" / "sample_riders.csv", riders)
    write_csv(ROOT / "data" / "merchants" / "sample_merchants.csv", merchants)
    write_csv(ROOT / "data" / "orders" / "sample_orders.csv", orders)
    print("Sample files generated.")


if __name__ == "__main__":
    main()
