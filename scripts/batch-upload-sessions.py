#!/usr/bin/env python3
"""
Массовая загрузка session файлов в S3
"""

import os
import json
import sys
from glob import glob
from minio import Minio
from minio.error import S3Error

def upload_session(session_file: str, client: Minio, bucket: str):
    """Загрузить один session файл"""
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        account_id = session_data.get('account_id')
        if not account_id:
            print(f"⚠️  Пропуск {session_file}: нет account_id")
            return False
        
        object_name = f"{account_id}.json"
        
        client.fput_object(
            bucket,
            object_name,
            session_file,
            content_type='application/json'
        )
        
        print(f"✅ {session_file} → {object_name}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при загрузке {session_file}: {e}")
        return False


def main():
    # Настройки
    s3_endpoint = os.getenv('S3_ENDPOINT', 'localhost:9000')
    s3_access_key = os.getenv('S3_ACCESS_KEY', 'minioadmin')
    s3_secret_key = os.getenv('S3_SECRET_KEY', 'minioadmin')
    s3_bucket = os.getenv('S3_BUCKET', 'telegram-sessions')
    
    endpoint = s3_endpoint.replace('http://', '').replace('https://', '')
    secure = s3_endpoint.startswith('https://')
    
    # Подключение
    try:
        client = Minio(endpoint, s3_access_key, s3_secret_key, secure=secure)
        
        # Создать bucket если нет
        if not client.bucket_exists(s3_bucket):
            print(f"📦 Создание bucket: {s3_bucket}")
            client.make_bucket(s3_bucket)
        
        # Найти все session файлы (локально и в local-storage)
        # Поддержка обоих форматов: по номеру и по account_id
        session_files = (
            glob("session_*.json") + 
            glob("local-storage/sessions/session_*.json") +
            glob("local-storage/sessions/*.json")  # Все JSON файлы (включая по номерам)
        )
        # Убрать дубликаты
        session_files = list(set(session_files))
        
        if not session_files:
            print("❌ Не найдено session файлов (session_*.json)")
            return
        
        print(f"📤 Найдено {len(session_files)} session файлов")
        print("=" * 50)
        
        success = 0
        failed = 0
        
        for session_file in session_files:
            if upload_session(session_file, client, s3_bucket):
                success += 1
            else:
                failed += 1
        
        print("=" * 50)
        print(f"✅ Успешно: {success}")
        print(f"❌ Ошибок: {failed}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == '__main__':
    # Загрузить .env если есть
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
    
    main()


