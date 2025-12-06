# 🔐 Telegram API Credentials

## Ваши API Credentials

**⚠️ ВАЖНО: Эти данные конфиденциальны! Не коммитьте их в Git!**

### App Information
- **App Title**: Bitapp
- **Short Name**: bitappbot
- **API ID**: `30348172`
- **API Hash**: `84b70fca6408500690aa026beb1982b3`

### MTProto Servers

#### Test Configuration
- **Server**: `149.154.167.40:443`
- **DC**: 2

#### Production Configuration
- **Server**: `149.154.167.50:443`
- **DC**: 2

## Использование

### 1. Сохранить в .env файл

```bash
# Создать .env файл (уже создан автоматически)
TELEGRAM_API_ID=30348172
TELEGRAM_API_HASH=84b70fca6408500690aa026beb1982b3
```

### 2. Использовать в скриптах

```bash
# Экспортировать переменные
export TELEGRAM_API_ID="30348172"
export TELEGRAM_API_HASH="84b70fca6408500690aa026beb1982b3"

# Или использовать .env файл
source .env  # Linux/Mac
# или
Get-Content .env | ForEach-Object { if ($_ -match '^([^=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process') } }  # PowerShell
```

### 3. В Python скриптах

```python
import os
from dotenv import load_dotenv

# Загрузить из .env
load_dotenv()

api_id = os.getenv('TELEGRAM_API_ID')
api_hash = os.getenv('TELEGRAM_API_HASH')
```

## Безопасность

✅ **Правильно:**
- Хранить в `.env` файле (уже в `.gitignore`)
- Использовать переменные окружения
- Не коммитить в Git

❌ **Неправильно:**
- Коммитить в Git
- Публиковать в открытом доступе
- Хранить в коде

## Проверка

Проверить что credentials работают:

```python
from telethon import TelegramClient
import os
from dotenv import load_dotenv

load_dotenv()

api_id = os.getenv('TELEGRAM_API_ID')
api_hash = os.getenv('TELEGRAM_API_HASH')

client = TelegramClient('test_session', int(api_id), api_hash)

async def test():
    await client.connect()
    print("✅ API credentials работают!")
    await client.disconnect()

asyncio.run(test())
```

## Дополнительная информация

- **Получено на**: https://my.telegram.org/apps
- **Приложение**: Bitapp (bitappbot)
- **Использование**: ОДИН раз для всех аккаунтов

Эти credentials используются для **всех** ваших Telegram аккаунтов при получении сессий.





