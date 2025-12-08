"""
AI интеграция для генерации сообщений в Telegram группах по темам
Поддержка: OpenAI, Groq (бесплатный!)
"""
import os
import random
import asyncio
import json
import httpx
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

# Попытка импорта openai (работает и для Groq)
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("WARNING: openai не установлен. Установите: pip install openai")

# ========== API КЛЮЧИ ==========
# Groq (бесплатный) - получить на https://console.groq.com/keys
# Ключ задается через UI или переменную окружения GROQ_API_KEY
DEFAULT_GROQ_API_KEY = ""

# OpenAI (платный) - получить на https://platform.openai.com/api-keys  
DEFAULT_OPENAI_API_KEY = ""
# ================================

# Конфигурация провайдеров AI
AI_PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-8b-instant",  # Быстрая бесплатная модель
        "name": "Groq (FREE)",
        "default_key": DEFAULT_GROQ_API_KEY
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-3.5-turbo",
        "name": "OpenAI",
        "default_key": DEFAULT_OPENAI_API_KEY
    }
}


# Личности для участников чата
PERSONALITIES = [
    {
        "name": "Оптимист",
        "style": "Всегда позитивный, видит хорошее во всем, использует эмодзи",
        "emoji": ["😊", "👍", "🔥", "💪", "✨"]
    },
    {
        "name": "Аналитик", 
        "style": "Логичный, любит факты и статистику, задает уточняющие вопросы",
        "emoji": ["🤔", "📊", "💡", "📈"]
    },
    {
        "name": "Душа компании",
        "style": "Шутит, рассказывает истории, поддерживает беседу",
        "emoji": ["😂", "🤣", "😄", "🎉"]
    },
    {
        "name": "Практик",
        "style": "Дает полезные советы, делится опытом, конкретный",
        "emoji": ["👌", "✅", "💯"]
    },
    {
        "name": "Мечтатель",
        "style": "Философствует, размышляет о жизни, творческий",
        "emoji": ["🌟", "💭", "🎨", "🌈"]
    },
    {
        "name": "Скептик",
        "style": "Сомневается, спрашивает 'а зачем?', но дружелюбно",
        "emoji": ["🧐", "❓", "🤷"]
    },
    {
        "name": "Энтузиаст",
        "style": "Все пробует, делится впечатлениями, очень активный",
        "emoji": ["🚀", "⚡", "🎯", "💥"]
    },
    {
        "name": "Ностальгик",
        "style": "Вспоминает прошлое, сравнивает с настоящим",
        "emoji": ["📷", "🎵", "💫"]
    },
    {
        "name": "Гурман",
        "style": "Любит поесть, знает рецепты, обсуждает рестораны",
        "emoji": ["🍕", "🍔", "🍰", "☕"]
    },
    {
        "name": "Путешественник",
        "style": "Много где был, рассказывает истории из поездок",
        "emoji": ["✈️", "🌍", "🗺️", "🏖️"]
    }
]


