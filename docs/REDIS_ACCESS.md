# 🔴 Как подключиться к Redis

## ⚠️ Важно!

Redis **НЕ работает через HTTP**. Redis использует собственный протокол **RESP (Redis Serialization Protocol)** по TCP.

Порт 6379 - это TCP порт, а не HTTP endpoint!

## ✅ Правильные способы подключения

### 1. Через redis-cli (внутри контейнера)

```bash
# Войти в контейнер Redis
docker exec -it bip-redis-1 redis-cli

# Или выполнить команду напрямую
docker exec bip-redis-1 redis-cli ping
docker exec bip-redis-1 redis-cli set mykey "myvalue"
docker exec bip-redis-1 redis-cli get mykey
```

### 2. Через Python

```python
import redis

# Подключение
r = redis.Redis(host='localhost', port=6379, db=0)

# Проверка
print(r.ping())  # Должно вернуть True

# Работа с данными
r.set('mykey', 'myvalue')
value = r.get('mykey')
print(value)  # b'myvalue'
```

### 3. Через Node.js

```javascript
const redis = require('redis');
const client = redis.createClient({
    host: 'localhost',
    port: 6379
});

client.on('connect', () => {
    console.log('Connected to Redis');
});

client.set('mykey', 'myvalue');
client.get('mykey', (err, reply) => {
    console.log(reply);
});
```

### 4. Через telnet/nc (для тестирования)

```bash
# Windows PowerShell
Test-NetConnection -ComputerName localhost -Port 6379

# Linux/Mac
nc -zv localhost 6379
telnet localhost 6379
```

## 🔍 Проверка работы Redis

### Проверка доступности порта

```powershell
# PowerShell
Test-NetConnection -ComputerName localhost -Port 6379
```

### Проверка через Docker

```bash
# Проверка что Redis отвечает
docker exec bip-redis-1 redis-cli ping
# Должно вернуть: PONG

# Проверка информации о сервере
docker exec bip-redis-1 redis-cli info server

# Проверка всех ключей
docker exec bip-redis-1 redis-cli keys "*"
```

## 📊 Redis Web UI (опционально)

Если нужен веб-интерфейс для Redis, можно использовать:

### Redis Commander

```bash
docker run -d \
  --name redis-commander \
  -p 8081:8081 \
  --network bip_default \
  rediscommander/redis-commander:latest \
  --redis-host bip-redis-1 \
  --redis-port 6379
```

Затем откройте: http://localhost:8081

### RedisInsight

Скачайте с официального сайта: https://redis.com/redis-enterprise/redis-insight/

## 🧪 Тестирование подключения

### Простой тест на Python

Создайте файл `test_redis.py`:

```python
import redis

try:
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    # Проверка подключения
    result = r.ping()
    print(f"✅ Redis подключен: {result}")
    
    # Тест записи/чтения
    r.set('test', 'Hello Redis!')
    value = r.get('test')
    print(f"✅ Значение получено: {value}")
    
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")
```

Запустите:
```bash
python test_redis.py
```

## 📝 Полезные команды Redis

```bash
# Войти в redis-cli
docker exec -it bip-redis-1 redis-cli

# Внутри redis-cli:
PING              # Проверка подключения
SET key value     # Установить значение
GET key           # Получить значение
KEYS *            # Показать все ключи
DEL key           # Удалить ключ
FLUSHALL          # Очистить все данные
INFO              # Информация о сервере
```

## 🔗 Подключение из приложения

### В docker-compose.yml

Если ваш сервис в той же сети:

```yaml
services:
  myapp:
    environment:
      REDIS_URL: redis://bip-redis-1:6379
```

### Извне Docker

```python
# Python
redis.Redis(host='localhost', port=6379)

# Node.js
redis.createClient({ host: 'localhost', port: 6379 })
```

## ✅ Итог

- Redis работает на **TCP порту 6379**, не HTTP
- Используйте **redis-cli** или клиентские библиотеки
- Для веб-интерфейса используйте Redis Commander или RedisInsight
- Подключение из приложений: `localhost:6379` (TCP)

