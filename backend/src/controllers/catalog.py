from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from src.config.database import get_db
from src.middlewares.auth import current_user
from src.models import Dataset, Job, Report, Audit
from src.services.business import metadata
from src.services.tenancy import require_lab
router=APIRouter()
@router.get('/meta')
def meta():return metadata()
@router.get('/overview')
def overview(db=Depends(get_db),user=Depends(current_user)):
    lab_id=require_lab(user)
    return {
        'datasets':db.scalar(select(func.count()).select_from(Dataset).where(Dataset.lab_id==lab_id)),
        'records':sum(len(d.records) for d in db.scalars(select(Dataset).where(Dataset.lab_id==lab_id))),
        'jobs':db.scalar(select(func.count()).select_from(Job).where(Job.lab_id==lab_id)),
        'approved':db.scalar(select(func.count()).select_from(Job).where(Job.lab_id==lab_id,Job.approved==True)),
        'reports':db.scalar(select(func.count()).select_from(Report).where(Report.lab_id==lab_id))}
@router.get('/audits')
def audits(db=Depends(get_db),user=Depends(current_user)):
    lab_id=require_lab(user)
    rows=db.scalars(select(Audit).where(Audit.lab_id==lab_id).order_by(Audit.id.desc()).limit(50))
    return [{'id':a.id,'actor':a.actor,'action':a.action,'detail':a.detail,'at':a.at} for a in rows]
