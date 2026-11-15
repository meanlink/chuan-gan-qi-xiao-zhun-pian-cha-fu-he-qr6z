# 传感器校准偏差复核

Bootstrap 区间估计的真实业务分析小型项目。完整模拟客户、痛点、上下游、算法公式与一天工作剧本见 [BUSINESS.md](BUSINESS.md)。

## 模块与业务流程
数据接入（JSON/CSV、字段验证、批次指纹）→ 参数化分析（异步 Python worker）→ 结果复核（指标、图形、明细、解释、批准）→ 定时分发（本地收件箱、CSV/JSON、SHA256）；另有业务总览和审计轨迹。
三个贯穿全栈的实体：Dataset 数据批次、Job 分析任务、Report 分发计划；辅助 User、Lab、LabClaim、Audit、Delivery。

## 多实验室隔离
多家实验室共用一套系统，账号归属实验室后，**接入、分析、批准、分发与下载全部按 `lab_id` 归属隔离**：列表只返回本实验室数据，详情/操作按主键二次校验，越权编号与不存在统一返回 404，不泄露其他实验室数据。批次名唯一约束为 `(lab_id, name)`，**同一批次名可在不同实验室分别使用**。
- 角色新增 `platform_admin`（平台管理员，不归属实验室）：管理实验室、设定账号归属、认领旧数据链、查看冲突；不能参与任何实验室业务操作。业务角色 admin/analyst/viewer 必须归属一个实验室。
- **旧数据迁移与认领**：升级迁移只补列不删数据，历史行 `lab_id` 为空即处于待认领冻结态——对业务账号不可见，worker 不执行其排队任务、不发布其到期计划。平台管理员在「实验室与归属」页按批次把 批次→分析→计划→归档**整链认领**给一个实验室。
- 认领是单事务：链上任一实体已归属其他实验室即判定**归属冲突并整次回滚**，保留原归属；并发认领靠 `SELECT ... FOR UPDATE` 串行化，只允许一家成功；对同一实验室重试为幂等成功，保持原归属。
- 认领期间以 `lab_id IS NULL` 作为后台任务的发布闸门，不会提前发布；认领不改动 `enabled`，提交后计划**按原状态恢复**（原本暂停的继续暂停）。归档文件内容保持原样，认领只补归属，不重写 CSV/JSON 与校验指纹。

## 快速启动
```bash
cp .env.example .env
docker compose up -d --build --wait
docker compose exec -T backend python -m scripts.seed_demo
```
访问 http://localhost:18206；后端文档 http://localhost:19206/docs；数据库宿主端口 17706。
`SEED_DEMO=true` 自动幂等 seed；不覆盖用户修改。手动 seed 命令可重复执行。
**已升级的旧库**没有平台管理员账号时，执行 `docker compose exec -T backend python -m scripts.ensure_platform_admin` 幂等引导一个（可用 `PLATFORM_ADMIN_EMAIL` / `PLATFORM_ADMIN_PASSWORD` 指定，否则生成一次性随机密码）。

## 演示账号与权限
|账号|密码|归属实验室|真实权限|
|---|---|---|---|
|platform@demo.local|Demo123!|不归属（平台）|实验室/账号归属管理、旧数据整链认领、冲突查看|
|admin@demo.local|Demo123!|望衡仪器校准实验室|本室接入、执行、批准、分发、暂停、读取与下载|
|analyst@demo.local|Demo123!|望衡仪器校准实验室|本室接入、执行、读取与下载；不能批准或安排分发|
|viewer@demo.local|Demo123!|望衡仪器校准实验室|本室只读与下载|
|qh-admin@demo.local|Demo123!|启衡计量校准实验室|同 admin，数据与望衡完全隔离|
|qh-analyst@demo.local|Demo123!|启衡计量校准实验室|同 analyst|
|qh-viewer@demo.local|Demo123!|启衡计量校准实验室|同 viewer|

## 技术与本地开发
Python 3.12 / FastAPI / SQLAlchemy / NumPy / SciPy / scikit-learn；PostgreSQL 16；Redis 7；Nginx；原生 HTML CSS JavaScript ES modules（用户指定）。后端所有校验、持久化和算法在服务端。无前端打包步骤。
后端：安装 backend/requirements.txt，设置 DATABASE_URL、REDIS_URL、JWT_SECRET、ARTIFACT_DIR 后在 backend/ 执行 `python -m migrations.initial`、`python -m scripts.seed_demo`、`uvicorn src.main:app`，另开 `python -m src.worker`。前端使用带 /api 反向代理的 Nginx，直接打开 index.html 不支持 API。

## 目录与工程约定
backend/src/{models,schemas,services,routes,controllers,middlewares,constants,config,utils}；backend/scripts/seed_demo.py、backend/scripts/ensure_platform_admin.py；backend/migrations/initial.py（幂等，支持旧库补列升级）。
frontend/src/{api,stores,types,components/common,hooks,pages,router,utils,constants}。
Role 枚举：platform_admin/admin/analyst/viewer；JobStatus：queued/running/completed/failed；ClaimStatus：pending/claimed/conflict。后端 backend/src/constants/enums.py，前端 frontend/src/constants/enums.js；路由权限在 middlewares/auth.py，归属过滤统一走 services/tenancy.py，认领事务在 services/claims.py；页面按相同角色控制操作入口。

## 环境变量与 Docker
COMPOSE_PROJECT_NAME=sensor-bootstrap；FRONTEND_PORT=18206；BACKEND_PORT=19206；DB_PORT=17706；DB_PASSWORD、JWT_SECRET 见 .env.example；SEED_DEMO 默认 true。共享命名产物卷供后端下载与 worker 写入，数据库/Redis 各持久卷。
恰好五服务均有健康检查。Redis 队列加 SQL 排队状态兜底；worker 按 next_run 生成本地收件箱文件。周期 60 秒至 30 天。分发结果为批准分析的固定快照；若需新数据重新计算并建立新计划。当前不连接邮件或企业聊天。
错误响应、请求编号、Redis 每 IP 每分钟 240 次限流、JWT 和数据库操作审计。演示密钥与密码仅供本机模拟；生产部署前配置独立密钥与账号。

## 数据与验收
所有数据为固定随机种子生成的模拟业务数据，不能作为实际生产决策证据。项目独立算法、输入边界及业务局限详见 BUSINESS.md。测试与截图统一存放 ../../test-artifacts/gb-1007/，源码不含日志/截图/测试报告。
清理本项目演示数据：`docker compose down -v --remove-orphans`（会删除本项目命名卷）。

## License
MIT，见 LICENSE。
