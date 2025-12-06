#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки всех сессий и создания списка номеров
"""

import json
from pathlib import Path

SESSIONS_DIR = Path("local-storage/sessions")
PHONES_FILE = Path("local-storage/phones/accounts.txt")

def find_all_sessions():
    """Найти все сессии в подпапках"""
    sessions = []
    
    if not SESSIONS_DIR.exists():
        print("ERROR: Sessions directory not found")
        return sessions
    
    # Рекурсивный поиск всех .json файлов
    for json_file in SESSIONS_DIR.rglob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                phone = data.get('phone_number', '') or data.get('phone', '')
                if not phone:
                    # Попробовать из имени файла/папки
                    phone = json_file.stem
                
                sessions.append({
                    'phone': phone,
                    'path': str(json_file.relative_to(SESSIONS_DIR)),
                    'account_id': data.get('account_id', json_file.stem)
                })
        except:
            # Если не JSON, использовать имя файла
            phone = json_file.stem
            sessions.append({
                'phone': phone,
                'path': str(json_file.relative_to(SESSIONS_DIR)),
                'account_id': phone
            })
    
    return sessions

def main():
    print("Searching for all sessions...")
    sessions = find_all_sessions()
    
    if not sessions:
        print("ERROR: No sessions found")
        return
    
    print("\nFound {} sessions:\n".format(len(sessions)))
    
    phones = []
    for i, session in enumerate(sessions, 1):
        phone = session['phone']
        # Добавить + если нет
        if not phone.startswith('+'):
            phone = '+' + phone
        phones.append(phone)
        print("{}. {} - {}".format(i, phone, session['path']))
    
    # Сохранить номера в файл
    PHONES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PHONES_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(phones))
    
    print("\nPhones saved to {}".format(PHONES_FILE))
    print("Total: {} phones".format(len(phones)))

if __name__ == '__main__':
    main()