class TopicManager:
    """Менеджер тем для общения"""
    
    def __init__(self, topics_file: str = None):
        self.topics = []
        self.default_topic = "travel"
        
        if topics_file and Path(topics_file).exists():
            self.load_topics(topics_file)
    
    def load_topics(self, filepath: str):
        """Загрузить темы из файла"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.topics = data.get("topics", [])
                self.default_topic = data.get("default_topic", "travel")
        except Exception as e:
            print(f"Ошибка загрузки тем: {e}")
    
    def get_topic(self, topic_id: str) -> dict:
        """Получить тему по ID"""
        for topic in self.topics:
            if topic["id"] == topic_id:
                return topic
        return self.topics[0] if self.topics else None
    
    def get_all_topics(self) -> list:
        """Получить все темы"""
        return self.topics
    
    def get_random_prompt(self, topic_id: str) -> str:
        """Получить случайный промпт для темы"""
        topic = self.get_topic(topic_id)
        if topic and topic.get("prompts"):
            return random.choice(topic["prompts"])
        return "Привет! Как дела?"


class OpenAIChatManager:
    """Менеджер для генерации сообщений через AI (OpenAI или Groq)"""
    
    def __init__(self, api_key: str = None, provider: str = "groq"):
        """
        Инициализация менеджера.
        
        Args:
            api_key: API ключ (для Groq или OpenAI)
            provider: "groq" (бесплатный) или "openai"
        """
        self.provider = provider
        self.provider_config = AI_PROVIDERS.get(provider, AI_PROVIDERS["groq"])
        
        # Приоритет ключей: переданный > env > дефолтный в коде
        self.api_key = (
            api_key or 
            os.getenv("GROQ_API_KEY") or 
            os.getenv("OPENAI_API_KEY") or
            self.provider_config.get("default_key", "")
        )
        
        self.client = None
        self.conversation_history: Dict[str, List[dict]] = {}
        self.topic_manager = TopicManager()
        self.model = self.provider_config["model"]
        
        if OPENAI_AVAILABLE and self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.provider_config["base_url"]
            )
            print(f"[AI] Используется: {self.provider_config['name']} ({self.model})")
        else:
            print(f"[AI] ВНИМАНИЕ: Ключ не найден! Будут использоваться fallback сообщения.")
    
    def set_topics_file(self, filepath: str):
        """Установить файл тем"""
        self.topic_manager = TopicManager(filepath)
    
    def assign_personality(self, member_index: int) -> dict:
        """Назначить личность участнику"""
        return PERSONALITIES[member_index % len(PERSONALITIES)]
    
    def _extract_key_phrases(self, context: List[str]) -> List[str]:
        """Извлечь ключевые фразы из истории чтобы не повторять"""
        phrases = []
        for msg in context[-10:]:
            # Извлекаем уникальные части сообщений
            if "помню когда" in msg.lower():
                phrases.append("история из прошлого")
            if "друг" in msg.lower() and ("хакер" in msg.lower() or "гений" in msg.lower()):
                phrases.append("друг-хакер")
            if "институт" in msg.lower() or "университет" in msg.lower():
                phrases.append("учёба")
            if "система защиты" in msg.lower():
                phrases.append("система защиты")
            if "девушка" in msg.lower() and ("гений" in msg.lower() or "создала" in msg.lower()):
                phrases.append("девушка-гений")
            if "хакерские романы" in msg.lower():
                phrases.append("хакерские романы")
            if "minecraft" in msg.lower():
                phrases.append("minecraft")
        return list(set(phrases))
    
    def _is_duplicate(self, new_msg: str, context: List[str]) -> bool:
        """Проверить не дубликат ли сообщение"""
        new_lower = new_msg.lower()
        
        for old_msg in context[-5:]:
            old_lower = old_msg.lower()
            # Проверяем совпадение начала
            if new_lower[:50] == old_lower.split(": ", 1)[-1][:50]:
                return True
            # Проверяем одинаковые вопросы
            if "?" in new_msg and new_msg.split("?")[0] in old_msg:
                return True
        return False

    async def generate_message(
        self,
        group_id: str,
        sender_name: str,
        sender_personality: dict,
        topic: dict = None,
        context: List[str] = None,
        is_first_message: bool = False
    ) -> str:
        """Генерировать сообщение для участника по теме"""
        
        if not self.client:
            return self._generate_fallback_message(sender_personality, topic, is_first_message)
        
        topic_name = topic.get("name", "общие темы") if topic else "общие темы"
        topic_desc = topic.get("description", "") if topic else ""
        
        # Построить промпт - больше контекста для лучших ответов
        last_messages = "\n".join(context[-15:]) if context else "Пока пусто, ты первый пишешь"
        
        # Извлечь что уже обсуждалось - НЕ ПОВТОРЯТЬ!
        used_phrases = self._extract_key_phrases(context or [])
        forbidden = ""
        if used_phrases:
            forbidden = f"\n\n⛔ УЖЕ ОБСУЖДАЛОСЬ (НЕ ПОВТОРЯЙ ЭТО!): {', '.join(used_phrases)}"
        
        system_prompt = f"""Ты {sender_name} - реальный человек в групповом чате. НЕ бот!
Личность: {sender_personality['name']} - {sender_personality['style']}

ТЕМА: {topic_name}
{topic_desc}

ИСТОРИЯ ЧАТА (прочитай внимательно!):
{last_messages}
{forbidden}

⚠️ КРИТИЧЕСКИ ВАЖНО - НЕ ПОВТОРЯЙ:
- НЕ рассказывай истории про друзей-хакеров если кто-то уже рассказал
- НЕ повторяй вопросы которые уже задавали (смотри историю!)
- НЕ пиши то же самое что написал кто-то до тебя
- КАЖДОЕ сообщение должно быть УНИКАЛЬНЫМ
- Если кто-то задал вопрос - ОТВЕТЬ на него, не задавай тот же вопрос!

КАК ПИСАТЬ:
1. ОТВЕЧАЙ на последнее сообщение конкретно!
2. Добавляй НОВУЮ информацию, не повторяй старую
3. Пиши с опечатками: "чо", "щас", "норм", "ваще", "блин"
4. Иногда без запятых и точек как в реальном чате
5. Можно спорить, соглашаться, шутить - но по-разному!
6. Эмодзи редко: {random.choice(sender_personality.get('emoji', ['👍']))}

