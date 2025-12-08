# 🤖 Интеграция с OpenAI

## 🔑 API Key

OpenAI API key сохранен в `.env` файле (не коммитится в Git).

## 💡 Возможные применения

### 1. Генерация контента для сообщений

```python
import openai
import os
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

# Генерация сообщения
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "Ты помощник для генерации сообщений в Telegram"},
        {"role": "user", "content": "Сгенерируй естественное сообщение для warm-up"}
    ]
)

message = response.choices[0].message.content
```

### 2. Умные ответы в группах

```python
# Worker может использовать AI для генерации ответов
async def generate_smart_reply(self, context_messages):
    """Генерация умного ответа на основе контекста"""
    if not os.getenv('OPENAI_API_KEY'):
        return "Согласен!"
    
    # Использовать OpenAI для генерации ответа
    # ...
```

### 3. Анализ сообщений

```python
# Анализ тональности, тематики сообщений
async def analyze_messages(self, messages):
    """Анализ сообщений через OpenAI"""
    # ...
```

## 🔧 Настройка

### В Worker

```python
# В worker.py можно добавить:
import openai

openai.api_key = os.getenv('OPENAI_API_KEY')

async def generate_message(self):
    """Генерация сообщения через AI"""
    if not openai.api_key:
        return "Hello!"
    
    # Генерация через OpenAI
    # ...
```

### В Control API

```python
# В control-api можно добавить AI функции
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

@app.post("/api/v1/ai/generate-message")
async def generate_message(prompt: str):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"message": response.choices[0].message.content}
```

## ✅ Безопасность

- ✅ API key в `.env` (не коммитится)
- ✅ Используется только внутри системы
- ✅ Не передается в логи

## 📝 Примеры использования

### Генерация сообщений для групп

```python
# Автоматическая генерация разнообразных сообщений
messages = []
for i in range(10):
    message = generate_ai_message(context="warm-up chat")
    messages.append(message)
```

### Умные ответы

```python
# Worker читает сообщения в группе
# Генерирует ответ через AI
# Отправляет естественный ответ
```

## 🎯 Итог

OpenAI API key сохранен и готов к использованию для:
- Генерации контента
- Умных ответов
- Анализа сообщений
- Других AI функций





