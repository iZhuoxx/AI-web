## AI Toolbox-WEB


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

### 语音转写

- 新增 `POST /api/audio/transcriptions` 接口，支持 mp3、wav、webm 等常见音频，默认使用 `gpt-4o-transcribe` 模型，返回纯文本结果。
- 前端的附件按钮支持选择文本、PDF 和音频（mp3、wav 等），在点击发送时统一触发转写并附带文本。
- 新增麦克风按钮：点击开始录音，再次点击会调用后端转写接口，并将识别文字填充到输入框中，可继续编辑后再发送。
