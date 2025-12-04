#!/usr/bin/env python3
"""
Скрипт для получения session string от Telegram аккаунта
Запустите этот скрипт один раз для каждого аккаунта, чтобы получить session
"""

import asyncio
import json
import os
from telethon import TelegramClient
from telethon.sessions import StringSession

async def get_session():
    """Получение session string для аккаунта"""
    
    # Получить API credentials
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone_number = os.getenv('PHONE_NUMBER')
    
    if not api_id or not api_hash:
        print("❌ Ошибка: Установите TELEGRAM_API_ID и TELEGRAM_API_HASH")
        print("   Получите их на https://my.telegram.org/apps")
        return None
    
    if not phone_number:
        phone_number = input("Введите номер телефона (с кодом страны, например +79001234567): ")
    
    # Создать временную сессию
    session = StringSession()
    client = TelegramClient(session, int(api_id), api_hash)
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"📱 Отправка кода на {phone_number}...")
            await client.send_code_request(phone_number)
            
            code = input("Введите код из Telegram: ")
            await client.sign_in(phone_number, code)
            
            # Если требуется пароль 2FA
            if await client.is_user_authorized() == False:
                password = input("Введите пароль 2FA (если установлен): ")
                await client.sign_in(password=password)
        
        # Получить информацию об аккаунте
        me = await client.get_me()
        session_string = client.session.save()
        
        # Сохранить session в JSON
        session_data = {
            "account_id": str(me.id),
            "phone_number": phone_number,
            "username": me.username,
            "first_name": me.first_name,
            "last_name": me.last_name,
            "session_string": session_string,
            "api_id": api_id,
            "api_hash": api_hash
        }
        
        # Сохранить в файл
        filename = f"session_{me.id}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Session успешно получен!")
        print(f"   Account ID: {me.id}")
        print(f"   Username: @{me.username}" if me.username else "   Username: (нет)")
        print(f"   Имя: {me.first_name} {me.last_name or ''}")
        print(f"\n📁 Session сохранен в: {filename}")
        print(f"\n📋 Session string (для копирования):")
        print(f"   {session_string[:50]}...")
        
        return session_data
        
    except Exception as e:
        print(f"❌ Ошибка при получении session: {e}")
        return None
    finally:
        await client.disconnect()


if __name__ == '__main__':
    print("🔐 Получение Telegram session")
    print("=" * 50)
    
    # Загрузить переменные из .env если есть
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
    
    asyncio.run(get_session())

