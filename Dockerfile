# 1. 选择一个官方的Python 3.12 运行时作为基础镜像
FROM python:3.12-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 复制并安装依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 4. 复制项目文件
COPY . .

# 5. 定义容器启动时执行的命令 (假设您的主程序是 main.py)
CMD ["python", "main.py"]