from pathlib import Path
import sys
ROOT = Path(r"F:\codex\delivery-dashboard")
sys.path.insert(0, str(ROOT))
from app.config import load_settings
from app.database import create_session_factory, session_scope
settings = load_settings()
_, session_factory = create_session_factory(settings)
cols = [
    'raw_id','file_registry_id','batch_id','row_number','order_month','imported_at','order_id','partner_id','partner_name','merchant_id','merchant_name','user_id','rider_id','order_status','added_at','pay_time','cancel_time','complete_time','hq_discount_amount','marketing_coupon_id','discount_amount','raw_payload'
]
months = ['2026-03']
month_sql = ', '.join('?' for _ in months)
sql = f"SELECT {', '.join(cols)} FROM ods_order_detail_raw WHERE order_month IN ({month_sql}) ORDER BY imported_at DESC, row_number DESC"
with session_scope(session_factory) as session:
    driver = session.connection().connection.driver_connection
    cursor = driver.cursor()
    cursor.execute(sql, months)
    print('description_len', len(cursor.description))
    rows = cursor.fetchmany(5)
    print('rows_len', len(rows))
    for idx, row in enumerate(rows):
        print('row', idx, 'tuple_len', len(row), 'sample', row[:8])
    cursor.close()
