0) 基础扩展 & 类型
-- 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS citext;

-- ENUM（可按需用 CHECK 代替）
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_role') THEN
    CREATE TYPE message_role AS ENUM ('user','assistant','system','tool');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'attachment_kind') THEN
    CREATE TYPE attachment_kind AS ENUM ('pdf','image','audio','video','file','other');  -- 更具实际支持的文件格式而定
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'membership_status') THEN
    CREATE TYPE membership_status AS ENUM ('active','canceled','expired','past_due');
  END IF;
END $$;

1) 用户 & 会员
-- 用户
CREATE TABLE users (
  id             uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  email          citext UNIQUE NOT NULL,
  password_hash  text   NOT NULL,
  name           text,
  is_active      boolean NOT NULL DEFAULT true,
  member_plan    text,                        -- basic/pro/enterprise
  member_until   timestamptz,                 -- 到期前视为会员
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now()
);

-- 订阅流水（历史）
CREATE TABLE memberships (
  id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  plan         text NOT NULL,
  status       membership_status NOT NULL,
  started_at   timestamptz NOT NULL,
  ends_at      timestamptz,
  meta         jsonb,                         -- 第三方支付/发票等
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_memberships_user ON memberships(user_id);

2) 笔记 / 会话（容器）与消息
-- 笔记（或会话容器）
CREATE TABLE notes (
  id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title        text,
  summary      text,
  content      text,                                   -- 可选：主文档正文
  is_archived  boolean NOT NULL DEFAULT false,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  fts tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('simple', coalesce(title,'')),   'A') ||
    setweight(to_tsvector('simple', coalesce(summary,'')), 'B') ||
    setweight(to_tsvector('simple', coalesce(content,'')), 'C')
  ) STORED
);
CREATE INDEX idx_notes_user_updated ON notes(user_id, updated_at DESC);
CREATE INDEX idx_notes_fts ON notes USING GIN (fts);

-- 聊天消息（对话明细）
CREATE TABLE note_messages (
  id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  note_id      uuid NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
  role         message_role NOT NULL,
  content      text,                                   -- 文本；富文本放 metadata
  metadata     jsonb,                                  -- 模型、tokens、延迟等
  seq          int NOT NULL,                           -- note 内严格有序
  created_at   timestamptz NOT NULL DEFAULT now(),
  fts tsvector GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(content,''))) STORED
);
CREATE UNIQUE INDEX idx_msg_note_seq ON note_messages(note_id, seq);
CREATE INDEX idx_msg_note_created ON note_messages(note_id, created_at);
CREATE INDEX idx_msg_fts ON note_messages USING GIN (fts);


如需“子笔记/段落”，可另建 subnotes(note_id, title, content, seq, …)，此处从略。

3) 附件（对象存储元信息）
CREATE TABLE attachments (
  id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  note_id      uuid NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
  user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind         attachment_kind NOT NULL,
  object_key   text NOT NULL,                 -- S3/OSS/MinIO 路径
  mime         text,
  bytes        bigint,                        -- 文件大小
  sha256       text,                          -- 去重/秒传
  meta         jsonb,                         -- 宽高/时长/页数/波形等
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_attach_note ON attachments(note_id);
CREATE INDEX idx_attach_user ON attachments(user_id);
CREATE INDEX idx_attach_sha  ON attachments(sha256);

4) 
-- 会话（一次实时录音或一次离线文件转写）
CREATE TABLE transcription_sessions (
  id               uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id          uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  note_id          uuid REFERENCES notes(id) ON DELETE SET NULL,
  attachment_id    uuid REFERENCES attachments(id) ON DELETE SET NULL, -- 离线文件转写时挂附件
  source           text NOT NULL CHECK (source IN ('realtime','batch')),
  session_uid      text,                        -- 前端 connectionId / 服务端 session id
  model            text,
  engine           text,                        -- whisper/openai/azure…
  lang             text,
  sample_rate      int,
  duration_sec     int,
  full_text        text,                        -- 可选：结束时汇总到此
  confidence       numeric(5,2),                -- 总体置信度（可选）
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_ts_user_created    ON transcription_sessions(user_id, created_at DESC);
CREATE INDEX idx_ts_note_created    ON transcription_sessions(note_id, created_at DESC);
CREATE INDEX idx_ts_attach_created  ON transcription_sessions(attachment_id, created_at DESC);

-- 分段（逐句/逐片段文本）
CREATE TABLE transcription_segments (
  id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id    uuid NOT NULL REFERENCES transcription_sessions(id) ON DELETE CASCADE,
  seq           int  NOT NULL,                         -- 会话内顺序（1..n）
  item_id       text,                                  -- 兼容 payload item_id
  content_index int,
  ts_seconds    int,                                   -- 统一秒数便于范围查询
  timestamp     text,                                  -- 原始 "MM:SS"（可选）
  text          text NOT NULL,
  confidence    numeric(5,3),
  created_at    timestamptz NOT NULL DEFAULT now(),
  fts tsvector GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(text,''))) STORED
);
CREATE UNIQUE INDEX idx_tseg_session_seq ON transcription_segments(session_id, seq);
CREATE INDEX idx_tseg_session_ts ON transcription_segments(session_id, ts_seconds);
CREATE INDEX idx_tseg_fts ON transcription_segments USING GIN (fts);


说明：

实时场景：未产生文件也没关系，直接 note_id → transcription_sessions。

离线场景：把音视频存为 attachments，再在会话上挂 attachment_id。

会话结束时把所有分段 string_agg 成 full_text，便于整段显示/检索。

5) 标签系统（多对多）
CREATE TABLE tags (
  id        uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id   uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name      text NOT NULL,
  UNIQUE (user_id, name)
);

CREATE TABLE note_tags (
  note_id   uuid NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
  tag_id    uuid NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (note_id, tag_id)
);

6) 通用触发器：自动更新时间
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

-- 自动维护 updated_at
CREATE TRIGGER trg_touch_users
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE PROCEDURE touch_updated_at();

CREATE TRIGGER trg_touch_notes
BEFORE UPDATE ON notes
FOR EACH ROW EXECUTE PROCEDURE touch_updated_at();

CREATE TRIGGER trg_touch_tsessions
BEFORE UPDATE ON transcription_sessions
FOR EACH ROW EXECUTE PROCEDURE touch_updated_at();

7) 视图（聚合整段文本/最近会话）
-- 视图：会话的整段文本（若 full_text 为空则动态聚合）
CREATE OR REPLACE VIEW v_transcription_full_text AS
SELECT
  s.id              AS session_id,
  COALESCE(
    s.full_text,
    (SELECT string_agg(t.text, E'\n' ORDER BY t.seq)
     FROM transcription_segments t
     WHERE t.session_id = s.id)
  )                 AS full_text,
  s.lang, s.engine, s.model, s.user_id, s.note_id, s.attachment_id,
  s.created_at, s.updated_at
FROM transcription_sessions s;

-- 视图：某笔记最近一次会话
CREATE OR REPLACE VIEW v_note_latest_transcription AS
SELECT DISTINCT ON (s.note_id)
  s.note_id, s.id AS session_id, s.created_at, s.lang, s.engine, s.model,
  COALESCE(
    s.full_text,
    (SELECT string_agg(t.text, E'\n' ORDER BY t.seq)
     FROM transcription_segments t
     WHERE t.session_id = s.id)
  ) AS full_text
FROM transcription_sessions s
WHERE s.note_id IS NOT NULL
ORDER BY s.note_id, s.created_at DESC;
