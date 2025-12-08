"""
Job Manager - управление задачами прогрева и автоматизации Telegram аккаунтов
"""
import os
import json
import asyncio
import random
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

# Попытка импорта APScheduler
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    print("WARNING: APScheduler не установлен. pip install apscheduler")


class JobType(str, Enum):
    """Типы задач"""
    WARMUP = "warmup"           # Прогрев аккаунта
    SUBSCRIBE = "subscribe"     # Подписка на каналы
    VIEW = "view"               # Просмотр постов
    REACT = "react"             # Реакции на посты
    MESSAGE = "message"         # Отправка сообщений
    JOIN_GROUP = "join_group"   # Вступление в группы
    PROFILE = "profile"         # Обновление профиля


class JobStatus(str, Enum):
    """Статусы задач"""
    PENDING = "pending"         # Ожидает выполнения
    SCHEDULED = "scheduled"     # Запланирована
    RUNNING = "running"         # Выполняется
    COMPLETED = "completed"     # Завершена
    FAILED = "failed"           # Ошибка
    CANCELLED = "cancelled"     # Отменена


@dataclass
class JobAction:
    """Действие в рамках задачи"""
    type: str                   # view, subscribe, react, message
    target: str                 # канал/группа/пользователь
    params: Dict = field(default_factory=dict)
    status: str = "pending"
    result: str = None
    executed_at: str = None


@dataclass
class Job:
    """Задача для выполнения"""
    id: str
    type: JobType
    name: str
    phones: List[str]           # Список телефонов для выполнения
    actions: List[JobAction]    # Действия
    status: JobStatus = JobStatus.PENDING
    
    # Расписание
    schedule_type: str = "once"  # once, interval, cron
    schedule_value: str = None   # "30m", "1h", "0 9 * * *"
    
    # Статистика
    created_at: str = None
    started_at: str = None
    completed_at: str = None
    progress: int = 0
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    
    # Логи
    logs: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['type'] = self.type.value if isinstance(self.type, JobType) else self.type
        data['status'] = self.status.value if isinstance(self.status, JobStatus) else self.status
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Job':
        data['type'] = JobType(data['type']) if isinstance(data['type'], str) else data['type']
        data['status'] = JobStatus(data['status']) if isinstance(data['status'], str) else data['status']
        data['actions'] = [JobAction(**a) if isinstance(a, dict) else a for a in data.get('actions', [])]
        return cls(**data)
    
    def add_log(self, message: str, level: str = "info"):
        self.logs.append({
            "time": datetime.now().isoformat(),
            "level": level,
            "message": message
        })
        # Ограничить логи
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]


# Популярные каналы для прогрева
WARMUP_CHANNELS = [
    "@telegram",
    "@durov",
    "@TelegramTips",
    "@TelegramRussian",
    "@temamusicnews",
    "@breakingmash",
    "@varlamov",
    "@medaboronin",
    "@laborproject",
]

# Популярные группы
WARMUP_GROUPS = [
    # Добавить публичные группы
]


