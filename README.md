# hamifs-convert

个人智能文档系统（hamifs）的**文档格式转换服务**，独立部署、可单独开源。
技术方案见 `D:\hamifs\开发文档\格式转换服务技术方案.docx`。

## 架构

- **FastAPI**：REST 接口（对齐前端 `hamifs-front/src/api/convert.js` 的 mock）
- **引擎**：LibreOffice（Office 互转/转 PDF）、Pandoc（通用互转）、pdf2docx（PDF→Word）、pypdfium2（PDF→图片）、openpyxl（xlsx→csv）、mammoth（docx→html/md）
- **异步**：默认进程内后台线程（开发期零依赖）；配置 `CELERY_BROKER_URL` 后切换 Celery + Redis
- **存储**：默认本地目录；`STORAGE_BACKEND=s3` 时走 MinIO/云 OSS，下载走预签名 URL

## 支持的转换方向

| 源 | 目标 | 引擎 |
|---|---|---|
| docx/doc/xlsx/pptx | pdf | LibreOffice |
| docx | html / md | mammoth |
| docx / pdf / md | txt | pandoc |
| pdf | docx | pdf2docx（仅文本层，扫描件需 OCR） |
| pdf | png | pypdfium2（多页输出 zip） |
| xlsx | csv | openpyxl（第一个工作表） |
| md / html / txt | docx / html / pdf | pandoc |

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST | `/convert/tasks` | multipart 提交：`file` + `targetFormat`，返回 `{taskId}` |
| GET | `/convert/tasks` | 任务列表 |
| GET | `/convert/tasks/{id}` | 状态与进度（前端轮询） |
| GET | `/convert/download/{id}` | 下载结果（s3 时 302 预签名 URL） |

任务状态机：`PENDING → RUNNING(进度%) → SUCCESS / FAILED`，失败自动重试 1 次。

## 本地开发（Windows）

```powershell
cd D:\hamifs\hamifs-convert
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8100
```

注意：
- `pdf2docx`、`pypdfium2`、`mammoth`、`openpyxl` 均可 pip 直接装，Windows 可用；
- LibreOffice（`soffice`）和 `pandoc` 需本机安装并加入 PATH，仅用到对应引擎时才需要；
- 默认存储为本地 `./data` 目录，无需 MinIO 即可跑通全流程。

## Docker 部署

```bash
docker compose up -d --build          # convert + redis + minio
docker compose --profile worker up -d # 需要独立 Celery worker 时
```

镜像内置 libreoffice、pandoc、fonts-noto-cjk（中文字体，缺了会变方框）。

## Java 侧对接（P4）

`hamifs-back` 调 `POST http://hamifs-convert:8100/convert/tasks` 提交任务，
任务元数据落 MySQL `convert_task` 表，前端轮询 Java 网关接口即可。
