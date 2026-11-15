from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from src.config.database import get_db
from src.models import Dataset
from src.schemas.dataset import DatasetInput
from src.middlewares.auth import current_user, can_write
from src.services import datasets
from src.services.tenancy import scoped_stmt, get_scoped
from src.services.audit import record
from src.utils.serialization import dataset_dict
router=APIRouter(prefix='/datasets')
@router.get('')
def listing(db=Depends(get_db),u=Depends(current_user)):
    # 仅返回本实验室已认领/自建批次；未认领旧数据对业务账号不可见。
    return [dataset_dict(d) for d in db.scalars(scoped_stmt(Dataset,u).order_by(Dataset.id.desc()))]
@router.post('',status_code=201)
def create(data:DatasetInput,db=Depends(get_db),u=Depends(can_write)):
    d=datasets.create(db,data,u); record(db,u.email,'dataset.create',{'id':d.id,'rows':len(d.records)},u.lab_id)
    db.commit(); return dataset_dict(d)
@router.get('/{id}')
def detail(id:int,db=Depends(get_db),u=Depends(current_user)):
    # 越权编号与其他实验室批次统一返回 404。
    d=get_scoped(db,Dataset,id,u)
    return {**dataset_dict(d),'records':d.records}
