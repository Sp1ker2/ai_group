"""
Life Simulator - симуляция живого человека для прогрева Telegram аккаунтов
Каждый аккаунт имеет свой "характер" и расписание активности
"""
import os
import json
import asyncio
import random
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, asdict, field
from datetime import datetime, time, timedelta
from enum import Enum
import hashlib


class LifeStyle(str, Enum):
    """Стили жизни персон"""
    WORKER = "worker"           # Офисный работник: мало днём, активен вечером
    STUDENT = "student"         # Студент: активен днём и вечером
    FREELANCER = "freelancer"   # Фрилансер: хаотичная активность
    NIGHT_OWL = "night_owl"     # Сова: активен поздно вечером и ночью
    EARLY_BIRD = "early_bird"   # Жаворонок: активен рано утром
    HOUSEWIFE = "housewife"     # Домохозяйка: активна весь день с перерывами
    RETIRED = "retired"         # Пенсионер: размеренная активность


@dataclass
class PersonaSchedule:
    """Расписание активности персоны"""
    # Часы активности для будних дней (0-23)
    weekday_active_hours: List[int] = field(default_factory=list)
    # Часы активности для выходных
    weekend_active_hours: List[int] = field(default_factory=list)
    # Пиковые часы (повышенная активность)
    peak_hours: List[int] = field(default_factory=list)
    # Минимальный интервал между действиями (минуты)
    min_interval: int = 15
    # Максимальный интервал
    max_interval: int = 120
    # Шанс пропустить час (0-100)
    skip_chance: int = 30


@dataclass  
class Persona:
    """Персона аккаунта - характер и поведение"""
    phone: str
    name: str
    lifestyle: LifeStyle
    schedule: PersonaSchedule
    
    # Предпочтения контента (веса 0-100)
    content_preferences: Dict[str, int] = field(default_factory=dict)
    # Любимые каналы
    favorite_channels: List[str] = field(default_factory=list)
    # Интересы (для генерации контента)
    interests: List[str] = field(default_factory=list)
    
    # Статистика
    last_activity: str = None
    actions_today: int = 0
    total_actions: int = 0
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['lifestyle'] = self.lifestyle.value
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Persona':
        data['lifestyle'] = LifeStyle(data['lifestyle'])
        data['schedule'] = PersonaSchedule(**data['schedule'])
        return cls(**data)


