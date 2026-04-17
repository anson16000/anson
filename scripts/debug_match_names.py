import shutil
from pathlib import Path

import duckdb


def main() -> None:
    db_path = Path(r"F:\codex\delivery-dashboard\db\delivery_analysis.duckdb")
    print(f"db_exists={db_path.exists()} path={db_path}")
    temp_path = db_path.with_name("delivery_analysis_debug_copy.duckdb")
    shutil.copy2(db_path, temp_path)
    print(f"copied_to={temp_path}")
    con = duckdb.connect(str(temp_path), read_only=True)
    queries = {
        "rider_roster_sample": """
            select rider_id, rider_name
            from rider_roster
            where rider_id is not null
            order by rider_id
            limit 20
        """,
        "merchant_roster_sample": """
            select merchant_id, merchant_name
            from merchant_roster
            where merchant_id is not null
            order by merchant_id
            limit 20
        """,
        "rider_unmatched": """
            select
                d.rider_id,
                max(d.rider_name) as dwd_name,
                max(r.rider_name) as roster_name,
                count(*) as order_rows
            from dwd_order_detail d
            left join rider_roster r on d.rider_id = r.rider_id
            where d.rider_id is not null
            group by d.rider_id
            having max(coalesce(r.rider_name, '')) = ''
            order by order_rows desc
            limit 20
        """,
        "merchant_unmatched": """
            select
                d.merchant_id,
                max(d.merchant_name) as dwd_name,
                max(m.merchant_name) as roster_name,
                count(*) as order_rows
            from dwd_order_detail d
            left join merchant_roster m on d.merchant_id = m.merchant_id
            where d.merchant_id is not null
            group by d.merchant_id
            having max(coalesce(m.merchant_name, '')) = ''
            order by order_rows desc
            limit 20
        """,
        "rider_dot_zero": """
            select rider_id, rider_name
            from rider_roster
            where rider_id like '%.0'
            limit 20
        """,
        "merchant_dot_zero": """
            select merchant_id, merchant_name
            from merchant_roster
            where merchant_id like '%.0'
            limit 20
        """,
    }
    for name, sql in queries.items():
        print(f"\n== {name} ==")
        rows = con.execute(sql).fetchall()
        for row in rows:
            print(row)


if __name__ == "__main__":
    main()
