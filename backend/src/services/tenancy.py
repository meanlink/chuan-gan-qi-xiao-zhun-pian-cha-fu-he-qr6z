"""实验室归属隔离的统一入口：所有业务实体按当前账号的 lab_id 过滤，越权编号一律按不存在处理。"""
from fastapi import HTTPException
from sqlalchemy import select
from src.models import Dataset, Job, Report, Delivery

def require_lab(user):
    if not user.lab_id:
        raise HTTPException(403, '账号尚未归属实验室，请联系平台管理员')
    return user.lab_id

def get_scoped(db, model, entity_id, user):
    """按主键取实体并强制归属校验。越权编号与不存在统一返回 404，避免泄露其他实验室数据。"""
    lab_id = require_lab(user)
    entity = db.get(model, entity_id)
    if entity is None or entity.lab_id != lab_id:
        raise HTTPException(404, _not_found_text(model))
    return entity

def _not_found_text(model):
    return {
        Dataset: '数据批次不存在',
        Job: '分析任务不存在',
        Report: '分发计划不存在',
        Delivery: '归档不存在',
    }.get(model, '资源不存在')

def scoped_stmt(model, user):
    return select(model).where(model.lab_id == require_lab(user))
