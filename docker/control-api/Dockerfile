FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    jinja2 \
    python-multipart \
    aiofiles \
    aiohttp \
    asyncpg \
    redis \
    pydantic \
    python-dotenv \
    telethon \
    pysocks

# Копирование кода
COPY . /app

# Порт
EXPOSE 8000

# Команда запуска
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]



