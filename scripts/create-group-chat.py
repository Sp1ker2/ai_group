#!/usr/bin/env python3
"""
Скрипт для создания группы и добавления участников
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession

def load_session(phone_number: str):
    """Загрузить session по номеру"""
    sessions_dir = Path('local-storage/sessions')
    phone_filename = phone_number.replace('+', '').replace('-', '').replace(' ', '')
    
    # Попробовать JSON
    json_file = sessions_dir / f"{phone_filename}.json"
    if json_file.exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Попробовать .session
    session_file = sessions_dir / f"{phone_filename}.session"
    if session_file.exists():
        return {
            'phone_number': phone_number,
            'session_file': str(session_file),
            'has_session_file': True
        }
    
    return None


async def create_group_with_members(group_title: str, admin_phone: str, member_phones: list):
    """Создать группу и добавить участников"""
    
    # Загрузить session админа
    admin_session = load_session(admin_phone)
    if not admin_session:
        print(f"❌ Session для {admin_phone} не найден")
        return None
    
    api_id = os.getenv('TELEGRAM_API_ID', admin_session.get('api_id', ''))
    api_hash = os.getenv('TELEGRAM_API_HASH', admin_session.get('api_hash', ''))
    
    if not api_id or not api_hash:
        print("❌ API credentials не найдены")
        return None
    
    # Создать клиент для админа
    if admin_session.get('has_session_file'):
        client = TelegramClient(admin_session['session_file'], int(api_id), api_hash)
    else:
        session_string = admin_session.get('session_string')
        if not session_string:
            print("❌ Session string не найден")
            return None
        client = TelegramClient(StringSession(session_string), int(api_id), api_hash)
    
    try:
        await client.start()
        me = await client.get_me()
        print(f"✅ Авторизован как: {me.first_name} ({me.phone})")
        
        # Создать группу
        print(f" group '{group_title}'...")
        created = await client.create_group(title=group_title, users=[])
        group_id = created.id
        
        print(f"✅ Группа создана: {group_id}")
        
        # Добавить участников
        if member_phones:
            print(f"👥 Добавление {len(member_phones)} участников...")
            added = []
            
            for phone in member_phones:
                try:
                    # Загрузить session участника
                    member_session = load_session(phone)
                    if not member_session:
                        print(f"⚠️  Session для {phone} не найден, пропуск")
                        continue
                    
                    # Получить entity пользователя
                    user = await client.get_entity(phone)
                    await client.add_participants(created, [user])
                    added.append(phone)
                    print(f"  ✅ Добавлен: {phone}")
                    await asyncio.sleep(2)  # Пауза между добавлениями
                except Exception as e:
                    print(f"  ❌ Ошибка при добавлении {phone}: {e}")
            
            print(f"✅ Добавлено участников: {len(added)}/{len(member_phones)}")
        
        # Получить информацию о группе
        group = await client.get_entity(group_id)
        
        result = {
            'group_id': group_id,
            'group_title': group_title,
            'admin_phone': admin_phone,
            'members_added': len(added) if member_phones else 0,
            'total_members': len(member_phones)
        }
        
        print(f"\n✅ Группа готова!")
        print(f"   ID: {group_id}")
        print(f"   Название: {group_title}")
        print(f"   Участников: {result['members_added']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None
    finally:
        await client.disconnect()


async def send_message_to_group(group_id: int, phone_number: str, message: str):
    """Отправить сообщение в группу от имени аккаунта"""
    session_data = load_session(phone_number)
    if not session_data:
        print(f"❌ Session для {phone_number} не найден")
        return False
    
    api_id = os.getenv('TELEGRAM_API_ID', session_data.get('api_id', ''))
    api_hash = os.getenv('TELEGRAM_API_HASH', session_data.get('api_hash', ''))
    
    if session_data.get('has_session_file'):
        client = TelegramClient(session_data['session_file'], int(api_id), api_hash)
    else:
        session_string = session_data.get('session_string')
        client = TelegramClient(StringSession(session_string), int(api_id), api_hash)
    
    try:
        await client.start()
        await client.send_message(group_id, message)
        print(f"✅ Сообщение отправлено от {phone_number}")
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return False
    finally:
        await client.disconnect()


if __name__ == '__main__':
    # Загрузить .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  # Создать группу")
        print("  python create-group-chat.py create <group_title> <admin_phone> <member1> <member2> ...")
        print("")
        print("  # Отправить сообщение")
        print("  python create-group-chat.py send <group_id> <phone> <message>")
        print("")
        print("Пример:")
        print("  python create-group-chat.py create 'Test Group' +79001234567 +79001234568 +79001234569")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'create':
        if len(sys.argv) < 4:
            print("❌ Недостаточно аргументов")
            sys.exit(1)
        
        group_title = sys.argv[2]
        admin_phone = sys.argv[3]
        member_phones = sys.argv[4:] if len(sys.argv) > 4 else []
        
        asyncio.run(create_group_with_members(group_title, admin_phone, member_phones))
    
    elif command == 'send':
        if len(sys.argv) < 5:
            print("❌ Недостаточно аргументов")
            sys.exit(1)
        
        group_id = int(sys.argv[2])
        phone = sys.argv[3]
        message = sys.argv[4]
        
        asyncio.run(send_message_to_group(group_id, phone, message))
    
    else:
        print(f"❌ Неизвестная команда: {command}")





