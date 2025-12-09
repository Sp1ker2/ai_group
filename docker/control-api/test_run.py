#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый запуск для проверки ошибок
"""
import sys
import os

print("Проверка импортов...")
try:
    from fastapi import FastAPI
    print("✅ fastapi")
except Exception as e:
    print(f"❌ fastapi: {e}")
    sys.exit(1)

try:
    from telethon import TelegramClient
    print("✅ telethon")
except Exception as e:
    print(f"❌ telethon: {e}")

try:
    import jinja2
    print("✅ jinja2")
except Exception as e:
    print(f"❌ jinja2: {e}")

print("\nПроверка main.py...")
try:
    import main
    print("✅ main.py импортируется")
except Exception as e:
    print(f"❌ Ошибка импорта main.py: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nПроверка путей...")
from pathlib import Path
BASE_DIR = Path(__file__).parent
print(f"BASE_DIR: {BASE_DIR}")
print(f"templates: {(BASE_DIR / 'templates').exists()}")
print(f"static: {(BASE_DIR / 'static').exists()}")

print("\n✅ Все проверки пройдены!")
print("Запуск API...")
print("=" * 50)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    print(f"\n🚀 Запуск на http://localhost:{port}\n")
    uvicorn.run(main.app, host="0.0.0.0", port=port, log_level="info")







