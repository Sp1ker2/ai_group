#!/usr/bin/env python3
"""
Android Worker для выполнения Telegram warm-up задач
Поддерживает локальное хранение сессий
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
        self.local_sessions_path = Path('local-storage/sessions')  # Локальное хранение
        self.client: Optional[TelegramClient] = None
        
        # Настройки для группового общения
        self.enable_group_chat = os.getenv('ENABLE_GROUP_CHAT', 'false').lower() == 'true'
        self.group_id = os.getenv('GROUP_ID', '')
        self.group_title = os.getenv('GROUP_TITLE', '')
        self.member_phones = os.getenv('MEMBER_PHONES', '').split(',') if os.getenv('MEMBER_PHONES') else []
        
        if not self.phone_number:
            raise ValueError("PHONE_NUMBER environment variable is required")
        if not self.account_id:
            raise ValueError("ACCOUNT_ID environment variable is required")
    
    async def load_session_local(self):
        """Загрузить session из локальной папки (приоритет, включая подпапки)"""
        try:
            # Сначала по номеру телефона
            phone_filename = self.phone_number.replace('+', '').replace('-', '').replace(' ', '')
            
            # 1. Попробовать загрузить .json файл напрямую
            json_file = self.local_sessions_path / f"{phone_filename}.json"
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                logger.info(f"Session JSON loaded from local storage: {json_file.name}")
                return session_data
            
            # 2. Попробовать найти в подпапке (например, 573025288905/573025288905.json)
            folder_path = self.local_sessions_path / phone_filename
            if folder_path.exists() and folder_path.is_dir():
                json_file = folder_path / f"{phone_filename}.json"
                if json_file.exists():
                    with open(json_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    logger.info(f"Session JSON loaded from subfolder: {json_file}")
                    return session_data
                
                # Также попробовать .session в подпапке
                session_file = folder_path / f"{phone_filename}.session"
                if session_file.exists():
                    logger.info(f"Session file found in subfolder: {session_file}")
                    return {
                        "phone_number": self.phone_number,
                        "session_file": str(session_file),
                        "has_session_file": True
                    }
            
            # 3. Рекурсивный поиск по имени файла
            for json_file in self.local_sessions_path.rglob(f"{phone_filename}.json"):
                with open(json_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                logger.info(f"Session JSON found recursively: {json_file}")
                return session_data
            
            # 4. Попробовать .session файл напрямую
            session_file = self.local_sessions_path / f"{phone_filename}.session"
            if session_file.exists():
                logger.info(f"Session file found: {session_file.name}")
                return {
                    "phone_number": self.phone_number,
                    "session_file": str(session_file),
                    "has_session_file": True
                }
            
            # 5. Рекурсивный поиск .session файлов
            for session_file in self.local_sessions_path.rglob(f"{phone_filename}.session"):
                logger.info(f"Session file found recursively: {session_file}")
                return {
                    "phone_number": self.phone_number,
                    "session_file": str(session_file),
                    "has_session_file": True
                }
            
            # Fallback: по account_id
            json_file = self.local_sessions_path / f"session_{self.account_id}.json"
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                logger.info(f"Session loaded from local storage: {json_file.name}")
                return session_data
                
        except Exception as e:
            logger.warning(f"Failed to load local session: {e}")
        return None
    
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
        
        # 1. Попытаться загрузить из локальной папки (приоритет)
        session_data = await self.load_session_local()
        
        # 2. Если нет локально, попробовать S3
        if not session_data:
            session_data = await self.load_session_from_s3()
        
        if session_data:
            api_id = session_data.get('api_id') or os.getenv('TELEGRAM_API_ID', '')
            api_hash = session_data.get('api_hash') or os.getenv('TELEGRAM_API_HASH', '')
            
            # Если есть .session файл, использовать его напрямую
            if session_data.get('has_session_file') and session_data.get('session_file'):
                session_file_path = session_data.get('session_file')
                self.client = TelegramClient(
                    session_file_path,
                    api_id=int(api_id) if api_id else None,
                    api_hash=api_hash
                )
                await self.client.start()
                logger.info(f"Client initialized from .session file: {session_file_path}")
                return
            
            # Иначе использовать StringSession из JSON
            session_string = session_data.get('session_string')
            if session_string:
                self.client = TelegramClient(
                    StringSession(session_string),
                    api_id=int(api_id),
                    api_hash=api_hash
                )
                await self.client.start()
                logger.info("Client initialized from session string")
                return
        
        # Fallback: использовать локальный файл .session
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
        
        # Если включено общение между аккаунтами
        if self.enable_group_chat:
            warmup_actions.extend([
                self._create_or_join_group,
                self._send_message_to_group,
            ])
        
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
    
    async def _create_or_join_group(self):
        """Создать или присоединиться к группе"""
        group_title = os.getenv('GROUP_TITLE', f'Warm-up Group {self.account_id}')
        group_username = os.getenv('GROUP_USERNAME', '')  # Опционально
        
        try:
            # Попытаться найти существующую группу
            if group_username:
                try:
                    entity = await self.client.get_entity(group_username)
                    if entity:
                        logger.info(f"Found existing group: {group_username}")
                        return {
                            'action': 'joined',
                            'group_id': entity.id,
                            'group_username': group_username
                        }
                except:
                    pass
            
            # Создать новую группу
            created = await self.client.create_group(
                title=group_title,
                users=[]  # Участники добавятся позже
            )
            
            logger.info(f"Created group: {created.id}")
            
            # Если указан username, установить его
            if group_username:
                try:
                    await self.client.edit_chat(created.id, username=group_username)
                except Exception as e:
                    logger.warning(f"Could not set username: {e}")
            
            return {
                'action': 'created',
                'group_id': created.id,
                'group_title': group_title
            }
        except Exception as e:
            logger.error(f"Failed to create/join group: {e}")
            return {'error': str(e)}
    
    async def _add_members_to_group(self, group_id, phone_numbers: list):
        """Добавить участников в группу"""
        try:
            # Получить entity группы
            group = await self.client.get_entity(group_id)
            
            # Добавить участников
            added = []
            for phone in phone_numbers:
                try:
                    user = await self.client.get_entity(phone)
                    await self.client.add_participants(group, [user])
                    added.append(phone)
                    await asyncio.sleep(1)  # Пауза между добавлениями
                except Exception as e:
                    logger.warning(f"Could not add {phone}: {e}")
            
            return {
                'group_id': group_id,
                'added_count': len(added),
                'added': added
            }
        except Exception as e:
            logger.error(f"Failed to add members: {e}")
            return {'error': str(e)}
    
    async def _send_message_to_group(self):
        """Отправить сообщение в группу"""
        group_id = os.getenv('GROUP_ID', '')
        message_text = os.getenv('MESSAGE_TEXT', f'Hello from {self.account_id}!')
        
        if not group_id:
            # Попытаться найти группу по названию
            group_title = os.getenv('GROUP_TITLE', '')
            if group_title:
                dialogs = await self.client.get_dialogs()
                for dialog in dialogs:
                    if dialog.name == group_title:
                        group_id = dialog.id
                        break
        
        if not group_id:
            logger.warning("No group ID specified, skipping message")
            return {'skipped': 'no_group_id'}
        
        try:
            # Отправить сообщение
            sent = await self.client.send_message(int(group_id), message_text)
            
            return {
                'group_id': group_id,
                'message_id': sent.id,
                'message_text': message_text
            }
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return {'error': str(e)}
    
    async def _read_group_messages(self, group_id, limit=10):
        """Прочитать сообщения из группы"""
        try:
            messages = await self.client.get_messages(group_id, limit=limit)
            return {
                'group_id': group_id,
                'messages_count': len(messages),
                'messages': [
                    {
                        'id': msg.id,
                        'text': msg.text[:100] if msg.text else '',
                        'date': str(msg.date)
                    }
                    for msg in messages[:5]
                ]
            }
        except Exception as e:
            logger.error(f"Failed to read messages: {e}")
            return {'error': str(e)}
    
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
