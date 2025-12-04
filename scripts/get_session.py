#!/usr/bin/env python3
"""
Скрипт для получения Telegram session
Использование: python get_session.py --phone +79001234567
"""
import asyncio
import json
import os
import sys
import argparse
from telethon import TelegramClient
from telethon.sessions import StringSession

async def get_session(phone, api_id, api_hash, output_file=None):
    """Получить session для Telegram аккаунта"""
    
    print(f"🔐 Получение session для {phone}...")
    
    # Создать клиента
    client = TelegramClient(StringSession(), api_id, api_hash)
    
    try:
        # Запустить клиента
        await client.start(phone=phone)
        
        # Получить информацию о себе
        me = await client.get_me()
        print(f"✅ Авторизован как: {me.first_name} (@{me.username})")
        
        # Получить session string
        session_string = client.session.save()
        
        # Подготовить данные
        session_data = {
            "phone_number": phone,
            "session_string": session_string,
            "api_id": api_id,
            "api_hash": api_hash,
            "user_id": me.id,
            "username": me.username,
            "first_name": me.first_name,
            "last_name": me.last_name
        }
        
        # Определить имя файла
        if not output_file:
            safe_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
            output_file = f"session_{safe_phone}.json"
        
        # Сохранить в файл
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Session сохранен в: {output_file}")
        print(f"📋 Session string (первые 50 символов): {session_string[:50]}...")
        print(f"\n💡 Теперь можно загрузить этот файл на сервер:")
        print(f"   python scripts/upload_session.py --account-id {me.id} --session {output_file}")
        
        return session_data
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None
    finally:
        await client.disconnect()


def main():
    parser = argparse.ArgumentParser(description='Получить Telegram session')
    parser.add_argument('--phone', type=str, help='Номер телефона (например: +79001234567)')
    parser.add_argument('--api-id', type=str, help='Telegram API ID', 
                       default=os.getenv('TELEGRAM_API_ID'))
    parser.add_argument('--api-hash', type=str, help='Telegram API Hash',
                       default=os.getenv('TELEGRAM_API_HASH'))
    parser.add_argument('--output', type=str, help='Имя выходного файла')
    
    args = parser.parse_args()
    
    # Запросить данные если не указаны
    phone = args.phone or input("Номер телефона (например +79001234567): ").strip()
    api_id = args.api_id or input("API ID (получить на https://my.telegram.org): ").strip()
    api_hash = args.api_hash or input("API Hash: ").strip()
    
    if not all([phone, api_id, api_hash]):
        print("❌ Ошибка: Необходимо указать phone, api_id и api_hash")
        sys.exit(1)
    
    # Получить session
    result = asyncio.run(get_session(phone, api_id, api_hash, args.output))
    
    if result:
        print("\n✅ Готово! Session получен успешно.")
        sys.exit(0)
    else:
        print("\n❌ Не удалось получить session.")
        sys.exit(1)


if __name__ == '__main__':
    main()

