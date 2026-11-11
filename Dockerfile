# 系统依赖：libreoffice（Office 互转/转 PDF）、pandoc（通用互转）、中文字体（否则中文变方框）
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp

# 锁定 libreoffice 版本由基础镜像源决定；如需严格锁定，在构建时固定 apt 版本号
RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice \
        pandoc \
        fonts-noto-cjk \
        fontconfig \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

EXPOSE 8100
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
