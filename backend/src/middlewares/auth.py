from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.config.database import get_db
from src.models import User
from src.utils.security import decode_token
bearer = HTTPBearer(auto_error=False)
def current_user(token: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(get_db)):
    try:
        user = db.get(User, decode_token(token.credentials))
        if user is None: raise ValueError('missing user')
        return user
    except Exception:
        raise HTTPException(401, '登录已过期，请重新登录')
def platform_admin_only(user=Depends(current_user)):
    if user.role != 'platform_admin': raise HTTPException(403, '需要平台管理员权限')
    return user
def can_write(user=Depends(current_user)):
    if user.role == 'platform_admin': raise HTTPException(403, '平台管理员不参与实验室业务操作')
    if user.role not in ('admin','analyst'): raise HTTPException(403, '观察员只有读取权限')
    if not user.lab_id: raise HTTPException(403, '账号尚未归属实验室，请联系平台管理员')
    return user
def admin_only(user=Depends(current_user)):
    if user.role == 'platform_admin': raise HTTPException(403, '平台管理员不参与实验室业务操作')
    if user.role != 'admin': raise HTTPException(403, '需要业务负责人批准')
    if not user.lab_id: raise HTTPException(403, '账号尚未归属实验室，请联系平台管理员')
    return user
def lab_user(user=Depends(current_user)):
    """业务页面只对归属实验室的账号开放；平台管理员走独立管理接口。"""
    if user.role == 'platform_admin' or not user.lab_id:
        raise HTTPException(403, '该页面仅对归属实验室的业务账号开放')
    return user
