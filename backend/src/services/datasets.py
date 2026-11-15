from fastapi import HTTPException
from sqlalchemy import select
from src.models import Dataset
from src.services.business import metadata
from src.services.tenancy import require_lab
from src.utils.serialization import checksum
import math, time
def create(db, data, user):
    lab_id = require_lab(user)
    name=data.name.strip()
    if len(name)<2: raise HTTPException(422, '批次名称去除空格后至少需要两个字符')
    # 同一批次名可在不同实验室使用；同实验室内仍保持唯一。
    if db.scalar(select(Dataset).where(Dataset.name==name, Dataset.lab_id==lab_id)):
        raise HTTPException(409, '该数据批次名在本实验室已存在，请修改名称')
    for index,row in enumerate(data.records):
        for c in metadata()['columns']:
            value=row.get(c['key'])
            if value is None or value=='': raise HTTPException(422, f'第 {index+1} 行缺少字段 {c["label"]}')
            if c['type']=='number':
                try:
                    if isinstance(value,bool) or not math.isfinite(float(value)): raise ValueError()
                    row[c['key']]=float(value)
                except (TypeError, ValueError, OverflowError): raise HTTPException(422, f'第 {index+1} 行 {c["label"]} 必须为有限数值')
    d=Dataset(name=name, source=data.source, records=data.records, checksum=checksum(data.records), created_at=time.time(), lab_id=lab_id)
    db.add(d); db.flush()
    return d
