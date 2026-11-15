import time, json, logging
from pathlib import Path
from sqlalchemy import select
from redis import Redis
from src.config.database import Session
from src.config.settings import REDIS_URL
from src.models import Job, Dataset, Report
from src.services.business import analyze
from src.services.reports import deliver
from src.services.audit import record
logging.basicConfig(level=logging.INFO)
def execute(job_id):
    with Session() as db:
        j=db.get(Job,job_id)
        # 未认领旧任务保持排队但不执行，等待平台管理员认领后再恢复。
        if not j or j.status!='queued' or j.lab_id is None:return
        j.status='running'; db.commit()
        try:
            d=db.get(Dataset,j.dataset_id)
            if d is None or d.lab_id is None:
                raise RuntimeError('批次尚未完成实验室认领')
            result=analyze(d.records,j.params)
            json.dumps(result,allow_nan=False)
            j.result=result;j.status='completed';j.finished_at=time.time()
            record(db,'worker','job.completed',{'id':j.id},j.lab_id)
        except Exception as e:
            logging.exception('Analysis failed')
            j.status='failed';j.error=str(e)[:990];j.finished_at=time.time()
            record(db,'worker','job.failed',{'id':j.id,'error':j.error},j.lab_id)
        db.commit()
def tick():
    with Session() as db:
        # 仅认领后（lab_id 非空）的排队任务才会被调度。
        queued=list(db.scalars(select(Job.id).where(Job.status=='queued',Job.lab_id.is_not(None)).limit(3)))
    for job_id in queued:execute(job_id)
    with Session() as db:
        # 未认领计划 lab_id 为空，deliver 内部亦有兜底，双重保证认领期间不提前发布。
        due=db.scalars(select(Report).where(Report.enabled==True,Report.next_run<=time.time(),Report.lab_id.is_not(None)))
        for r in due:
            d=deliver(db,r)
            if d:record(db,'worker','report.delivered',{'id':r.id,'delivery':d.id},r.lab_id)
        db.commit()
def main():
    r=Redis.from_url(REDIS_URL,socket_timeout=3)
    # This Compose stack has a single worker. A crash must not strand its jobs.
    with Session() as db:
        for j in db.scalars(select(Job).where(Job.status=='running')):
            # 未认领旧任务不重置，避免在认领窗口内被抢先执行。
            if j.lab_id is None:continue
            j.status='queued';record(db,'worker','job.recovered',{'id':j.id},j.lab_id)
        db.commit()
    while True:
        Path('/tmp/heartbeat').touch()
        try:
            item=r.blpop('analysis:queue',timeout=1)
            if item:execute(int(item[1]))
            tick()
        except Exception:
            logging.exception('Worker retry');time.sleep(2)
if __name__=='__main__':main()
