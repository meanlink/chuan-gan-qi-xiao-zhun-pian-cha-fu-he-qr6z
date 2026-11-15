from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from src.config.database import get_db
from src.models import Lab, User, Dataset, LabClaim
from src.middlewares.auth import platform_admin_only
from src.services.claims import claim_chain, pending_chains, conflicts, claim_dict, ClaimConflict
from src.services.audit import record
from src.utils.security import hash_password
import time
router=APIRouter(prefix='/platform')

class LabInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=2, max_length=40)

class UserInput(BaseModel):
    email: str = Field(max_length=150)
    name: str = Field(max_length=80)
    role: str
    password: str = Field(default='', max_length=200)
    lab_id: int | None = None

class UserReassign(BaseModel):
    lab_id: int | None = None
    role: str | None = None

class ClaimInput(BaseModel):
    dataset_id: int
    lab_id: int

def _lab_dict(l):
    return {'id':l.id,'name':l.name,'code':l.code,'created_at':l.created_at}

def _user_dict(db,u):
    lab=db.get(Lab,u.lab_id) if u.lab_id else None
    return {'id':u.id,'email':u.email,'name':u.name,'role':u.role,
            'lab_id':u.lab_id,'lab_name':lab.name if lab else None}

BUSINESS_ROLES=('admin','analyst','viewer')

@router.get('/labs')
def list_labs(db=Depends(get_db),_=Depends(platform_admin_only)):
    return [_lab_dict(l) for l in db.scalars(select(Lab).order_by(Lab.id))]

@router.post('/labs',status_code=201)
def create_lab(data:LabInput,db=Depends(get_db),u=Depends(platform_admin_only)):
    if db.scalar(select(Lab).where(Lab.name==data.name.strip())):
        raise HTTPException(409,'实验室名称已存在')
    if db.scalar(select(Lab).where(Lab.code==data.code.strip())):
        raise HTTPException(409,'实验室编码已存在')
    l=Lab(name=data.name.strip(),code=data.code.strip(),created_at=time.time())
    db.add(l);db.flush()
    record(db,u.email,'lab.create',{'id':l.id,'code':l.code})
    db.commit();return _lab_dict(l)

@router.get('/users')
def list_users(db=Depends(get_db),_=Depends(platform_admin_only)):
    return [_user_dict(db,x) for x in db.scalars(select(User).order_by(User.id))]

@router.post('/users',status_code=201)
def create_user(data:UserInput,db=Depends(get_db),u=Depends(platform_admin_only)):
    if db.scalar(select(User).where(User.email==data.email)):
        raise HTTPException(409,'账号邮箱已存在')
    lab_id=None
    if data.role=='platform_admin':
        lab_id=None
    else:
        if data.role not in BUSINESS_ROLES:
            raise HTTPException(422,'业务角色须为 admin / analyst / viewer')
        if not data.lab_id or not db.get(Lab,data.lab_id):
            raise HTTPException(422,'业务账号必须归属一个已存在的实验室')
        lab_id=data.lab_id
    if not data.password:
        raise HTTPException(422,'新建账号需要初始密码')
    user=User(email=data.email,name=data.name,role=data.role,
              password=hash_password(data.password),lab_id=lab_id)
    db.add(user);db.flush()
    record(db,u.email,'user.create',{'id':user.id,'lab_id':lab_id,'role':data.role})
    db.commit();return _user_dict(db,user)

@router.post('/users/{id}/assign')
def assign_user(id:int,data:UserReassign,db=Depends(get_db),u=Depends(platform_admin_only)):
    target=db.get(User,id)
    if not target:raise HTTPException(404,'账号不存在')
    role=data.role or target.role
    if role=='platform_admin':
        target.role='platform_admin';target.lab_id=None
    else:
        if role not in BUSINESS_ROLES:
            raise HTTPException(422,'业务角色须为 admin / analyst / viewer')
        if not data.lab_id or not db.get(Lab,data.lab_id):
            raise HTTPException(422,'业务账号必须归属一个已存在的实验室')
        target.role=role;target.lab_id=data.lab_id
    record(db,u.email,'user.assign',{'id':id,'lab_id':target.lab_id,'role':target.role})
    db.commit();return _user_dict(db,target)

@router.get('/claims/pending')
def claim_pending(db=Depends(get_db),_=Depends(platform_admin_only)):
    return pending_chains(db)

@router.get('/claims/conflicts')
def claim_conflicts(db=Depends(get_db),_=Depends(platform_admin_only)):
    return conflicts(db)

@router.post('/claims')
def make_claim(data:ClaimInput,db=Depends(get_db),u=Depends(platform_admin_only)):
    if not db.get(Dataset,data.dataset_id):
        raise HTTPException(404,'数据批次不存在')
    try:
        rec=claim_chain(db,data.dataset_id,data.lab_id,u.email)
    except ClaimConflict as exc:
        record(db,u.email,'claim.conflict',{'dataset_id':data.dataset_id,'lab_id':data.lab_id})
        db.commit()
        raise HTTPException(409,exc.reason)
    record(db,u.email,'claim.chain',{'dataset_id':data.dataset_id,'lab_id':data.lab_id,'detail':rec.detail})
    db.commit()
    return claim_dict(rec)
