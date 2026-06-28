FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 确保 .env 不被复制到镜像中（已经在 .dockerignore 忽略）
EXPOSE 7860

# Hugging Face Spaces 使用 PORT 环境变量（通常是 7860）
CMD gunicorn web_app:app --worker-class sync --timeout 120 --bind 0.0.0.0:$PORT
