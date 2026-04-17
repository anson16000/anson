from pathlib import Path
import sys
ROOT = Path(r"F:\codex\delivery-dashboard")
sys.path.insert(0, str(ROOT))
from sqlalchemy import text
from app.config import load_settings
from app.database import create_session_factory, session_scope
settings = load_settings()
_, session_factory = create_session_factory(settings)
cols = [
    'raw_id','file_registry_id','batch_id','row_number','order_month','imported_at','order_id','partner_id','partner_name','merchant_id','merchant_name','user_id','rider_id','order_status','added_at','pay_time','cancel_time','complete_time','hq_discount_amount','marketing_coupon_id','discount_amount','raw_payload'
]
with session_scope(session_factory) as session:
    result = session.execute(text(f"SELECT {', '.join(cols)} FROM ods_order_detail_raw LIMIT 1"))
    row = result.first()
    print('keys', list(result.keys()), len(list(result.keys())))
    print('row', type(row), len(row), row)
    for idx, value in enumerate(row):
        print(idx, type(value).__name__, value if idx < 8 else '...')
