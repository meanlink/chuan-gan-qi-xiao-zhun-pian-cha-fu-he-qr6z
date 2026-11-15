import time
from src.models import Audit
def record(db, actor, action, detail=None, lab_id=None):
    db.add(Audit(actor=actor, action=action, detail=detail or {}, at=time.time(), lab_id=lab_id))
