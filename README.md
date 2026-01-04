# AI Toolbox

基于 Vue 3 + Vite 前端与 FastAPI 后端的全栈应用，支持会话笔记、文件/音频附件、S3 存储、PostgreSQL 永久化以及 CSRF/Session 登录。

## 项目结构
- `web/`：Vue 3 + TypeScript + Vite 前端，Ant Design Vue 组件库。
- `api/`：FastAPI 后端，SQLAlchemy + Alembic，S3/音频等业务逻辑。
- `docker-compose.yml`：PostgreSQL 16 与 Redis 7 的本地依赖。
- `PROXY.md`：国内网络环境下的代理说明。

## 环境要求
- Node.js ≥ 18，pnpm（或 npm/yarn）。
- Python ≥ 3.8，pip 或 poetry。
- PostgreSQL、Redis（可用 `docker compose` 一键启动）。

## 本地快速开始
1) 启动数据库与缓存（可选）  
```bash
docker compose up -d postgres redis
```
如需自建数据库，确保有可访问的 PostgreSQL 与 Redis 实例。

2) 配置后端环境变量：复制 `api/.env`，填写关键项（与上面 docker-compose 默认账号保持一致）：  
```env
DATABASE_URL=postgresql+psycopg://myuser:mypassword@localhost:5432/mydb
JWT_SECRET_KEY=your-long-random-secret
CSRF_SECRET=another-random-secret
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=lax
AWS_S3_BUCKET=your-bucket
AWS_S3_REGION=ap-northeast-1
AWS_S3_ENDPOINT_URL=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

3) 安装依赖  
```bash
cd web && pnpm install
cd ../api && pip install -r requirements.txt    # 或 poetry install
```

4) 初始化数据库（首次）  
```bash
cd api
alembic upgrade head
```

5) 启动开发服务（两个终端）  
```bash
# 后端：FastAPI + 热重载
cd api
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000

# 前端：Vite 开发服务器，带 /api 代理
cd web
pnpm run dev  # http://localhost:5173
```

## 生产构建与部署
```bash
# 构建前端
cd web && pnpm build

# 启动后端并同时托管前端静态资源
cd ../api
SERVE_SPA=true uvicorn api.app:app --host 0.0.0.0 --port 8000
```
将进程交给 systemd/supervisor，并在外层加反向代理与 TLS 即可。

## 数据库与迁移
- 生成新迁移：`cd api && alembic revision --autogenerate -m "describe change"`  
- 应用迁移：`alembic upgrade head`  
- 常用 `psql`：`\dt` 查看表，`\d <table>` 看结构，`\l` 列数据库，`\q` 退出。

## 前端配置提示
- 默认通过 Vite 代理访问 `http://localhost:8000/api`。如后端域名不同，可在 `web/.env.development` 设置 `VITE_API_BASE_URL=https://your-api.com/api`。
- 流式/转写端点也可在同一文件里设置 `VITE_RESPONSES_ENDPOINT`、`VITE_TRANSCRIBE_STREAM_ENDPOINT`、`VITE_TRANSCRIBE_REALTIME_WS`。

## 语音转写流程
- 选择音频附件或点击麦克风录制后，前端会异步调用 `POST /api/audio/transcriptions`（默认模型 `gpt-4o-transcribe`），完成后把识别文本填入输入框。
- 后端同样支持常规文件上传、S3 预签名上传和下载、以及 OpenAI File linking（见 `api/README.md`）。
