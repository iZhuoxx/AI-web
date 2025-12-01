## AI Toolbox


## 快速开始


### 本地部署

- 拉取项目，安装依赖

```bash
cd web
pnpm install
pnpm run build
```

```bash
cp -r web/dist api/dist
cd api
pip install -r requirements.txt
```

- 启动项目


```bash
# 启动前端
cd web
pnpm run dev
```

```bash
# 启动后端
python3 -m uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

```bash
#启动Postgre数据库
docker start postgres
psql -h localhost -U noteai -d appdb

c常用查看命令
\dt,列出表,列出当前模式下所有的表（tables）。
\dt+,列出表（详细）,列出表，并显示更多细节，如大小、描述等。
\d,列出所有关系,列出所有的关系（包括表、视图、序列、索引等）。
\d [表名],查看表结构,查看特定表的详细结构、列信息、索引和约束。
\l,列出数据库,列出当前 PostgreSQL 服务器上的所有数据库。
\c [数据库名],切换数据库,切换到另一个数据库。
\q,退出 psql,退出 PostgreSQL 客户端。

```


登录数据库：psql -h localhost -U noteai -d appdb

update the table → PYTHONPATH=.. poetry run alembic revision --autogenerate -m "Comments" → PYTHONPATH=.. poetry run alembic upgrade head
在此之前可以先确认当前迁移状态，避免你已经在最新 head 上重复生成文件。常用指令：

PYTHONPATH=.. poetry run alembic current 看当前数据库的 revision
PYTHONPATH=.. poetry run alembic heads 看最新的 head 是什么

### 语音转写

- 新增 `POST /api/audio/transcriptions` 接口，支持 mp3、wav、webm 等常见音频，默认使用 `gpt-4o-transcribe` 模型，返回纯文本结果。
- 前端的附件按钮支持文本、PDF 与音频（mp3、wav 等），音频在选中后将立即后台并行转写，发送前系统会自动等待转写完成并附带识别文本。
- 麦克风按钮可直接录音：再次点击会触发后台转写并把识别文字填入输入框，可确认或继续编辑后发送。
