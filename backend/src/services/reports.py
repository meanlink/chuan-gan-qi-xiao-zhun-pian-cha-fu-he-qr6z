import time, os, csv, io, hashlib, json
from fastapi import HTTPException
from src.models import Job, Report, Delivery
from src.config.settings import ARTIFACT_DIR
from src.services.tenancy import require_lab, get_scoped
def create(db, data, user):
    lab_id = require_lab(user)
    # 越权编号按不存在处理；get_scoped 保证任务已归属本实验室（未认领旧数据不可见）。
    j = get_scoped(db, Job, data.job_id, user)
    if j.status!='completed' or not j.approved:
        raise HTTPException(409,'请先选择已完成且获批准的分析结果')
    r=Report(name=data.name, job_id=j.id, destination=data.destination, interval_seconds=data.interval_seconds, next_run=time.time()+data.delay_seconds, enabled=True, lab_id=lab_id)
    db.add(r); db.flush()
    return r
def deliver(db, report):
    # 未认领旧链路（lab_id 为空）在认领前一律不得分发。
    if report.lab_id is None:
        return None
    j=db.get(Job,report.job_id)
    if not j or not j.approved or j.lab_id is None: return None
    out=io.StringIO()
    out.write('﻿')
    table=j.result.get('table',{})
    cols=table.get('columns',[])
    writer=csv.writer(out)
    def safe(v):
        if isinstance(v,(int,float)) and not isinstance(v,bool): return v
        text=str(v)
        return "'"+text if text.startswith(('=','+','-','@','\t','\r')) else text
    writer.writerow([safe(c['label']) for c in cols])
    for row in table.get('rows',[]): writer.writerow([safe(row.get(c['key'],'')) for c in cols])
    data=out.getvalue().encode('utf-8')
    delivery=Delivery(report_id=report.id, created_at=time.time(), checksum=hashlib.sha256(data).hexdigest(), filename='', destination=report.destination, lab_id=report.lab_id)
    db.add(delivery); db.flush()
    delivery.filename=f'report-{report.id}-delivery-{delivery.id}.csv'
    os.makedirs(ARTIFACT_DIR,exist_ok=True)
    with open(os.path.join(ARTIFACT_DIR,delivery.filename),'wb') as f:f.write(data)
    # 归档内容保持原样：沿用既有快照口径，认领只改归属不改文件内容。
    with open(os.path.join(ARTIFACT_DIR,delivery.filename+'.json'),'w') as f: json.dump({'job':j.name,'params':j.params,'result':j.result,'checksum':delivery.checksum},f,ensure_ascii=False,allow_nan=False)
    report.next_run=time.time()+report.interval_seconds
    return delivery