ФОРМАТЫ ОТВЕТОВ (выбери один, не повторяй предыдущих):
- Согласие + свой пример: "да точно, у меня тоже было..."
- Несогласие: "ну хз не уверен, мне кажется..."
- Дополнение: "кстати ещё важно что..."
- Вопрос (только если не спрашивали!): "а ты пробовал...?"
- Шутка: "хах это напомнило когда..."
- Факт: "я читал что на самом деле..."
"""

        messages = [{"role": "system", "content": system_prompt}]
        
        if is_first_message:
            messages.append({"role": "user", "content": f"Начни беседу на тему '{topic_name}'. Поделись личным опытом или мнением. 2-3 предложения с опечатками."})
        else:
            last_msg = context[-1] if context else ""
            last_sender = last_msg.split(":")[0] if ":" in last_msg else "Кто-то"
            last_text = last_msg.split(": ", 1)[-1] if ": " in last_msg else last_msg
            
            if "?" in last_text:
                messages.append({"role": "user", "content": f"{last_sender} спросил: '{last_text}'\n\nОТВЕТЬ НА ВОПРОС! Не задавай тот же вопрос. Дай конкретный ответ со своим опытом."})
            else:
                messages.append({"role": "user", "content": f"Последнее от {last_sender}: '{last_text}'\n\nОтреагируй КОНКРЕТНО на это. Согласись/поспорь/дополни. НЕ повторяй чужие истории, расскажи СВОЁ."})
        
        try:
            # Попытка сгенерировать уникальное сообщение (до 3 попыток)
            for attempt in range(3):
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=200,
                    temperature=0.95 + (attempt * 0.02)  # Увеличиваем креатив с каждой попыткой
                )
                result = response.choices[0].message.content.strip()
                
                # Проверка на дубликат
                if not self._is_duplicate(result, context or []):
                    return result
                print(f"[AI] Дубликат на попытке {attempt+1}, генерирую заново...")
            
            # Если все попытки дали дубликаты - возвращаем fallback
            return self._generate_fallback_message(sender_personality, topic, is_first_message)
            
        except Exception as e:
            print(f"[AI] Error ({self.provider}): {e}")
            return self._generate_fallback_message(sender_personality, topic, is_first_message)
    
    def _generate_fallback_message(self, personality: dict, topic: dict = None, is_first: bool = False) -> str:
        """Fallback сообщения если AI не работает - как реальный человек"""
        
        emoji = random.choice(personality.get("emoji", ["👍"]))
        topic_name = topic.get("name", "") if topic else ""
        
        greetings = [
            f"прив всем! {emoji} чо как дела",
            f"здаров)) давно не писал сюда",
            f"о привте {emoji} что нового",
            f"хай! что обсуждаем",
            f"всем прив {emoji}",
        ]
        
        # Разные типы ответов
        agreements = [
            f"да согласен {emoji}",
            f"точно! сам так думаю",
            f"ага плюсую",
            f"это да {emoji}",
        ]
        
        disagreements = [
            f"ну хз не уверен",
            f"спорно как по мне",
            f"не знаю, мне кажется по другому",
            f"хмм сомневаюсь {emoji}",
        ]
        
        additions = [
            f"кстати ещё важно что {topic_name} это не только про это {emoji}",
            f"а ещё я заметил интересную штуку",
            f"о и вот что ещё скажу",
            f"плюс к этому {emoji}",
        ]
        
        questions = [
            f"а вы чо думаете? {emoji}",
            f"интересно а как у вас с этим",
            f"кто пробовал расскажите {emoji}",
        ]
        
        reactions = [
            f"хах {emoji}",
            f"ого",
            f"ну такое",
            f"прикольно {emoji}",
            f"жиза",
        ]
        
        if is_first:
            return random.choice(greetings)
        
        # Выбираем случайный тип ответа
        response_type = random.choice([agreements, disagreements, additions, questions, reactions])
        return random.choice(response_type)
    
    def add_to_history(self, group_id: str, sender: str, message: str):
        """Добавить сообщение в историю"""
        if group_id not in self.conversation_history:
            self.conversation_history[group_id] = []
        
        self.conversation_history[group_id].append({
            "sender": sender,
            "message": message,
            "time": datetime.now().isoformat()
        })
        
        # Хранить последние 100 сообщений для лучшего контекста
        if len(self.conversation_history[group_id]) > 100:
            self.conversation_history[group_id] = self.conversation_history[group_id][-100:]
    
    def get_context(self, group_id: str) -> List[str]:
        """Получить контекст беседы (последние 20 сообщений)"""
        if group_id not in self.conversation_history:
            return []
        
        return [
            f"{msg['sender']}: {msg['message']}"
            for msg in self.conversation_history[group_id][-20:]
        ]
    
    def clear_history(self, group_id: str):
        """Очистить историю группы"""
        if group_id in self.conversation_history:
            del self.conversation_history[group_id]


# Глобальный экземпляр
chat_manager: Optional[OpenAIChatManager] = None


def get_chat_manager(api_key: str = None, provider: str = "groq") -> OpenAIChatManager:
    """
    Получить или создать менеджер чата.
    
    Args:
        api_key: API ключ
        provider: "groq" (бесплатный, рекомендуется) или "openai"
    """
    global chat_manager
    if chat_manager is None or (api_key and chat_manager.api_key != api_key):
        chat_manager = OpenAIChatManager(api_key, provider)
    return chat_manager


def reset_chat_manager():
    """Сбросить менеджер чата (для смены провайдера)"""
    global chat_manager
    chat_manager = None
