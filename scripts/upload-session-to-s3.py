#!/usr/bin/env python3
"""
Скрипт для загрузки session JSON в MinIO/S3
"""

import json
import os
import sys
from minio import Minio
from minio.error import S3Error

def upload_session_to_s3(session_file: str):
    """Загрузить session файл в S3/MinIO"""
    
    # Настройки S3/MinIO
    s3_endpoint = os.getenv('S3_ENDPOINT', 'localhost:9000')
    s3_access_key = os.getenv('S3_ACCESS_KEY', 'minioadmin')
    s3_secret_key = os.getenv('S3_SECRET_KEY', 'minioadmin')
    s3_bucket = os.getenv('S3_BUCKET', 'telegram-sessions')
    secure = s3_endpoint.startswith('https://')
    
    # Убрать протокол из endpoint
    endpoint = s3_endpoint.replace('http://', '').replace('https://', '')
    
    try:
        # Подключение к MinIO
        client = Minio(
            endpoint,
            access_key=s3_access_key,
            secret_key=s3_secret_key,
            secure=secure
        )
        
        # Проверить существование bucket, создать если нет
        if not client.bucket_exists(s3_bucket):
            print(f"📦 Создание bucket: {s3_bucket}")
            client.make_bucket(s3_bucket)
        
        # Загрузить session файл
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        account_id = session_data.get('account_id')
        if not account_id:
            print("❌ Ошибка: account_id не найден в session файле")
            return False
        
        # Имя объекта в S3
        object_name = f"{account_id}.json"
        
        # Загрузить файл
        client.fput_object(
            s3_bucket,
            object_name,
            session_file,
            content_type='application/json'
        )
        
        print(f"✅ Session успешно загружен в S3!")
        print(f"   Bucket: {s3_bucket}")
        print(f"   Object: {object_name}")
        print(f"   Account ID: {account_id}")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ Ошибка: Файл {session_file} не найден")
        return False
    except S3Error as e:
        print(f"❌ Ошибка S3: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python upload-session-to-s3.py <session_file.json>")
        print("\nПример:")
        print("  python upload-session-to-s3.py session_12345.json")
        sys.exit(1)
    
    session_file = sys.argv[1]
    
    # Загрузить переменные из .env если есть
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
    
    upload_session_to_s3(session_file)









