#!/usr/bin/env python3
"""
Автоматизация общения между аккаунтами в группах
Создает группы, добавляет участников, организует общение
"""

import asyncio
import json
import os
import sys
import importlib.util
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession

def load_all_sessions():
    """Загрузить все сессии из local-storage/sessions/"""
    sessions_dir = Path('local-storage/sessions')
    sessions = {}
    
    for json_file in sessions_dir.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                phone = data.get('phone_number')
                if phone:
                    sessions[phone] = data
        except:
            continue
    
    return sessions


async def create_group_and_add_all(group_title: str, admin_phone: str, all_phones: list):
    """Создать группу и добавить всех участников"""
    # Импорт функций из create-group-chat.py
    import sys
    import importlib.util
    
    create_chat_path = Path(__file__).parent / "create-group-chat.py"
    spec = importlib.util.spec_from_file_location("create_group_chat", str(create_chat_path))
    create_group_chat = importlib.util.module_from_spec(spec)
    sys.modules["create_group_chat"] = create_group_chat
    spec.loader.exec_module(create_group_chat)
    
    result = await create_group_chat.create_group_with_members(group_title, admin_phone, all_phones)
    return result


async def send_messages_round_robin(group_id: int, phones: list, messages: list, delay=5):
    """Отправить сообщения по кругу от разных аккаунтов"""
    from scripts.create_group_chat import send_message_to_group
    
    print(f"💬 Начало отправки сообщений в группу {group_id}")
    print(f"   Участников: {len(phones)}")
    print(f"   Сообщений: {len(messages)}")
    
    for i, message in enumerate(messages):
        phone = phones[i % len(phones)]  # По кругу
        print(f"\n[{i+1}/{len(messages)}] Отправка от {phone}...")
        
        success = await send_message_to_group(group_id, phone, message)
        
        if success:
            print(f"✅ Отправлено: {message[:50]}...")
        else:
            print(f"❌ Ошибка отправки")
        
        # Пауза между сообщениями
        if i < len(messages) - 1:
            await asyncio.sleep(delay)


async def simulate_group_chat(group_id: int, phones: list, rounds=5, delay=10):
    """Симуляция общения в группе"""
    messages = [
        "Привет всем!",
        "Как дела?",
        "Все отлично, спасибо!",
        "Отлично, продолжаем",
        "Согласен",
        "Давайте обсудим",
        "Хорошая идея",
        "Продолжаем работу"
    ]
    
    print(f"💬 Симуляция общения в группе {group_id}")
    print(f"   Участников: {len(phones)}")
    print(f"   Раундов: {rounds}")
    
    for round_num in range(rounds):
        print(f"\n--- Раунд {round_num + 1}/{rounds} ---")
        
        # Каждый участник отправляет сообщение
        for phone in phones:
            message = messages[round_num % len(messages)]
            print(f"📤 {phone}: {message}")
            
            import importlib.util
            import sys
            
            spec = importlib.util.spec_from_file_location("create_group_chat", "scripts/create-group-chat.py")
            create_group_chat = importlib.util.module_from_spec(spec)
            sys.modules["create_group_chat"] = create_group_chat
            spec.loader.exec_module(create_group_chat)
            
            await create_group_chat.send_message_to_group(group_id, phone, message)
            
            await asyncio.sleep(delay)
    
    print("\n✅ Симуляция завершена")


if __name__ == '__main__':
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  # Создать группу со всеми аккаунтами")
        print("  python group-chat-automation.py create <group_title> <admin_phone>")
        print("")
        print("  # Отправить сообщения по кругу")
        print("  python group-chat-automation.py send <group_id> <message1> <message2> ...")
        print("")
        print("  # Симуляция общения")
        print("  python group-chat-automation.py simulate <group_id> <rounds>")
        print("")
        print("Пример:")
        print("  python group-chat-automation.py create 'Warm-up Chat' +79001234567")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'create':
        if len(sys.argv) < 4:
            print("❌ Недостаточно аргументов")
            sys.exit(1)
        
        group_title = sys.argv[2]
        admin_phone = sys.argv[3]
        
        # Загрузить все сессии
        all_sessions = load_all_sessions()
        all_phones = list(all_sessions.keys())
        
        if admin_phone not in all_phones:
            print(f"❌ {admin_phone} не найден в сессиях")
            sys.exit(1)
        
        # Убрать админа из списка участников
        member_phones = [p for p in all_phones if p != admin_phone]
        
        print(f"📋 Найдено {len(all_phones)} аккаунтов")
        print(f"   Админ: {admin_phone}")
        print(f"   Участников: {len(member_phones)}")
        
        result = asyncio.run(create_group_and_add_all(group_title, admin_phone, member_phones))
        
        if result:
            # Сохранить информацию о группе
            groups_file = Path('local-storage/groups.json')
            groups_data = []
            if groups_file.exists():
                with open(groups_file, 'r') as f:
                    groups_data = json.load(f)
            
            groups_data.append(result)
            with open(groups_file, 'w') as f:
                json.dump(groups_data, f, indent=2)
            
            print(f"\n✅ Информация о группе сохранена в local-storage/groups.json")
    
    elif command == 'send':
        if len(sys.argv) < 4:
            print("❌ Недостаточно аргументов")
            sys.exit(1)
        
        group_id = int(sys.argv[2])
        messages = sys.argv[3:]
        
        all_sessions = load_all_sessions()
        phones = list(all_sessions.keys())
        
        asyncio.run(send_messages_round_robin(group_id, phones, messages))
    
    elif command == 'simulate':
        if len(sys.argv) < 3:
            print("❌ Недостаточно аргументов")
            sys.exit(1)
        
        group_id = int(sys.argv[2])
        rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        
        all_sessions = load_all_sessions()
        phones = list(all_sessions.keys())
        
        asyncio.run(simulate_group_chat(group_id, phones, rounds))
    
    else:
        print(f"❌ Неизвестная команда: {command}")

