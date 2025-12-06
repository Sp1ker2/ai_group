# 🔧 Исправление проблем с запуском

## Проблема: "ERR_CONNECTION_REFUSED"

### Решение 1: Простой тест

```bash
cd docker\control-api
python run_simple.py
```

Откройте: http://localhost:8001/test

### Решение 2: Установка зависимостей

```bash
cd docker\control-api
pip install fastapi uvicorn jinja2 python-multipart aiofiles
python main.py
```

### Решение 3: Проверка Python

```bash
# Проверить версию
python --version

# Должно быть Python 3.8+
# Если нет - установите с python.org
```

### Решение 4: Если порт занят

Измените порт в `main.py`:
```python
port = int(os.getenv("PORT", "8002"))  # Другой порт
```

## Быстрый запуск

1. **Простой тест:**
   ```bash
   cd docker\control-api
   python run_simple.py
   ```
   Откройте: http://localhost:8001/test

2. **Полная версия:**
   ```bash
   cd docker\control-api
   pip install fastapi uvicorn jinja2 python-multipart aiofiles
   python main.py
   ```
   Откройте: http://localhost:8001

## Что проверить

1. ✅ Python установлен: `python --version`
2. ✅ Зависимости установлены: `pip list | findstr fastapi`
3. ✅ Порт свободен: `netstat -an | findstr :8001`
4. ✅ API запущен (в консоли должно быть "Uvicorn running")

## Если ничего не помогает

Запустите простую версию:
```bash
cd docker\control-api
python run_simple.py
```

Она работает без всех зависимостей и покажет работает ли вообще Python и FastAPI.



