import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from src.config.database import get_db
from src.config.settings import ARTIFACT_DIR
from src.models import Report, Delivery
from src.schemas.report import ReportInput
from src.middlewares.auth import current_user, admin_only
from src.services import reports
from src.services.tenancy import scoped_stmt, get_scoped
from src.services.audit import record
from src.utils.serialization import report_dict, delivery_dict
router=APIRouter()
@router.get('/reports')
def listing(db=Depends(get_db),u=Depends(current_user)):
    return [report_dict(r) for r in db.scalars(scoped_stmt(Report,u).order_by(Report.id.desc()))]
@router.post('/reports',status_code=201)
def create(data:ReportInput,db=Depends(get_db),u=Depends(admin_only)):
    r=reports.create(db,data,u); record(db,u.email,'report.schedule',{'id':r.id,'destination':r.destination},u.lab_id); db.commit()
    return report_dict(r)
@router.post('/reports/{id}/toggle')
def toggle(id:int,db=Depends(get_db),u=Depends(admin_only)):
    r=get_scoped(db,Report,id,u)
    r.enabled=not r.enabled;record(db,u.email,'report.toggle',{'id':id,'enabled':r.enabled},u.lab_id);db.commit()
    return report_dict(r)
@router.get('/deliveries')
def deliveries(db=Depends(get_db),u=Depends(current_user)):
    return [delivery_dict(d) for d in db.scalars(scoped_stmt(Delivery,u).order_by(Delivery.id.desc()).limit(100))]
@router.get('/deliveries/{id}/download')
def download(id:int,format:str='csv',db=Depends(get_db),u=Depends(current_user)):
    # 下载同样按归属隔离：其他实验室或未认领归档一律拒绝。
    d=get_scoped(db,Delivery,id,u)
    if format not in ('csv','json'):raise HTTPException(422,'支持 CSV 或 JSON')
    filename=d.filename+('.json' if format=='json' else '')
    p=os.path.join(ARTIFACT_DIR,filename)
    if not os.path.exists(p):raise HTTPException(404,'归档文件不存在，请重新安排分发')
    record(db,u.email,'delivery.download',{'id':id,'format':format},u.lab_id);db.commit()
    return FileResponse(p,filename=filename,media_type='application/json' if format=='json' else 'text/csv; charset=utf-8')
