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

# Конфигурация провайдеров AI
AI_PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-8b-instant",  # Быстрая бесплатная модель
        "name": "Groq (FREE)"
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-3.5-turbo",
        "name": "OpenAI"
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
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
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
    
    def set_topics_file(self, filepath: str):
        """Установить файл тем"""
        self.topic_manager = TopicManager(filepath)
    
    def assign_personality(self, member_index: int) -> dict:
        """Назначить личность участнику"""
        return PERSONALITIES[member_index % len(PERSONALITIES)]
    
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
        
        system_prompt = f"""Ты РЕАЛЬНЫЙ человек в групповом чате Telegram. НЕ бот!
Имя: {sender_name}
Личность: {sender_personality['name']}
Стиль: {sender_personality['style']}

ТЕМА: {topic_name}
{topic_desc}

ИСТОРИЯ ЧАТА:
{last_messages}

КАК ПИСАТЬ (ОЧЕНЬ ВАЖНО):
1. Пиши КАК ЖИВОЙ ЧЕЛОВЕК - с опечатками, пропущенными буквами, без всех знаков препинания
2. Иногда забывай запятые и точки, пиши "чо" вместо "что", "щас" вместо "сейчас", "норм" вместо "нормально"
3. Можешь начать предложение с маленькой буквы
4. Иногда делай опечатки типа "привте", "кагда", "тоэе"
5. Пиши развёрнуто! 2-5 предложений. Делись историями, опытом, мнениями
6. ОТВЕЧАЙ на то что написали до тебя, продолжай мысль
7. Если тема исчерпана - плавно переходи к смежной теме
8. Не будь слишком вежливым, пиши неформально как с друзьями
9. Эмодзи иногда: {', '.join(sender_personality.get('emoji', ['👍'])[:2])}

ПРИМЕРЫ СООБЩЕНИЙ:
- "да блин я тоже так думаю, помню когда первый раз попробовал вообще не понял прикола а щас прям топ"
- "ну хз я бы не согласился тут, мне кажется это слишком уж... хотя может и да"  
- "о кстати вспомнил историю, у меня друг тоже так делал и потом такой типа нифига себе работает"
- "а вы пробовали вот это? я недавно наткнулся прям огонь"

ЗАПРЕЩЕНО:
- Писать идеально грамотно
- Ставить все знаки препинания
- Повторять вопросы из истории
- Быть роботом
"""

        messages = [{"role": "system", "content": system_prompt}]
        
        if is_first_message:
            starter = self.topic_manager.get_random_prompt(topic.get("id", "travel")) if topic else "Привет!"
            messages.append({"role": "user", "content": f"Начни беседу на тему '{topic_name}'. Напиши что-то интересное, расскажи историю или поделись мнением. Пиши развёрнуто, 2-4 предложения. С опечатками!"})
        else:
            # Анализ последнего сообщения - отвечаем на него
            last_msg = context[-1] if context else ""
            msg_count = len(context)
            
            if "?" in last_msg:
                messages.append({"role": "user", "content": f"Кто-то спросил: '{last_msg}'\n\nОТВЕТЬ развёрнуто! Расскажи свой опыт, историю из жизни, мнение. 2-4 предложения. Пиши как живой человек с опечатками!"})
            elif msg_count > 15 and random.random() > 0.7:
                # Тема исчерпана - переход к новой
                messages.append({"role": "user", "content": f"Тема '{topic_name}' уже обсуждена. Плавно перейди к смежной теме или расскажи что-то новое связанное с этим. Типа 'кстати а вы знали что...' или 'о это напомнило мне...' Пиши с опечатками!"})
            else:
                messages.append({"role": "user", "content": f"Продолжи разговор по теме '{topic_name}'. Последнее сообщение: '{last_msg}'\n\nОтреагируй на него, добавь свои мысли, расскажи историю. 2-4 предложения с опечатками и без всех запятых!"})
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=250,  # Длинные развёрнутые сообщения
                temperature=0.9  # Больше креатива и случайности
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[AI] Error ({self.provider}): {e}")
            return self._generate_fallback_message(sender_personality, topic, is_first_message)
    
    def _generate_fallback_message(self, personality: dict, topic: dict = None, is_first: bool = False) -> str:
        """Fallback сообщения если AI не работает - как реальный человек"""
        
        emoji = random.choice(personality.get("emoji", ["👍"]))
        
        if topic:
            prompts = topic.get("prompts", [])
            if prompts:
                return f"{random.choice(prompts)} {emoji}"
        
        greetings = [
            f"прив всем! {emoji} чо как дела у вас",
            f"здаров народ)) давно тут не был",
            f"о привте {emoji} что нового расказывайте",
            f"хай! ну что тут интересного пропустил",
            f"всем прив, как выходные прошли {emoji}",
        ]
        
        responses = [
            f"да блин это прям в точку, я тоже так думаю {emoji}",
            f"ну хз спорный момент конечно но в целом соглашусь",
            f"о это напомнило мне одну историю кстати {emoji}",
            f"а я вот недавно пробовал и скажу что норм вполне",
            f"согласен на все сто {emoji} сам такое проходил",
            f"ммм ну такое честно говоря, но может я не понял",
            f"кстати а вы знали что это работает и по другому тоже {emoji}",
            f"да точно! я тоже сначала не верил а потом прям вау",
            f"не ну а чо, норм же вроде все {emoji}",
            f"о я про это могу много расказать если интересно",
        ]
        
        if is_first:
            return random.choice(greetings)
        
        return random.choice(responses)
    
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
