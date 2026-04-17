from pathlib import Path
import sys
ROOT = Path(r"F:\codex\delivery-dashboard")
sys.path.insert(0, str(ROOT))
from app.models import OrderDetailRaw
print(list(OrderDetailRaw.__table__.c.keys()))
print({name: idx for idx, name in enumerate(OrderDetailRaw.__table__.c.keys())})
