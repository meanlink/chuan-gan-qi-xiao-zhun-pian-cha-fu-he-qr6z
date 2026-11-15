"""旧数据整链认领：平台管理员按批次把 批次→分析→计划→归档 一次性划归一个实验室。

规则：
- 认领是一个事务：链上任一实体已归属其他实验室即判定冲突，整次回滚，不留半归属。
- 并发认领靠行锁 + 唯一约束保证只有一家成功；重试保持原归属（已归属本实验室即幂等成功）。
- 认领期间后台任务不得提前发布：未认领实体 lab_id 为空，worker 到期查询与 deliver()
  均以 lab_id 非空为前提；认领不改动 enabled，提交后计划按原状态恢复（暂停的继续暂停）。
"""
import time
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, OperationalError
from src.models import Dataset, Job, Report, Delivery, Lab, LabClaim

class ClaimConflict(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason

def _lock_dataset(db, dataset_id):
    # SELECT ... FOR UPDATE 串行化同一批次的并发认领；SQLite 退化为普通查询。
    if db.bind.dialect.name == 'sqlite':
        dataset = db.get(Dataset, dataset_id)
    else:
        dataset = db.execute(
            select(Dataset).where(Dataset.id == dataset_id).with_for_update()
        ).scalar_one_or_none()
    return dataset

def pending_chains(db):
    """所有待认领批次（lab_id 为空），附带链路统计与冲突/认领记录。"""
    rows = []
    for d in db.scalars(select(Dataset).where(Dataset.lab_id.is_(None)).order_by(Dataset.id)):
        job_ids = list(db.scalars(select(Job.id).where(Job.dataset_id == d.id)))
        report_ids = list(db.scalars(select(Report.id).where(Report.job_id.in_(job_ids)))) if job_ids else []
        delivery_count = db.scalar(
            select(func.count()).select_from(Delivery).where(Delivery.report_id.in_(report_ids))
        ) if report_ids else 0
        claims = db.scalars(select(LabClaim).where(LabClaim.dataset_id == d.id).order_by(LabClaim.id.desc())).all()
        rows.append({
            'dataset_id': d.id, 'dataset_name': d.name,
            'jobs': len(job_ids), 'reports': len(report_ids),
            'deliveries': 1 if delivery_count else 0,
            'claims': [claim_dict(c) for c in claims],
        })
    return rows

def conflicts(db):
    return [claim_dict(c) for c in db.scalars(
        select(LabClaim).where(LabClaim.status == 'conflict').order_by(LabClaim.id.desc()))]

def claim_chain(db, dataset_id, lab_id, actor):
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(404, '目标实验室不存在')
    now = time.time()
    try:
        # 保存点保证冲突时只回滚本次认领，外层连接仍可写入 conflict 记录。
        savepoint = db.begin_nested()
        try:
            dataset = _lock_dataset(db, dataset_id)
            if dataset is None:
                raise ClaimConflict('数据批次不存在')
            job_ids = list(db.scalars(select(Job.id).where(Job.dataset_id == dataset.id)))
            report_ids = list(db.scalars(select(Report.id).where(Report.job_id.in_(job_ids)))) if job_ids else []

            # 冲突检测：链上任一实体已归属其他实验室 → 整次回滚。
            owned = set()
            if dataset.lab_id is not None:
                owned.add(('批次', dataset.lab_id))
            for jid in job_ids:
                j = db.get(Job, jid)
                if j.lab_id is not None:
                    owned.add(('分析任务', j.lab_id))
            for rid in report_ids:
                r = db.get(Report, rid)
                if r.lab_id is not None:
                    owned.add(('分发计划', r.lab_id))
            for delivery in db.scalars(select(Delivery).where(Delivery.report_id.in_(report_ids))):
                if delivery.lab_id is not None:
                    owned.add(('归档', delivery.lab_id))
            foreign = {lid for _, lid in owned if lid != lab_id}
            if foreign:
                names = '、'.join(sorted({kind for kind, lid in owned if lid in foreign}))
                raise ClaimConflict(f'链路中{names}已归属其他实验室，为避免半归属本次认领整体回滚')

            # 幂等重试：整条链已属于目标实验室，保持原归属，直接返回成功。
            already = dataset.lab_id == lab_id and all(
                db.get(Job, jid).lab_id == lab_id for jid in job_ids
            ) and all(db.get(Report, rid).lab_id == lab_id for rid in report_ids)

            # 冻结与恢复：认领前所有计划 lab_id 为空，worker 的到期查询与 deliver() 均以
            # lab_id 非空为发布前提，因此认领期间不会提前发布；这里不修改 enabled，
            # 认领提交后计划天然按原 enabled 状态恢复，原本暂停的计划继续保持暂停。
            enabled_reports = [rid for rid in report_ids if db.get(Report, rid).enabled]

            # 统一写入归属。
            dataset.lab_id = lab_id
            for jid in job_ids:
                job = db.get(Job, jid)
                job.lab_id = lab_id
                # 迁移窗口内 worker 崩溃遗留的 running 旧任务：认领后重新排队，避免永久卡死。
                if job.status == 'running':
                    job.status = 'queued'
                    job.finished_at = None
                    job.error = ''
            for rid in report_ids:
                db.get(Report, rid).lab_id = lab_id
            for delivery in db.scalars(select(Delivery).where(Delivery.report_id.in_(report_ids))):
                delivery.lab_id = lab_id

            record = LabClaim(dataset_id=dataset_id, lab_id=lab_id, status='claimed',
                              actor=actor, detail={'jobs': len(job_ids), 'reports': len(report_ids),
                                                   'restored_enabled_reports': enabled_reports,
                                                   'retry': already},
                              conflict_reason='', created_at=now, updated_at=now)
            db.add(record)
            savepoint.commit()
            return record
        except ClaimConflict as exc:
            savepoint.rollback()
            db.add(LabClaim(dataset_id=dataset_id, lab_id=lab_id, status='conflict',
                            actor=actor, detail={}, conflict_reason=exc.reason,
                            created_at=now, updated_at=now))
            raise
        except IntegrityError as exc:
            savepoint.rollback()
            reason = '并发认领冲突：该批次已被其他实验室认领，请刷新后重试'
            db.add(LabClaim(dataset_id=dataset_id, lab_id=lab_id, status='conflict',
                            actor=actor, detail={}, conflict_reason=reason,
                            created_at=now, updated_at=now))
            raise ClaimConflict(reason) from exc
        except OperationalError as exc:
            # SQLite 等无行锁数据库的并发写入冲突；PostgreSQL 走 FOR UPDATE 不会进入这里。
            savepoint.rollback()
            reason = '并发认领冲突：该批次正被其他管理员处理，请刷新后重试'
            raise ClaimConflict(reason) from exc
    except ClaimConflict:
        raise

def claim_dict(c):
    return {'id': c.id, 'dataset_id': c.dataset_id, 'lab_id': c.lab_id, 'status': c.status,
            'actor': c.actor, 'detail': c.detail, 'conflict_reason': c.conflict_reason,
            'created_at': c.created_at, 'updated_at': c.updated_at}
