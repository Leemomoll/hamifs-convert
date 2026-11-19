# 系统依赖：libreoffice（Office 互转/转 PDF）、pandoc（通用互转）、中文字体（否则中文变方框）
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp

# Debian 官方源国内直连慢/不通，换 USTC 镜像源（deb822 格式的 sources.list.d/debian.sources）
RUN sed -i 's|deb.debian.org|mirrors.ustc.edu.cn|g' /etc/apt/sources.list.d/debian.sources || true
RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice \
        pandoc \
        fonts-noto-cjk \
        fontconfig \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# pip 走清华源，加速依赖安装
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY app ./app

EXPOSE 8100
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
