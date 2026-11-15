"""为已升级的旧库引导一个平台管理员账号（幂等，可重复执行）。

用法：
  python -m scripts.ensure_platform_admin                 # 用默认演示邮箱，生成随机密码并打印
  PLATFORM_ADMIN_EMAIL=ops@lab.local PLATFORM_ADMIN_PASSWORD=... python -m scripts.ensure_platform_admin

平台管理员不归属任何实验室，负责建立实验室、设定账号归属、认领旧数据链与查看冲突。
"""
import os, secrets, sys
from sqlalchemy import select
from src.config.database import Session
from migrations.initial import migrate
from src.models import User
from src.utils.security import hash_password

def ensure():
    migrate()
    email = os.getenv('PLATFORM_ADMIN_EMAIL', 'platform@demo.local')
    password = os.getenv('PLATFORM_ADMIN_PASSWORD') or ('Init-' + secrets.token_urlsafe(12))
    with Session() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            changed = False
            if user.role != 'platform_admin':
                user.role = 'platform_admin'; changed = True
            if user.lab_id is not None:
                user.lab_id = None; changed = True
            if os.getenv('PLATFORM_ADMIN_PASSWORD'):
                user.password = hash_password(password); changed = True
            db.commit()
            print(f'平台管理员已存在：{email}' + ('（已校正角色与归属）' if changed else '（无需变更）'))
            if os.getenv('PLATFORM_ADMIN_PASSWORD'):
                print('密码已按环境变量 PLATFORM_ADMIN_PASSWORD 更新。')
            return
        user = User(email=email, name='平台管理员', role='platform_admin',
                    password=hash_password(password), lab_id=None)
        db.add(user); db.commit()
        print(f'已创建平台管理员：{email}')
        if not os.getenv('PLATFORM_ADMIN_PASSWORD'):
            print(f'初始密码（仅显示一次，请立即登录并改密）：{password}')

if __name__ == '__main__':
    ensure()
