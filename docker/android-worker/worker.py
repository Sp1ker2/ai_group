#!/usr/bin/env python3
"""
Android Worker для выполнения Telegram warm-up задач
"""

import os
import sys
import asyncio
import logging
import json
from typing import Optional
from pathlib import Path

# Telegram клиенты
try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
except ImportError:
    print("ERROR: telethon not installed", file=sys.stderr)
    sys.exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/data/logs/worker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class AndroidWorker:
    """Worker для выполнения warm-up задач"""
    
    def __init__(self):
        self.phone_number = os.getenv('PHONE_NUMBER')
        self.account_id = os.getenv('ACCOUNT_ID')
        self.script_id = os.getenv('SCRIPT_ID', 'warmup_script_v1')
        self.control_api_url = os.getenv('CONTROL_API_URL', 'http://control-node:8000')
        self.control_api_token = os.getenv('CONTROL_API_TOKEN')
        self.session_path = Path(os.getenv('SESSION_STORAGE_PATH', '/data/sessions'))
        self.client: Optional[TelegramClient] = None
        
        if not self.phone_number:
            raise ValueError("PHONE_NUMBER environment variable is required")
        if not self.account_id:
            raise ValueError("ACCOUNT_ID environment variable is required")
    
    async def load_session_from_s3(self):
        """Загрузка session из S3/MinIO"""
        try:
            from minio import Minio
            import json
            
            s3_endpoint = os.getenv('S3_ENDPOINT', 'http://minio:9000')
            s3_access_key = os.getenv('S3_ACCESS_KEY', 'minioadmin')
            s3_secret_key = os.getenv('S3_SECRET_KEY', 'minioadmin')
            s3_bucket = os.getenv('S3_BUCKET', 'telegram-sessions')
            
            # Подключение к MinIO
            client = Minio(
                s3_endpoint.replace('http://', '').replace('https://', ''),
                access_key=s3_access_key,
                secret_key=s3_secret_key,
                secure=False
            )
            
            # Загрузить session файл
            object_name = f"{self.account_id}.json"
            response = client.get_object(s3_bucket, object_name)
            session_data = json.loads(response.read().decode('utf-8'))
            response.close()
            response.release_conn()
            
            logger.info(f"Session loaded from S3 for account {self.account_id}")
            return session_data
            
        except Exception as e:
            logger.warning(f"Failed to load session from S3: {e}, trying local file")
            return None
    
    async def initialize_client(self):
        """Инициализация Telegram клиента"""
        logger.info(f"Initializing client for account {self.account_id}")
        
        # Попытаться загрузить session из S3
        session_data = await self.load_session_from_s3()
        
        if session_data:
            # Использовать StringSession из S3
            from telethon.sessions import StringSession
            session_string = session_data.get('session_string')
            api_id = session_data.get('api_id') or os.getenv('TELEGRAM_API_ID', '')
            api_hash = session_data.get('api_hash') or os.getenv('TELEGRAM_API_HASH', '')
            
            if session_string:
                self.client = TelegramClient(
                    StringSession(session_string),
                    api_id=int(api_id),
                    api_hash=api_hash
                )
                await self.client.start()
                logger.info("Client initialized from S3 session")
                return
        
        # Fallback: использовать локальный файл
        session_file = self.session_path / f"{self.account_id}.session"
        api_id = os.getenv('TELEGRAM_API_ID', '')
        api_hash = os.getenv('TELEGRAM_API_HASH', '')
        
        self.client = TelegramClient(
            str(session_file),
            api_id=int(api_id) if api_id else None,
            api_hash=api_hash
        )
        
        await self.client.start(phone=self.phone_number)
        logger.info("Client initialized from local session file")
    
    async def execute_warmup_script(self):
        """Выполнение warm-up скрипта"""
        logger.info(f"Executing warmup script: {self.script_id}")
        
        if not self.client:
            await self.initialize_client()
        
        # Пример warm-up действий
        warmup_actions = [
            self._check_connection,
            self._get_me,
            self._get_dialogs,
            # Добавьте свои действия здесь
        ]
        
        results = []
        for action in warmup_actions:
            try:
                result = await action()
                results.append({
                    'action': action.__name__,
                    'status': 'success',
                    'result': result
                })
                logger.info(f"Action {action.__name__} completed")
                await asyncio.sleep(2)  # Пауза между действиями
            except Exception as e:
                logger.error(f"Action {action.__name__} failed: {e}")
                results.append({
                    'action': action.__name__,
                    'status': 'error',
                    'error': str(e)
                })
        
        return results
    
    async def _check_connection(self):
        """Проверка соединения"""
        return await self.client.is_connected()
    
    async def _get_me(self):
        """Получение информации о себе"""
        me = await self.client.get_me()
        return {
            'id': me.id,
            'username': me.username,
            'phone': me.phone
        }
    
    async def _get_dialogs(self):
        """Получение списка диалогов"""
        dialogs = await self.client.get_dialogs(limit=10)
        return {
            'count': len(dialogs),
            'dialogs': [{'id': d.id, 'name': d.name} for d in dialogs[:5]]
        }
    
    async def report_to_control_api(self, results: list):
        """Отправка результатов в Control API"""
        import aiohttp
        
        payload = {
            'account_id': self.account_id,
            'script_id': self.script_id,
            'results': results,
            'status': 'completed' if all(r['status'] == 'success' for r in results) else 'partial'
        }
        
        headers = {
            'Authorization': f'Bearer {self.control_api_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.control_api_url}/api/v1/jobs/report",
                    json=payload,
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        logger.info("Results reported to control API")
                    else:
                        logger.warning(f"Control API returned status {resp.status}")
        except Exception as e:
            logger.error(f"Failed to report to control API: {e}")
    
    async def run(self):
        """Основной цикл worker'а"""
        try:
            await self.initialize_client()
            results = await self.execute_warmup_script()
            await self.report_to_control_api(results)
            logger.info("Worker completed successfully")
            return 0
        except Exception as e:
            logger.error(f"Worker failed: {e}", exc_info=True)
            return 1
        finally:
            if self.client:
                await self.client.disconnect()


async def main():
    """Точка входа"""
    worker = AndroidWorker()
    exit_code = await worker.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    asyncio.run(main())

