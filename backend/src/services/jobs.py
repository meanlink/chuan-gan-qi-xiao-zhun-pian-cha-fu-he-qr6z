import time
from fastapi import HTTPException
from redis import Redis
from sqlalchemy import select
from src.config.settings import REDIS_URL
from src.models import Dataset, Job
from src.services.business import metadata
from src.services.tenancy import require_lab, get_scoped
def create(db, data, user):
    lab_id = require_lab(user)
    # 越权编号按不存在处理；get_scoped 同时保证批次已归属本实验室（未认领旧数据对业务账号不可见）。
    d = get_scoped(db, Dataset, data.dataset_id, user)
    allowed={p['key']:p for p in metadata().get('parameters',[])}
    if set(data.params)-set(allowed): raise HTTPException(422,'包含未知分析参数')
    params={k:p['default'] for k,p in allowed.items()}
    params.update(data.params)
    for key,p in allowed.items():
        v=params[key]
        if p['type']=='number':
            try:
                v=float(v)
                if not (p.get('min',-1e9)<=v<=p.get('max',1e9)): raise ValueError()
                params[key]=v
            except (ValueError,TypeError): raise HTTPException(422, f'{p["label"]} 超出范围或非数值')
        elif str(v) not in [str(o['value']) for o in p.get('options',[])]:
            raise HTTPException(422,f'{p["label"]} 不是有效选项')
    j=Job(name=data.name, dataset_id=d.id, params=params, created_by=user.id, created_at=time.time(), status='queued', lab_id=lab_id)
    db.add(j); db.flush()
    return j
def enqueue(job_id):
    try:
        r=Redis.from_url(REDIS_URL); r.rpush('analysis:queue',job_id); r.close()
    except Exception:
        pass # SQL queued status is the durable fallback
