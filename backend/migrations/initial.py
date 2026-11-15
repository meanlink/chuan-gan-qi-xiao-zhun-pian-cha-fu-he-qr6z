"""幂等迁移：新建库直接建表；已部署旧库补齐多实验室隔离所需列与表，不删除任何数据。"""
from sqlalchemy import text
from src.config.database import Base, engine
from src import models

def _table_exists(conn, table):
    if engine.dialect.name == 'sqlite':
        return bool(conn.execute(text(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=:t"), {'t': table}).first())
    return bool(conn.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name=:t"), {'t': table}).first())

def _columns(conn, table):
    if engine.dialect.name == 'sqlite':
        return {row[1] for row in conn.execute(text(f'PRAGMA table_info("{table}")'))}
    return {row[1] for row in conn.execute(text(
        "SELECT * FROM information_schema.columns WHERE table_name=:t"), {'t': table})}

def migrate():
    Base.metadata.create_all(engine)
    # create_all 不会修改已存在的表，这里为旧库补齐列。
    with engine.begin() as conn:
        if _table_exists(conn, 'users') and 'lab_id' not in _columns(conn, 'users'):
            conn.execute(text('ALTER TABLE users ADD COLUMN lab_id INTEGER'))
        if _table_exists(conn, 'datasets'):
            cols = _columns(conn, 'datasets')
            if 'lab_id' not in cols:
                conn.execute(text('ALTER TABLE datasets ADD COLUMN lab_id INTEGER'))
            if engine.dialect.name == 'sqlite':
                exists = conn.execute(text(
                    "SELECT 1 FROM sqlite_master WHERE type='index' AND name='uq_datasets_lab_name'")).first()
                if not exists:
                    conn.execute(text('CREATE UNIQUE INDEX uq_datasets_lab_name ON datasets(lab_id,name)'))
            else:
                exists = conn.execute(text(
                    "SELECT 1 FROM information_schema.table_constraints WHERE constraint_name='uq_datasets_lab_name'")).first()
                if not exists:
                    conn.execute(text('ALTER TABLE datasets ADD CONSTRAINT uq_datasets_lab_name UNIQUE (lab_id,name)'))
        if _table_exists(conn, 'jobs') and 'lab_id' not in _columns(conn, 'jobs'):
            conn.execute(text('ALTER TABLE jobs ADD COLUMN lab_id INTEGER'))
        if _table_exists(conn, 'reports') and 'lab_id' not in _columns(conn, 'reports'):
            conn.execute(text('ALTER TABLE reports ADD COLUMN lab_id INTEGER'))
        if _table_exists(conn, 'deliveries') and 'lab_id' not in _columns(conn, 'deliveries'):
            conn.execute(text('ALTER TABLE deliveries ADD COLUMN lab_id INTEGER'))
        if _table_exists(conn, 'audits') and 'lab_id' not in _columns(conn, 'audits'):
            conn.execute(text('ALTER TABLE audits ADD COLUMN lab_id INTEGER'))

if __name__ == '__main__':
    migrate()
