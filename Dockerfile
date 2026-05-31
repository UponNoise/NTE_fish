# NTE 异环钓鱼自动化 - Docker 镜像
# 
# 注意：由于需要直接访问桌面 GUI、屏幕捕获和虚拟手柄驱动，
# Docker 容器化主要用于环境标准化和依赖管理。
# 实际运行建议直接在宿主机执行，参考 setup.bat。
#
# 构建: docker build -t nte-fish-bot .
# 运行: docker-compose up

FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="NTE Fish Bot"
LABEL org.opencontainers.image.description="异环钓鱼自动化脚本"
LABEL org.opencontainers.image.source="https://github.com/UponNoise/NTE_fish"

# 设置工作目录
WORKDIR /app

# 安装系统依赖（OpenCV 运行时库）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 注意：容器内无法直接使用 GUI 和虚拟手柄驱动
# 此镜像仅用于环境一致性验证和 CI/CD
CMD ["python", "-c", "print('NTE Fish Bot container ready. Run on host for actual use.')"]