class JobManager:
    """Менеджер задач"""
    
    def __init__(self, storage_path: str = "local-storage"):
        self.storage_path = Path(storage_path)
        self.jobs_file = self.storage_path / "jobs.json"
        self.history_file = self.storage_path / "jobs_history.json"
        
        self.jobs: Dict[str, Job] = {}
        self.history: List[Job] = []
        self.scheduler = None
        
        self._load_jobs()
        self._init_scheduler()
    
    def _init_scheduler(self):
        """Инициализировать планировщик"""
        if SCHEDULER_AVAILABLE:
            self.scheduler = AsyncIOScheduler()
            self.scheduler.start()
            print("[Jobs] Планировщик запущен")
    
    def _load_jobs(self):
        """Загрузить задачи"""
        if self.jobs_file.exists():
            try:
                with open(self.jobs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for job_data in data.get("jobs", []):
                        job = Job.from_dict(job_data)
                        self.jobs[job.id] = job
            except Exception as e:
                print(f"[Jobs] Ошибка загрузки: {e}")
        
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = [Job.from_dict(j) for j in data.get("history", [])]
            except:
                pass
    
    def _save_jobs(self):
        """Сохранить задачи"""
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            
            with open(self.jobs_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "jobs": [j.to_dict() for j in self.jobs.values()]
                }, f, indent=2, ensure_ascii=False)
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "history": [j.to_dict() for j in self.history[-100:]]  # Последние 100
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Jobs] Ошибка сохранения: {e}")
    
    def create_warmup_job(
        self,
        phones: List[str],
        name: str = None,
        channels: List[str] = None,
        actions_per_account: int = 5,
        schedule: str = None
    ) -> Job:
        """
        Создать задачу прогрева аккаунтов.
        
        Args:
            phones: Список телефонов
            name: Название задачи
            channels: Каналы для подписки/просмотра (или использовать дефолтные)
            actions_per_account: Количество действий на аккаунт
            schedule: Расписание ("30m", "1h", "daily")
        """
        job_id = f"warmup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        channels = channels or WARMUP_CHANNELS
        
        # Создать действия для каждого телефона
        actions = []
        for phone in phones:
            # Выбрать случайные каналы
            selected_channels = random.sample(channels, min(actions_per_account, len(channels)))
            
            for channel in selected_channels:
                # Случайное действие: просмотр или подписка
                action_type = random.choice(["view", "subscribe", "react"])
                actions.append(JobAction(
                    type=action_type,
                    target=channel,
                    params={"phone": phone}
                ))
        
        job = Job(
            id=job_id,
            type=JobType.WARMUP,
            name=name or f"Прогрев {len(phones)} аккаунтов",
            phones=phones,
            actions=actions,
            created_at=datetime.now().isoformat(),
            total_actions=len(actions),
            schedule_type="interval" if schedule else "once",
            schedule_value=schedule
        )
        
        self.jobs[job_id] = job
        self._save_jobs()
        
        # Запланировать если есть расписание
        if schedule and self.scheduler:
            self._schedule_job(job)
        
        return job
    
    def create_subscribe_job(
        self,
        phones: List[str],
        channels: List[str],
        name: str = None
    ) -> Job:
        """Создать задачу подписки на каналы"""
        job_id = f"subscribe_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        actions = []
        for phone in phones:
            for channel in channels:
                actions.append(JobAction(
                    type="subscribe",
                    target=channel,
                    params={"phone": phone}
                ))
        
        job = Job(
            id=job_id,
            type=JobType.SUBSCRIBE,
            name=name or f"Подписка на {len(channels)} каналов",
            phones=phones,
            actions=actions,
            created_at=datetime.now().isoformat(),
            total_actions=len(actions)
        )
        
        self.jobs[job_id] = job
        self._save_jobs()
        return job
    
    def create_view_job(
        self,
        phones: List[str],
        channels: List[str],
        posts_per_channel: int = 5,
        name: str = None
    ) -> Job:
        """Создать задачу просмотра постов"""
        job_id = f"view_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        actions = []
        for phone in phones:
            for channel in channels:
                actions.append(JobAction(
                    type="view",
                    target=channel,
                    params={"phone": phone, "count": posts_per_channel}
                ))
        
        job = Job(
            id=job_id,
            type=JobType.VIEW,
            name=name or f"Просмотр {len(channels)} каналов",
            phones=phones,
            actions=actions,
            created_at=datetime.now().isoformat(),
            total_actions=len(actions)
        )
        
        self.jobs[job_id] = job
        self._save_jobs()
        return job
    
    def _schedule_job(self, job: Job):
        """Запланировать задачу"""
        if not self.scheduler:
            return
        
        schedule = job.schedule_value
        
        if schedule.endswith('m'):
            # Интервал в минутах
            minutes = int(schedule[:-1])
            trigger = IntervalTrigger(minutes=minutes)
        elif schedule.endswith('h'):
            # Интервал в часах
            hours = int(schedule[:-1])
            trigger = IntervalTrigger(hours=hours)
        elif schedule == "daily":
            # Ежедневно в 10:00
            trigger = CronTrigger(hour=10, minute=0)
        else:
            # Cron выражение
            trigger = CronTrigger.from_crontab(schedule)
        
        self.scheduler.add_job(
            self._execute_job,
            trigger,
            args=[job.id],
            id=job.id,
            replace_existing=True
        )
        
        job.status = JobStatus.SCHEDULED
        self._save_jobs()
    
    async def _execute_job(self, job_id: str):
        """Выполнить задачу"""
        job = self.jobs.get(job_id)
        if not job:
            return
        
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now().isoformat()
        job.add_log(f"Задача запущена: {job.name}")
        self._save_jobs()
        
        try:
            for i, action in enumerate(job.actions):
                if job.status == JobStatus.CANCELLED:
                    break
                
                try:
                    result = await self._execute_action(action)
                    action.status = "completed"
                    action.result = result
                    action.executed_at = datetime.now().isoformat()
                    job.successful_actions += 1
                    job.add_log(f"✅ {action.type} -> {action.target}")
                except Exception as e:
                    action.status = "failed"
                    action.result = str(e)
                    job.failed_actions += 1
                    job.add_log(f"❌ {action.type} -> {action.target}: {e}", "error")
                
                job.progress = int((i + 1) / len(job.actions) * 100)
                self._save_jobs()
                
                # Пауза между действиями
                await asyncio.sleep(random.uniform(2, 5))
            
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now().isoformat()
            job.add_log(f"Задача завершена: {job.successful_actions}/{job.total_actions} успешно")
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.add_log(f"Критическая ошибка: {e}", "error")
        
        # Переместить в историю если одноразовая
        if job.schedule_type == "once":
            self.history.append(job)
            del self.jobs[job_id]
        
        self._save_jobs()
    
    async def _execute_action(self, action: JobAction) -> str:
        """Выполнить конкретное действие"""
        from telethon import TelegramClient
        from telethon.tl.functions.channels import JoinChannelRequest
        from telethon.tl.functions.messages import GetHistoryRequest
        
        phone = action.params.get("phone")
        if not phone:
            raise ValueError("Phone not specified")
        
        # Получить путь к сессии
        from pathlib import Path
        sessions_dir = self.storage_path / "sessions"
        session_file = sessions_dir / phone / f"{phone}.session"
        
        if not session_file.exists():
            raise FileNotFoundError(f"Session not found: {phone}")
        
        # Загрузить данные сессии
        json_file = sessions_dir / phone / f"{phone}.json"
        app_id = 2040
        app_hash = "b18441a1ff607e10a989891a5462e627"
        
        if json_file.exists():
            with open(json_file, 'r') as f:
                data = json.load(f)
                app_id = data.get("app_id", app_id)
                app_hash = data.get("app_hash", app_hash)
        
        # Создать клиент
        client = TelegramClient(str(session_file), int(app_id), app_hash)
        
        try:
            await client.connect()
            
            if not await client.is_user_authorized():
                raise PermissionError(f"Not authorized: {phone}")
            
            target = action.target
            
            if action.type == "subscribe":
                # Подписка на канал
                await client(JoinChannelRequest(target))
                return f"Subscribed to {target}"
            
            elif action.type == "view":
                # Просмотр постов
                entity = await client.get_entity(target)
                count = action.params.get("count", 5)
                
                messages = await client(GetHistoryRequest(
                    peer=entity,
                    limit=count,
                    offset_date=None,
                    offset_id=0,
                    max_id=0,
                    min_id=0,
                    add_offset=0,
                    hash=0
                ))
                
                # "Читаем" сообщения (имитация просмотра)
                for msg in messages.messages[:count]:
                    await asyncio.sleep(random.uniform(0.5, 2))
                
                return f"Viewed {len(messages.messages)} posts in {target}"
            
            elif action.type == "react":
                # Реакция на пост
                from telethon.tl.functions.messages import SendReactionRequest
                from telethon.tl.types import ReactionEmoji
                
                entity = await client.get_entity(target)
                messages = await client(GetHistoryRequest(
                    peer=entity,
                    limit=5,
                    offset_date=None,
                    offset_id=0,
                    max_id=0,
                    min_id=0,
                    add_offset=0,
                    hash=0
                ))
                
                if messages.messages:
                    msg = random.choice(messages.messages)
                    emoji = random.choice(["👍", "❤️", "🔥", "👏", "😂"])
                    
                    await client(SendReactionRequest(
                        peer=entity,
                        msg_id=msg.id,
                        reaction=[ReactionEmoji(emoticon=emoji)]
                    ))
                    return f"Reacted {emoji} to post in {target}"
                
                return "No messages to react"
            
            else:
                return f"Unknown action type: {action.type}"
        
        finally:
            await client.disconnect()
    
    async def run_job(self, job_id: str):
        """Запустить задачу вручную"""
        await self._execute_job(job_id)
    
    def cancel_job(self, job_id: str) -> bool:
        """Отменить задачу"""
        job = self.jobs.get(job_id)
        if not job:
            return False
        
        job.status = JobStatus.CANCELLED
        job.add_log("Задача отменена пользователем")
        
        if self.scheduler:
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass
        
        self._save_jobs()
        return True
    
    def delete_job(self, job_id: str) -> bool:
        """Удалить задачу"""
        if job_id in self.jobs:
            if self.scheduler:
                try:
                    self.scheduler.remove_job(job_id)
                except:
                    pass
            del self.jobs[job_id]
            self._save_jobs()
            return True
        return False
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Получить задачу"""
        return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> List[Job]:
        """Получить все задачи"""
        return list(self.jobs.values())
    
    def get_history(self, limit: int = 50) -> List[Job]:
        """Получить историю"""
        return self.history[-limit:]
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        total = len(self.jobs)
        running = sum(1 for j in self.jobs.values() if j.status == JobStatus.RUNNING)
        scheduled = sum(1 for j in self.jobs.values() if j.status == JobStatus.SCHEDULED)
        completed = len(self.history)
        
        return {
            "total_jobs": total,
            "running": running,
            "scheduled": scheduled,
            "completed": completed,
            "history_count": len(self.history)
        }


# Глобальный экземпляр
job_manager: Optional[JobManager] = None


def get_job_manager(storage_path: str = "local-storage") -> JobManager:
    """Получить или создать менеджер задач"""
    global job_manager
    if job_manager is None:
        job_manager = JobManager(storage_path)
    return job_manager

