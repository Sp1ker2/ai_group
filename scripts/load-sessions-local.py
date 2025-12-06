#!/usr/bin/env python3
"""
Загрузить session из локальной папки local-storage/sessions/
Использовать для локального тестирования без S3
"""

import json
import os
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio

def load_session_local(phone_number: str = None, account_id: str = None):
    """Загрузить session из локального файла по номеру или account_id"""
    sessions_dir = Path('local-storage/sessions')
    
    # Приоритет: по номеру телефона
    if phone_number:
        phone_filename = phone_number.replace('+', '').replace('-', '').replace(' ', '')
        
        # Сначала попробовать .json файл
        json_file = sessions_dir / f"{phone_filename}.json"
        if json_file.exists():
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Потом .session файл (если есть JSON рядом, загрузим его для метаданных)
        session_file = sessions_dir / f"{phone_filename}.session"
        if session_file.exists():
            # Если есть .session, но нет .json, создадим базовую структуру
            return {
                "phone_number": phone_number,
                "session_file": str(session_file),
                "has_session_file": True
            }
    
    # Fallback: по account_id
    if account_id:
        json_file = sessions_dir / f"session_{account_id}.json"
        if json_file.exists():
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    # Попробовать найти по всем JSON файлам
    for json_file in sessions_dir.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if account_id and str(data.get('account_id')) == str(account_id):
                    return data
                if phone_number and data.get('phone_number') == phone_number:
                    return data
        except:
            continue
    
    return None


async def test_session_local(phone_number: str = None, account_id: str = None):
    """Протестировать session локально"""
    session_data = load_session_local(phone_number=phone_number, account_id=account_id)
    
    if not session_data:
        identifier = phone_number or f"account_id {account_id}"
        print(f"❌ Session для {identifier} не найден")
        return False
    
    try:
        client = TelegramClient(
            StringSession(session_data['session_string']),
            int(session_data['api_id']),
            session_data['api_hash']
        )
        
        await client.start()
        me = await client.get_me()
        
        print(f"✅ Session работает!")
        print(f"   Account ID: {me.id}")
        print(f"   Username: @{me.username}" if me.username else "   Username: (нет)")
        print(f"   Имя: {me.first_name} {me.last_name or ''}")
        
        await client.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании session: {e}")
        return False


def list_all_sessions():
    """Показать все локальные сессии"""
    sessions_dir = Path('local-storage/sessions')
    
    if not sessions_dir.exists():
        print("❌ Папка local-storage/sessions не найдена")
        return []
    
    sessions = list(sessions_dir.glob('*.json'))
    
    if not sessions:
        print("📭 Нет сохраненных сессий")
        return []
    
    print(f"📁 Найдено {len(sessions)} сессий:\n")
    
    for session_file in sessions:
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            account_id = data.get('account_id', 'unknown')
            phone = data.get('phone_number', 'unknown')
            username = data.get('username', 'нет')
            
            print(f"  • {session_file.name}")
            print(f"    Account ID: {account_id}")
            print(f"    Phone: {phone}")
            print(f"    Username: @{username}" if username != 'нет' else "    Username: (нет)")
            print()
        except Exception as e:
            print(f"  ⚠️  {session_file.name} - ошибка чтения: {e}")
    
    return sessions


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'list':
            list_all_sessions()
        elif sys.argv[1] == 'test' and len(sys.argv) > 2:
            identifier = sys.argv[2]
            # Определить это номер или account_id
            if identifier.startswith('+') or identifier.replace('+', '').isdigit():
                asyncio.run(test_session_local(phone_number=identifier))
            else:
                asyncio.run(test_session_local(account_id=identifier))
        else:
            print("Использование:")
            print("  python load-sessions-local.py list                    # Показать все сессии")
            print("  python load-sessions-local.py test <phone>             # Протестировать по номеру")
            print("  python load-sessions-local.py test <account_id>        # Протестировать по ID")
    else:
        print("Использование:")
        print("  python load-sessions-local.py list                    # Показать все сессии")
        print("  python load-sessions-local.py test <phone>             # Протестировать по номеру")
        print("  python load-sessions-local.py test <account_id>        # Протестировать по ID")
        print("\nПример:")
        print("  python load-sessions-local.py list")
        print("  python load-sessions-local.py test +79001234567")
        print("  python load-sessions-local.py test 12345")

