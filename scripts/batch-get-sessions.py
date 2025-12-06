#!/usr/bin/env python3
"""
Массовое получение Telegram сессий для списка номеров
Использует ОДИНАКОВЫЕ api_id/api_hash для всех аккаунтов
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession

# Глобальные настройки (ОДИН раз для всех)
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')

if not API_ID or not API_HASH:
    print("❌ Ошибка: Установите TELEGRAM_API_ID и TELEGRAM_API_HASH")
    print("   Получите их на https://my.telegram.org/apps (ОДИН РАЗ!)")
    print("\n   export TELEGRAM_API_ID='ваш_api_id'")
    print("   export TELEGRAM_API_HASH='ваш_api_hash'")
    sys.exit(1)

async def get_session_for_phone(phone_number: str, api_id: str, api_hash: str):
    """Получить session для одного номера"""
    session = StringSession()
    client = TelegramClient(session, int(api_id), api_hash)
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"📱 [{phone_number}] Отправка кода...")
            await client.send_code_request(phone_number)
            
            code = input(f"   Введите код для {phone_number}: ")
            await client.sign_in(phone_number, code)
            
            # Если требуется пароль 2FA
            if not await client.is_user_authorized():
                password = input(f"   Введите пароль 2FA для {phone_number} (или Enter если нет): ")
                if password:
                    await client.sign_in(password=password)
        
        if await client.is_user_authorized():
            me = await client.get_me()
            session_string = client.session.save()
            
            session_data = {
                "account_id": str(me.id),
                "phone_number": phone_number,
                "username": me.username,
                "first_name": me.first_name,
                "last_name": me.last_name,
                "session_string": session_string,
                "api_id": api_id,  # ОДИН для всех
                "api_hash": api_hash  # ОДИН для всех
            }
            
            # Сохранить в local-storage/sessions/ по номеру телефона
            sessions_dir = Path('local-storage/sessions')
            sessions_dir.mkdir(parents=True, exist_ok=True)
            
            # Имя файла по номеру телефона (убираем + и заменяем на _)
            phone_filename = phone_number.replace('+', '').replace('-', '').replace(' ', '')
            
            # 1. Сохранить .session файл (стандартный формат Telethon)
            session_file = sessions_dir / f"{phone_filename}.session"
            client.session.save(str(session_file))
            
            # 2. Сохранить .json файл (с метаданными)
            json_file = sessions_dir / f"{phone_filename}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ [{phone_number}] Session сохранен:")
            print(f"   • {session_file} (.session)")
            print(f"   • {json_file} (.json)")
            print(f"   Account ID: {me.id}")
            return session_data
        else:
            print(f"❌ [{phone_number}] Не удалось авторизоваться")
            return None
            
    except Exception as e:
        print(f"❌ [{phone_number}] Ошибка: {e}")
        return None
    finally:
        await client.disconnect()


async def process_phones(phone_list: list):
    """Обработать список номеров"""
    print(f"🚀 Начало обработки {len(phone_list)} номеров")
    print(f"📋 Используются API credentials: api_id={API_ID}")
    print("=" * 60)
    
    success = 0
    failed = 0
    
    for i, phone in enumerate(phone_list, 1):
        phone = phone.strip()
        if not phone:
            continue
        
        print(f"\n[{i}/{len(phone_list)}] Обработка {phone}...")
        
        result = await get_session_for_phone(phone, API_ID, API_HASH)
        
        if result:
            success += 1
        else:
            failed += 1
        
        # Пауза между запросами (чтобы не спамить Telegram)
        if i < len(phone_list):
            await asyncio.sleep(2)
    
    print("\n" + "=" * 60)
    print(f"✅ Успешно: {success}")
    print(f"❌ Ошибок: {failed}")
    print(f"\n📁 Все session файлы сохранены в текущей директории")


def load_phones_from_file(filename: str) -> list:
    """Загрузить номера из файла"""
    phones = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                phones.append(line)
    return phones


def main():
    if len(sys.argv) < 2:
        print("Использование: python batch-get-sessions.py <файл_с_номерами.txt>")
        print("\nПример файла accounts.txt:")
        print("  +79001234567")
        print("  +79001234568")
        print("  +79001234569")
        print("\nИли создайте файл вручную и запустите:")
        print("  python batch-get-sessions.py accounts.txt")
        sys.exit(1)
    
    filename = sys.argv[1]
    
    if not os.path.exists(filename):
        print(f"❌ Файл {filename} не найден")
        sys.exit(1)
    
    # Загрузить номера
    phones = load_phones_from_file(filename)
    
    if not phones:
        print(f"❌ Файл {filename} пуст или не содержит номеров")
        sys.exit(1)
    
    print(f"📋 Загружено {len(phones)} номеров из {filename}")
    
    # Загрузить .env если есть
    try:
        from dotenv import load_dotenv
        load_dotenv()
        # Обновить глобальные переменные
        global API_ID, API_HASH
        API_ID = os.getenv('TELEGRAM_API_ID') or API_ID
        API_HASH = os.getenv('TELEGRAM_API_HASH') or API_HASH
    except:
        pass
    
    if not API_ID or not API_HASH:
        print("\n❌ Ошибка: TELEGRAM_API_ID и TELEGRAM_API_HASH не установлены")
        print("   Установите их:")
        print("   export TELEGRAM_API_ID='ваш_api_id'")
        print("   export TELEGRAM_API_HASH='ваш_api_hash'")
        print("\n   Или создайте .env файл:")
        print("   TELEGRAM_API_ID=ваш_api_id")
        print("   TELEGRAM_API_HASH=ваш_api_hash")
        sys.exit(1)
    
    # Обработать номера
    asyncio.run(process_phones(phones))


if __name__ == '__main__':
    main()


