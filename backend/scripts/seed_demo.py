import time, json
from sqlalchemy import select, func
from src.config.database import Session
from migrations.initial import migrate
from src.models import User, Dataset, Job, Report, Delivery, Audit, Lab, LabClaim
from src.services.business import metadata, seed_records, analyze
from src.services.reports import deliver
from src.utils.security import hash_password
from src.utils.serialization import checksum

LABS=[('望衡仪器校准实验室','WH-LAB'),('启衡计量校准实验室','QH-LAB')]
# 平台管理员不归属实验室；每个实验室各配一套业务账号。
ACCOUNTS=[
    ('platform@demo.local','平台管理员 · 宿岚','platform_admin',None),
    ('admin@demo.local','林知 · 望衡业务负责人','admin',0),
    ('analyst@demo.local','陈舟 · 望衡分析员','analyst',0),
    ('viewer@demo.local','周禾 · 望衡观察员','viewer',0),
    ('qh-admin@demo.local','岑越 · 启衡业务负责人','admin',1),
    ('qh-analyst@demo.local','沈砚 · 启衡分析员','analyst',1),
    ('qh-viewer@demo.local','闻笛 · 启衡观察员','viewer',1),
]
def seed():
    migrate()
    with Session() as db:
        labs=[]
        for name,code in LABS:
            l=db.scalar(select(Lab).where(Lab.code==code))
            if not l:
                l=Lab(name=name,code=code,created_at=time.time());db.add(l);db.flush()
            labs.append(l)
        for email,name,role,lab_idx in ACCOUNTS:
            if not db.scalar(select(User).where(User.email==email)):
                db.add(User(email=email,name=name,role=role,password=hash_password('Demo123!'),
                            lab_id=labs[lab_idx].id if lab_idx is not None else None))
        db.flush()
        m=metadata()
        # 1) 归属望衡实验室的正式演示链路（同名单批次在不同实验室各自存在）。
        d=db.scalar(select(Dataset).where(Dataset.name==m['dataset_name'],Dataset.lab_id==labs[0].id))
        if not d:
            rows=seed_records()
            d=Dataset(name=m['dataset_name'],source=m['short']+'-202611.csv',records=rows,checksum=checksum(rows),created_at=time.time(),lab_id=labs[0].id)
            db.add(d); db.flush()
        if not db.scalar(select(Job).where(Job.name=='基线复核 · '+m['name'],Job.lab_id==labs[0].id)):
            params={p['key']:p['default'] for p in m.get('parameters',[])}
            result=analyze(d.records,params)
            json.dumps(result,ensure_ascii=False,allow_nan=False)
            admin=db.scalar(select(User).where(User.email=='admin@demo.local'))
            j=Job(name='基线复核 · '+m['name'],dataset_id=d.id,params=params,status='completed',result=result,created_by=admin.id,created_at=time.time()-3600,finished_at=time.time()-3595,approved=True,lab_id=labs[0].id)
            db.add(j);db.flush()
            r=Report(name='每日业务复核简报',job_id=j.id,destination='业务复核组 · 本地收件箱',interval_seconds=86400,next_run=time.time()+86400,enabled=True,lab_id=labs[0].id)
            db.add(r);db.flush();deliver(db,r)
            db.add(Audit(actor='seed',action='demo.baseline',detail={'dataset':d.id},at=time.time(),lab_id=labs[0].id))
        # 2) 启衡实验室接入同名批次，验证批次名可跨实验室复用。
        d2=db.scalar(select(Dataset).where(Dataset.name==m['dataset_name'],Dataset.lab_id==labs[1].id))
        if not d2:
            rows2=seed_records()
            d2=Dataset(name=m['dataset_name'],source=m['short']+'-qh-202611.csv',records=rows2,checksum=checksum(rows2),created_at=time.time(),lab_id=labs[1].id)
            db.add(d2);db.flush()
        # 3) 迁移前旧数据：lab_id 全部为空，处于待认领冻结状态，含计划与历史归档。
        legacy_name='历史遗留批次 · T-18 三温区 240 对读数'
        legacy=db.scalar(select(Dataset).where(Dataset.name==legacy_name))
        if not legacy:
            lrows=seed_records()
            legacy=Dataset(name=legacy_name,source='legacy-T18-202609.csv',records=lrows,checksum=checksum(lrows),created_at=time.time()-90*86400,lab_id=None)
            db.add(legacy);db.flush()
            params={p['key']:p['default'] for p in m.get('parameters',[])}
            lresult=analyze(legacy.records,params)
            admin=db.scalar(select(User).where(User.email=='admin@demo.local'))
            lj=Job(name='历史基线复核 · T-18',dataset_id=legacy.id,params=params,status='completed',result=lresult,created_by=admin.id,created_at=time.time()-89*86400,finished_at=time.time()-89*86400+300,approved=True,lab_id=None)
            db.add(lj);db.flush()
            # enabled=True 但 lab_id 为空：worker 必须跳过，等待认领后恢复。
            lr=Report(name='历史每日简报',job_id=lj.id,destination='旧业务复核组 · 本地收件箱',interval_seconds=86400,next_run=time.time()-3600,enabled=True,lab_id=None)
            db.add(lr);db.flush()
            # 认领前已产生的归档内容保持原样，仅归属待补。
            old=deliver_legacy(db,lr)
            db.add(Audit(actor='seed',action='demo.legacy',detail={'dataset':legacy.id},at=time.time(),lab_id=None))
        db.commit()
        counts={model.__tablename__:db.scalar(select(func.count()).select_from(model)) for model in [Lab,User,Dataset,Job,Report,Delivery,Audit,LabClaim]}
        print(json.dumps(counts,ensure_ascii=False))
        return counts

def deliver_legacy(db,report):
    """复刻旧归档：无 lab_id，文件内容与正常分发完全一致。"""
    from src.models import Delivery
    import os,csv,io,hashlib
    from src.config.settings import ARTIFACT_DIR
    j=db.get(Job,report.job_id)
    out=io.StringIO();out.write('﻿')
    table=j.result.get('table',{});cols=table.get('columns',[])
    writer=csv.writer(out)
    writer.writerow([c['label'] for c in cols])
    for row in table.get('rows',[]):writer.writerow([row.get(c['key'],'') for c in cols])
    data=out.getvalue().encode('utf-8')
    delivery=Delivery(report_id=report.id,created_at=time.time()-89*86400,checksum=hashlib.sha256(data).hexdigest(),filename='',destination=report.destination,lab_id=None)
    db.add(delivery);db.flush()
    delivery.filename=f'report-{report.id}-delivery-{delivery.id}.csv'
    os.makedirs(ARTIFACT_DIR,exist_ok=True)
    with open(os.path.join(ARTIFACT_DIR,delivery.filename),'wb') as f:f.write(data)
    with open(os.path.join(ARTIFACT_DIR,delivery.filename+'.json'),'w') as f:json.dump({'job':j.name,'params':j.params,'result':j.result,'checksum':delivery.checksum},f,ensure_ascii=False,allow_nan=False)
    return delivery
if __name__=='__main__':seed()
