# 🚀 Статус системы Telegram Farm

## ✅ Все компоненты запущены и работают!

### 📊 Статус контейнеров

| Сервис | Статус | Порт | Описание |
|--------|--------|------|----------|
| **Control API** | ✅ Running | 8000 | API для управления |
| **Postgres** | ✅ Healthy | 5432 | База данных |
| **Redis** | ✅ Healthy | 6379 | Очередь задач |
| **MinIO** | ✅ Healthy | 9000-9001 | S3-совместимое хранилище |

### 🐳 Docker образы

- ✅ `telegram-farm/android-worker:latest` (881 MB)
- ✅ `bip-control-api:latest` (273 MB)
- ✅ `postgres:15-alpine` (391 MB)
- ✅ `redis:7-alpine` (60.7 MB)
- ✅ `minio/minio:latest` (241 MB)

### 🌐 Доступные endpoints

#### Control API (http://localhost:8000)

- **GET /** - Главная страница
  ```bash
  curl http://localhost:8000/
  ```

- **GET /health** - Проверка здоровья
  ```bash
  curl http://localhost:8000/health
  ```

- **GET /ready** - Проверка готовности
  ```bash
  curl http://localhost:8000/ready
  ```

- **GET /api/v1/status** - Статус системы
  ```bash
  curl http://localhost:8000/api/v1/status
  ```

- **POST /api/v1/jobs/report** - Отчет от worker'а
  ```bash
  curl -X POST http://localhost:8000/api/v1/jobs/report \
    -H "Content-Type: application/json" \
    -d '{"account_id": "123", "status": "completed"}'
  ```

#### MinIO Console

- **URL**: http://localhost:9001
- **Логин**: `minioadmin`
- **Пароль**: `minioadmin`

### 💾 База данных

- **Host**: localhost:5432
- **Database**: telegram_farm
- **User**: telegram_farm
- **Password**: dev_password

Подключение:
```bash
docker exec -it bip-postgres-1 psql -U telegram_farm -d telegram_farm
```

### 📮 Redis

- **Host**: localhost:6379

Тестирование:
```bash
docker exec -it bip-redis-1 redis-cli
```

### 🔧 Полезные команды

#### Просмотр логов
```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f control-api
docker-compose logs -f postgres
docker-compose logs -f redis
```

#### Остановка/запуск
```bash
# Остановить все
docker-compose stop

# Запустить все
docker-compose start

# Перезапустить
docker-compose restart

# Остановить и удалить
docker-compose down
```

#### Проверка статуса
```bash
docker-compose ps
```

#### Тестирование API
```powershell
# PowerShell
Invoke-WebRequest -Uri http://localhost:8000/health
Invoke-WebRequest -Uri http://localhost:8000/api/v1/status
```

### 📝 Следующие шаги

1. **Настроить переменные окружения** для production
2. **Создать secrets** для реальных данных
3. **Развернуть в Kubernetes** (используя файлы из `k8s/` или `helm/`)
4. **Настроить мониторинг** (Prometheus + Grafana)
5. **Настроить бэкапы** для Postgres и MinIO

### 🎯 Готово к использованию!

Все базовые компоненты работают. Система готова для:
- Локальной разработки
- Тестирования
- Развертывания в Kubernetes





