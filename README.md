## ChatGPT-WEB

![](https://miclon-job.oss-cn-hangzhou.aliyuncs.com/img/20230306213958.png)


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
python3 -m uvicorn api.app:app --reload --host 0.0.0.0 --port 800
```


