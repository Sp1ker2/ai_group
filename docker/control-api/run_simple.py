#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой запуск API без лишних зависимостей
"""
import sys
import os

# Добавить текущую директорию в путь
sys.path.insert(0, os.path.dirname(__file__))

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
except ImportError as e:
    print("ERROR: Не установлены зависимости!")
    print(f"Ошибка: {e}")
    print("\nУстановите:")
    print("  pip install fastapi uvicorn jinja2 python-multipart aiofiles")
    sys.exit(1)

# Простое приложение
app = FastAPI(title="Telegram Farm Control API")

@app.get("/")
async def root():
    return {
        "message": "Telegram Farm Control API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/test", response_class=HTMLResponse)
async def test():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram Farm - Test</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
            h1 { color: #6366f1; }
            .status { padding: 10px; background: #10b981; color: white; border-radius: 5px; margin: 10px 0; }
            a { color: #6366f1; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Telegram Farm Control API</h1>
            <div class="status">✅ API работает!</div>
            <p>Если вы видите эту страницу, значит API запущен успешно.</p>
            <h2>Следующие шаги:</h2>
            <ol>
                <li>Установите все зависимости: <code>pip install fastapi uvicorn jinja2 python-multipart aiofiles</code></li>
                <li>Запустите полную версию: <code>python main.py</code></li>
            </ol>
            <p><a href="/">Главная</a> | <a href="/health">Health Check</a></p>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    print(f"\n🚀 Запуск простого API на http://localhost:{port}")
    print(f"📱 Откройте: http://localhost:{port}/test\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")