# Шаблоны расписаний по стилям жизни
LIFESTYLE_SCHEDULES = {
    LifeStyle.WORKER: PersonaSchedule(
        weekday_active_hours=[7, 8, 12, 13, 18, 19, 20, 21],  # Утро, обед, вечер
        weekend_active_hours=[9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
        peak_hours=[12, 13, 19, 20],  # Обед и вечер
        min_interval=30,
        max_interval=180,
        skip_chance=40
    ),
    LifeStyle.STUDENT: PersonaSchedule(
        weekday_active_hours=[9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22],
        weekend_active_hours=[11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
        peak_hours=[13, 14, 20, 21, 22],
        min_interval=15,
        max_interval=90,
        skip_chance=25
    ),
    LifeStyle.FREELANCER: PersonaSchedule(
        weekday_active_hours=[10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
        weekend_active_hours=[10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        peak_hours=[11, 12, 15, 16, 20],
        min_interval=20,
        max_interval=120,
        skip_chance=35
    ),
    LifeStyle.NIGHT_OWL: PersonaSchedule(
        weekday_active_hours=[12, 13, 14, 15, 18, 19, 20, 21, 22, 23],
        weekend_active_hours=[13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 0],
        peak_hours=[21, 22, 23],
        min_interval=20,
        max_interval=90,
        skip_chance=30
    ),
    LifeStyle.EARLY_BIRD: PersonaSchedule(
        weekday_active_hours=[6, 7, 8, 9, 12, 13, 17, 18, 19],
        weekend_active_hours=[7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        peak_hours=[7, 8, 12, 17],
        min_interval=30,
        max_interval=150,
        skip_chance=35
    ),
    LifeStyle.HOUSEWIFE: PersonaSchedule(
        weekday_active_hours=[9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        weekend_active_hours=[9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
        peak_hours=[10, 11, 14, 15, 19, 20],
        min_interval=20,
        max_interval=90,
        skip_chance=20
    ),
    LifeStyle.RETIRED: PersonaSchedule(
        weekday_active_hours=[8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19],
        weekend_active_hours=[8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19],
        peak_hours=[9, 10, 15, 16],
        min_interval=45,
        max_interval=180,
        skip_chance=40
    ),
}

# Предпочтения контента по стилям
LIFESTYLE_CONTENT = {
    LifeStyle.WORKER: {"text": 40, "photo": 15, "video": 10, "gif": 15, "sticker": 10, "link": 10},
    LifeStyle.STUDENT: {"text": 30, "photo": 20, "video": 15, "gif": 20, "sticker": 10, "link": 5},
    LifeStyle.FREELANCER: {"text": 35, "photo": 15, "video": 15, "gif": 15, "sticker": 10, "link": 10},
    LifeStyle.NIGHT_OWL: {"text": 30, "photo": 15, "video": 20, "gif": 20, "sticker": 10, "link": 5},
    LifeStyle.EARLY_BIRD: {"text": 45, "photo": 15, "video": 10, "gif": 10, "sticker": 10, "link": 10},
    LifeStyle.HOUSEWIFE: {"text": 35, "photo": 25, "video": 15, "gif": 10, "sticker": 10, "link": 5},
    LifeStyle.RETIRED: {"text": 50, "photo": 20, "video": 10, "gif": 5, "sticker": 5, "link": 10},
}

# Интересы по стилям
LIFESTYLE_INTERESTS = {
    LifeStyle.WORKER: ["работа", "бизнес", "новости", "спорт", "отдых", "путешествия"],
    LifeStyle.STUDENT: ["учёба", "музыка", "игры", "фильмы", "мемы", "технологии"],
    LifeStyle.FREELANCER: ["IT", "дизайн", "маркетинг", "саморазвитие", "путешествия"],
    LifeStyle.NIGHT_OWL: ["игры", "фильмы", "музыка", "аниме", "технологии"],
    LifeStyle.EARLY_BIRD: ["спорт", "здоровье", "новости", "природа", "саморазвитие"],
    LifeStyle.HOUSEWIFE: ["рецепты", "дети", "дом", "здоровье", "шоппинг", "сериалы"],
    LifeStyle.RETIRED: ["здоровье", "новости", "история", "природа", "внуки", "сад"],
}

# Популярные каналы для разных интересов
INTEREST_CHANNELS = {
    "новости": ["@breakingmash", "@rian_ru", "@taborisha"],
    "технологии": ["@teknoblog", "@habr_com", "@iguides"],
    "музыка": ["@muzyka", "@music_news"],
    "игры": ["@gamedevsru", "@games_news"],
    "спорт": ["@sport24ru", "@sportexpress"],
    "путешествия": ["@travel_blog", "@world_travel"],
    "здоровье": ["@zdorovie", "@medportal"],
    "бизнес": ["@biznesnews", "@rbc_news"],
    "мемы": ["@memes_ru", "@funny_pics"],
    "фильмы": ["@kinoblog", "@cinema_news"],
}


class LifeSimulator:
    """Симулятор живой активности для аккаунтов"""
    
    def __init__(self, storage_path: str = "local-storage"):
        self.storage_path = Path(storage_path)
        self.personas_file = self.storage_path / "personas.json"
        self.personas: Dict[str, Persona] = {}
        self.active = False
        self._load_personas()
    
    def _load_personas(self):
        """Загрузить персоны"""
        if self.personas_file.exists():
            try:
                with open(self.personas_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for phone, persona_data in data.items():
                        self.personas[phone] = Persona.from_dict(persona_data)
            except Exception as e:
                print(f"[Life] Ошибка загрузки: {e}")
    
    def _save_personas(self):
        """Сохранить персоны"""
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            with open(self.personas_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {p.phone: p.to_dict() for p in self.personas.values()},
                    f, indent=2, ensure_ascii=False
                )
        except Exception as e:
            print(f"[Life] Ошибка сохранения: {e}")
    
    def generate_persona(self, phone: str, name: str = None) -> Persona:
        """Сгенерировать уникальную персону для аккаунта"""
        # Детерминированный выбор на основе телефона
        seed = int(hashlib.md5(phone.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        
        # Выбрать стиль жизни
        lifestyle = rng.choice(list(LifeStyle))
        
        # Получить базовое расписание и немного рандомизировать
        base_schedule = LIFESTYLE_SCHEDULES[lifestyle]
        schedule = PersonaSchedule(
            weekday_active_hours=base_schedule.weekday_active_hours.copy(),
            weekend_active_hours=base_schedule.weekend_active_hours.copy(),
            peak_hours=base_schedule.peak_hours.copy(),
            min_interval=base_schedule.min_interval + rng.randint(-5, 10),
            max_interval=base_schedule.max_interval + rng.randint(-20, 30),
            skip_chance=base_schedule.skip_chance + rng.randint(-10, 10)
        )
        
        # Немного рандомизировать часы
        if rng.random() > 0.5:
            # Сдвинуть расписание на 1-2 часа
            shift = rng.choice([-2, -1, 1, 2])
            schedule.weekday_active_hours = [
                (h + shift) % 24 for h in schedule.weekday_active_hours
            ]
        
        # Контент предпочтения
        content_prefs = LIFESTYLE_CONTENT[lifestyle].copy()
        # Рандомизировать
        for key in content_prefs:
            content_prefs[key] += rng.randint(-10, 10)
            content_prefs[key] = max(0, min(100, content_prefs[key]))
        
        # Интересы
        base_interests = LIFESTYLE_INTERESTS[lifestyle].copy()
        rng.shuffle(base_interests)
        interests = base_interests[:rng.randint(3, len(base_interests))]
        
        # Любимые каналы на основе интересов
        favorite_channels = []
        for interest in interests[:3]:
            channels = INTEREST_CHANNELS.get(interest.lower(), [])
            if channels:
                favorite_channels.extend(rng.sample(channels, min(2, len(channels))))
        
        # Добавить общие каналы
        favorite_channels.extend(["@telegram", "@durov"])
        
        persona = Persona(
            phone=phone,
            name=name or f"User_{phone[-4:]}",
            lifestyle=lifestyle,
            schedule=schedule,
            content_preferences=content_prefs,
            favorite_channels=list(set(favorite_channels)),
            interests=interests
        )
        
        self.personas[phone] = persona
        self._save_personas()
        
        return persona
    
    def get_persona(self, phone: str) -> Optional[Persona]:
        """Получить или создать персону"""
        if phone not in self.personas:
            return self.generate_persona(phone)
        return self.personas[phone]
    
    def should_be_active(self, persona: Persona) -> bool:
        """Должен ли аккаунт быть активен сейчас?"""
        now = datetime.now()
        hour = now.hour
        is_weekend = now.weekday() >= 5
        
        # Получить активные часы
        active_hours = (
            persona.schedule.weekend_active_hours if is_weekend 
            else persona.schedule.weekday_active_hours
        )
        
        if hour not in active_hours:
            return False
        
        # Шанс пропустить
        if random.randint(0, 100) < persona.schedule.skip_chance:
            return False
        
        return True
    
    def get_activity_level(self, persona: Persona) -> float:
        """Получить уровень активности (0.0 - 1.0)"""
        now = datetime.now()
        hour = now.hour
        is_weekend = now.weekday() >= 5
        
        # Базовый уровень
        level = 0.5
        
        # Пиковые часы
        if hour in persona.schedule.peak_hours:
            level += 0.3
        
        # Выходные - больше активности
        if is_weekend:
            level += 0.2
        
        # Рандом
        level += random.uniform(-0.1, 0.1)
        
        return max(0.1, min(1.0, level))
    
    def get_next_action_delay(self, persona: Persona) -> int:
        """Получить задержку до следующего действия (секунды)"""
        activity_level = self.get_activity_level(persona)
        
        # Базовый интервал
        min_interval = persona.schedule.min_interval
        max_interval = persona.schedule.max_interval
        
        # Корректировка по активности
        interval = min_interval + (max_interval - min_interval) * (1 - activity_level)
        
        # Добавить случайность
        interval *= random.uniform(0.7, 1.5)
        
        return int(interval * 60)  # в секундах
    
    def choose_content_type(self, persona: Persona) -> str:
        """Выбрать тип контента для отправки"""
        prefs = persona.content_preferences
        types = list(prefs.keys())
        weights = list(prefs.values())
        
        return random.choices(types, weights=weights, k=1)[0]
    
    def choose_channel(self, persona: Persona) -> str:
        """Выбрать канал для активности"""
        if persona.favorite_channels and random.random() > 0.3:
            return random.choice(persona.favorite_channels)
        
        # Случайный из общих
        all_channels = []
        for channels in INTEREST_CHANNELS.values():
            all_channels.extend(channels)
        
        return random.choice(all_channels) if all_channels else "@telegram"
    
    def generate_for_all_accounts(self, sessions_dir: Path = None) -> Dict[str, Persona]:
        """Сгенерировать персоны для всех аккаунтов"""
        if sessions_dir is None:
            sessions_dir = self.storage_path / "sessions"
        
        generated = {}
        
        if not sessions_dir.exists():
            return generated
        
        for phone_dir in sessions_dir.iterdir():
            if not phone_dir.is_dir():
                continue
            
            phone = phone_dir.name
            if not phone.isdigit():
                continue
            
            # Загрузить имя из session.json если есть
            name = None
            json_file = phone_dir / f"{phone}.json"
            if json_file.exists():
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        name = data.get("first_name")
                except:
                    pass
            
            persona = self.generate_persona(phone, name)
            generated[phone] = persona
        
        return generated
    
    def get_status(self) -> Dict:
        """Получить статус симулятора"""
        lifestyles = {}
        for persona in self.personas.values():
            ls = persona.lifestyle.value
            lifestyles[ls] = lifestyles.get(ls, 0) + 1
        
        return {
            "total_personas": len(self.personas),
            "active": self.active,
            "lifestyles_distribution": lifestyles,
            "personas": {p.phone: p.to_dict() for p in self.personas.values()}
        }
    
    def get_active_accounts_now(self) -> List[Persona]:
        """Получить аккаунты которые должны быть активны сейчас"""
        return [p for p in self.personas.values() if self.should_be_active(p)]


# Глобальный экземпляр
life_simulator: Optional[LifeSimulator] = None


def get_life_simulator(storage_path: str = "local-storage") -> LifeSimulator:
    """Получить симулятор"""
    global life_simulator
    if life_simulator is None:
        life_simulator = LifeSimulator(storage_path)
    return life_simulator

