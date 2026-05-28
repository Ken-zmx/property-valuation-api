# 使用官方Python 3.11镜像，完全兼容pydantic 2.9.0
FROM python:3.11.9-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制所有代码
COPY . .

# 暴露端口
EXPOSE 10000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
