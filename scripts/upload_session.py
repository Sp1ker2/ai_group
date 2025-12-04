#!/usr/bin/env python3
"""
Скрипт для загрузки Telegram session на сервер (MinIO/S3)
Использование: python upload_session.py --account-id 12345 --session session.json
"""
import json
import os
import sys
import argparse
from minio import Minio
from minio.error import S3Error

def upload_session(account_id, session_file, minio_endpoint=None, 
                  access_key=None, secret_key=None, bucket_name='telegram-sessions'):
    """Загрузить session файл на MinIO/S3"""
    
    # Параметры по умолчанию
    minio_endpoint = minio_endpoint or os.getenv('MINIO_ENDPOINT', 'localhost:9000')
    access_key = access_key or os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
    secret_key = secret_key or os.getenv('MINIO_SECRET_KEY', 'minioadmin')
    
    print(f"📤 Загрузка session для аккаунта {account_id}...")
    print(f"   Endpoint: {minio_endpoint}")
    print(f"   Bucket: {bucket_name}")
    
    try:
        # Подключение к MinIO
        client = Minio(
            minio_endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False
        )
        
        # Проверить/создать bucket
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"✅ Bucket '{bucket_name}' создан")
        else:
            print(f"✅ Bucket '{bucket_name}' существует")
        
        # Прочитать session файл
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        # Добавить account_id если его нет
        if 'account_id' not in session_data:
            session_data['account_id'] = account_id
        
        # Конвертировать обратно в JSON
        session_json = json.dumps(session_data, indent=2, ensure_ascii=False)
        session_bytes = session_json.encode('utf-8')
        
        # Имя файла в bucket
        object_name = f"{account_id}.json"
        
        # Загрузить на MinIO
        from io import BytesIO
        client.put_object(
            bucket_name,
            object_name,
            BytesIO(session_bytes),
            length=len(session_bytes),
            content_type='application/json'
        )
        
        print(f"✅ Session успешно загружен!")
        print(f"   Object: {bucket_name}/{object_name}")
        print(f"   Размер: {len(session_bytes)} bytes")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ Ошибка: Файл {session_file} не найден")
        return False
    except S3Error as e:
        print(f"❌ Ошибка MinIO: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Загрузить Telegram session на сервер')
    parser.add_argument('--account-id', type=str, required=True, help='ID аккаунта')
    parser.add_argument('--session', type=str, required=True, help='Путь к session файлу')
    parser.add_argument('--endpoint', type=str, help='MinIO endpoint (по умолчанию: localhost:9000)')
    parser.add_argument('--access-key', type=str, help='MinIO access key')
    parser.add_argument('--secret-key', type=str, help='MinIO secret key')
    parser.add_argument('--bucket', type=str, default='telegram-sessions', help='Имя bucket')
    
    args = parser.parse_args()
    
    # Проверить что файл существует
    if not os.path.exists(args.session):
        print(f"❌ Ошибка: Файл {args.session} не найден")
        sys.exit(1)
    
    # Загрузить session
    success = upload_session(
        args.account_id,
        args.session,
        args.endpoint,
        args.access_key,
        args.secret_key,
        args.bucket
    )
    
    if success:
        print("\n✅ Готово! Session загружен на сервер.")
        print(f"💡 Теперь можно создать задачу для аккаунта {args.account_id}")
        sys.exit(0)
    else:
        print("\n❌ Не удалось загрузить session.")
        sys.exit(1)


if __name__ == '__main__':
    main()

