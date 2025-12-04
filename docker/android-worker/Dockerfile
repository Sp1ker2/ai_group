# Android Worker Dockerfile
# Базируется на Ubuntu с поддержкой Android эмуляции (Waydroid/Anbox)

FROM ubuntu:22.04

# Отключение интерактивных запросов
ENV DEBIAN_FRONTEND=noninteractive

# Установка базовых зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    python3 \
    python3-pip \
    python3-venv \
    adb \
    android-tools-adb \
    android-tools-fastboot \
    unzip \
    zip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Установка Waydroid (альтернатива: Anbox)
# Waydroid требует privileged контейнер и доступ к /dev
RUN apt-get update && apt-get install -y \
    waydroid \
    || echo "Waydroid installation may require additional setup"

# Установка Python зависимостей для Telegram клиента
RUN pip3 install --no-cache-dir \
    telethon \
    pyrogram \
    python-dotenv \
    requests \
    aiohttp \
    asyncpg \
    redis \
    pydantic

# Создание рабочей директории
WORKDIR /app

# Копирование скриптов worker'а
COPY worker.py /app/
COPY requirements.txt /app/

# Создание директорий для данных
RUN mkdir -p /data/sessions /data/logs /data/tmp

# Установка прав
RUN chmod +x /app/scripts/*.sh || true
RUN chmod +x /app/worker.py || true

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV SESSION_STORAGE_PATH=/data/sessions
ENV LOG_PATH=/data/logs

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8080/health', timeout=5)" || exit 1

# Точка входа
ENTRYPOINT ["python3", "/app/worker.py"]

