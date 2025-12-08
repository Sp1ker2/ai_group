"""
Device Generator - генерация уникальных устройств для Telegram аккаунтов
Каждый аккаунт получает уникальный fingerprint устройства
"""
import random
import hashlib
import json
from typing import Dict, Optional
from pathlib import Path
from dataclasses import dataclass, asdict


# База популярных Android устройств
ANDROID_DEVICES = [
    # Samsung
    {"brand": "Samsung", "model": "SM-G998B", "name": "Galaxy S21 Ultra", "sdk": "Android 13"},
    {"brand": "Samsung", "model": "SM-G991B", "name": "Galaxy S21", "sdk": "Android 13"},
    {"brand": "Samsung", "model": "SM-S908B", "name": "Galaxy S22 Ultra", "sdk": "Android 13"},
    {"brand": "Samsung", "model": "SM-S901B", "name": "Galaxy S22", "sdk": "Android 14"},
    {"brand": "Samsung", "model": "SM-S918B", "name": "Galaxy S23 Ultra", "sdk": "Android 14"},
    {"brand": "Samsung", "model": "SM-A536B", "name": "Galaxy A53", "sdk": "Android 13"},
    {"brand": "Samsung", "model": "SM-A546B", "name": "Galaxy A54", "sdk": "Android 14"},
    {"brand": "Samsung", "model": "SM-G780F", "name": "Galaxy S20 FE", "sdk": "Android 13"},
    {"brand": "Samsung", "model": "SM-N986B", "name": "Galaxy Note 20 Ultra", "sdk": "Android 13"},
    {"brand": "Samsung", "model": "SM-F936B", "name": "Galaxy Z Fold4", "sdk": "Android 14"},
    
    # Xiaomi
    {"brand": "Xiaomi", "model": "2201123G", "name": "Xiaomi 12", "sdk": "Android 13"},
    {"brand": "Xiaomi", "model": "2211133G", "name": "Xiaomi 13", "sdk": "Android 14"},
    {"brand": "Xiaomi", "model": "23049PCD8G", "name": "Xiaomi 13 Ultra", "sdk": "Android 14"},
    {"brand": "Xiaomi", "model": "22101316G", "name": "Redmi Note 12 Pro", "sdk": "Android 13"},
    {"brand": "Xiaomi", "model": "23021RAA2Y", "name": "Redmi Note 12", "sdk": "Android 13"},
    {"brand": "Xiaomi", "model": "2107113SG", "name": "Poco X3 GT", "sdk": "Android 12"},
    {"brand": "Xiaomi", "model": "22021211RG", "name": "Poco F4", "sdk": "Android 13"},
    {"brand": "Xiaomi", "model": "M2012K11AG", "name": "Redmi Note 9 Pro", "sdk": "Android 12"},
    
    # OnePlus
    {"brand": "OnePlus", "model": "LE2123", "name": "OnePlus 9 Pro", "sdk": "Android 13"},
    {"brand": "OnePlus", "model": "NE2213", "name": "OnePlus 10 Pro", "sdk": "Android 14"},
    {"brand": "OnePlus", "model": "CPH2449", "name": "OnePlus 11", "sdk": "Android 14"},
    {"brand": "OnePlus", "model": "AC2003", "name": "OnePlus Nord", "sdk": "Android 13"},
    {"brand": "OnePlus", "model": "CPH2387", "name": "OnePlus Nord CE 3", "sdk": "Android 13"},
    
    # Google Pixel
    {"brand": "Google", "model": "Pixel 6", "name": "Pixel 6", "sdk": "Android 14"},
    {"brand": "Google", "model": "Pixel 6 Pro", "name": "Pixel 6 Pro", "sdk": "Android 14"},
    {"brand": "Google", "model": "Pixel 7", "name": "Pixel 7", "sdk": "Android 14"},
    {"brand": "Google", "model": "Pixel 7 Pro", "name": "Pixel 7 Pro", "sdk": "Android 14"},
    {"brand": "Google", "model": "Pixel 8", "name": "Pixel 8", "sdk": "Android 14"},
    {"brand": "Google", "model": "Pixel 8 Pro", "name": "Pixel 8 Pro", "sdk": "Android 14"},
    
    # Huawei (без Google Services, но всё ещё используется)
    {"brand": "Huawei", "model": "ELS-NX9", "name": "P40 Pro", "sdk": "Android 12"},
    {"brand": "Huawei", "model": "NOH-NX9", "name": "Mate 40 Pro", "sdk": "Android 12"},
    {"brand": "Huawei", "model": "OCE-AN10", "name": "Mate 50 Pro", "sdk": "Android 13"},
    
    # Oppo
    {"brand": "Oppo", "model": "CPH2305", "name": "Find X5 Pro", "sdk": "Android 13"},
    {"brand": "Oppo", "model": "CPH2413", "name": "Reno 8 Pro", "sdk": "Android 13"},
    {"brand": "Oppo", "model": "CPH2525", "name": "Find X6 Pro", "sdk": "Android 14"},
    
    # Vivo
    {"brand": "Vivo", "model": "V2145", "name": "X70 Pro+", "sdk": "Android 13"},
    {"brand": "Vivo", "model": "V2219", "name": "X80 Pro", "sdk": "Android 13"},
    {"brand": "Vivo", "model": "V2324", "name": "X90 Pro", "sdk": "Android 14"},
    
    # Realme
    {"brand": "Realme", "model": "RMX3371", "name": "GT 2 Pro", "sdk": "Android 13"},
    {"brand": "Realme", "model": "RMX3563", "name": "10 Pro+", "sdk": "Android 13"},
    
    # Asus ROG
    {"brand": "Asus", "model": "ASUS_AI2201", "name": "ROG Phone 6", "sdk": "Android 13"},
    {"brand": "Asus", "model": "ASUS_AI2301", "name": "ROG Phone 7", "sdk": "Android 14"},
    
    # Motorola
    {"brand": "Motorola", "model": "XT2201-2", "name": "Edge 30 Pro", "sdk": "Android 13"},
    {"brand": "Motorola", "model": "XT2301-4", "name": "Edge 40 Pro", "sdk": "Android 14"},
    
    # Nothing
    {"brand": "Nothing", "model": "A063", "name": "Phone (1)", "sdk": "Android 14"},
    {"brand": "Nothing", "model": "A065", "name": "Phone (2)", "sdk": "Android 14"},
]

# Telegram версии
TELEGRAM_VERSIONS = [
    "10.6.1", "10.6.2", "10.7.0", "10.7.1", "10.8.0", "10.8.1",
    "10.9.0", "10.9.1", "10.9.2", "10.10.0", "10.10.1",
    "10.11.0", "10.11.1", "10.12.0", "10.12.1",
    "10.13.0", "10.13.1", "10.14.0", "10.14.1",
]

# Языки
LANGUAGES = [
    ("en", "en-US"), ("en", "en-GB"), ("ru", "ru-RU"),
    ("es", "es-ES"), ("es", "es-MX"), ("de", "de-DE"),
    ("fr", "fr-FR"), ("it", "it-IT"), ("pt", "pt-BR"),
    ("pl", "pl-PL"), ("uk", "uk-UA"), ("tr", "tr-TR"),
    ("ar", "ar-SA"), ("ja", "ja-JP"), ("ko", "ko-KR"),
    ("zh", "zh-CN"), ("id", "id-ID"), ("vi", "vi-VN"),
    ("th", "th-TH"), ("hi", "hi-IN"),
]


@dataclass
class DeviceInfo:
    """Информация об устройстве для Telegram"""
    device_model: str      # Модель устройства (SM-G998B)
    system_version: str    # Версия ОС (Android 13)
    app_version: str       # Версия Telegram (10.6.1)
    lang_code: str         # Код языка (en)
    system_lang_code: str  # Системный язык (en-US)
    
    # Дополнительно для session.json
    brand: str             # Бренд (Samsung)
    device_name: str       # Название (Galaxy S21 Ultra)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DeviceInfo':
        return cls(**data)
    
    def to_telethon_params(self) -> dict:
        """Параметры для TelegramClient"""
        return {
            "device_model": self.device_model,
            "system_version": self.system_version,
            "app_version": self.app_version,
            "lang_code": self.lang_code,
            "system_lang_code": self.system_lang_code,
        }


class DeviceGenerator:
    """Генератор уникальных устройств для аккаунтов"""
    
    def __init__(self, storage_path: str = "local-storage"):
        self.storage_path = Path(storage_path)
        self.devices_file = self.storage_path / "device_assignments.json"
        self.assignments: Dict[str, DeviceInfo] = {}
        self.used_combinations = set()  # Использованные комбинации
        
        self._load_assignments()
    
    def _load_assignments(self):
        """Загрузить назначения устройств"""
        if self.devices_file.exists():
            try:
                with open(self.devices_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for phone, device_data in data.items():
                        self.assignments[phone] = DeviceInfo.from_dict(device_data)
                        # Добавляем в использованные
                        combo = f"{device_data['device_model']}_{device_data['app_version']}"
                        self.used_combinations.add(combo)
            except Exception as e:
                print(f"[Device] Ошибка загрузки: {e}")
    
    def _save_assignments(self):
        """Сохранить назначения"""
        try:
            data = {phone: device.to_dict() for phone, device in self.assignments.items()}
            with open(self.devices_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Device] Ошибка сохранения: {e}")
    
    def generate_unique_device(self, phone: str = None, seed: str = None) -> DeviceInfo:
        """
        Сгенерировать уникальное устройство.
        Если передан phone - устройство будет детерминированным для этого номера.
        """
        # Если для этого номера уже есть устройство - вернуть его
        if phone and phone in self.assignments:
            return self.assignments[phone]
        
        # Генерация с seed для воспроизводимости
        if seed or phone:
            rng = random.Random(seed or phone)
        else:
            rng = random
        
        # Выбираем уникальную комбинацию
        max_attempts = 100
        for _ in range(max_attempts):
            device = rng.choice(ANDROID_DEVICES)
            app_version = rng.choice(TELEGRAM_VERSIONS)
            
            combo = f"{device['model']}_{app_version}"
            if combo not in self.used_combinations:
                self.used_combinations.add(combo)
                break
        
        # Выбираем язык
        lang_code, system_lang_code = rng.choice(LANGUAGES)
        
        device_info = DeviceInfo(
            device_model=device["model"],
            system_version=device["sdk"],
            app_version=app_version,
            lang_code=lang_code,
            system_lang_code=system_lang_code,
            brand=device["brand"],
            device_name=device["name"]
        )
        
        # Если указан phone - сохраняем привязку
        if phone:
            self.assignments[phone] = device_info
            self._save_assignments()
        
        return device_info
    
    def get_device_for_phone(self, phone: str) -> Optional[DeviceInfo]:
        """Получить устройство для номера (или сгенерировать новое)"""
        if phone in self.assignments:
            return self.assignments[phone]
        return self.generate_unique_device(phone)
    
    def update_session_json(self, phone: str, session_dir: Path = None) -> bool:
        """
        Обновить session.json файл устройством.
        """
        if session_dir is None:
            session_dir = self.storage_path / "sessions" / phone
        
        session_file = session_dir / f"{phone}.json"
        
        if not session_file.exists():
            print(f"[Device] Session файл не найден: {session_file}")
            return False
        
        device_info = self.get_device_for_phone(phone)
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # Обновляем device info
            session_data["device"] = device_info.device_name
            session_data["sdk"] = device_info.system_version
            session_data["app_version"] = device_info.app_version
            session_data["lang_pack"] = device_info.lang_code
            session_data["system_lang_pack"] = device_info.system_lang_code
            
            # Сохраняем дополнительно
            session_data["device_model"] = device_info.device_model
            session_data["device_brand"] = device_info.brand
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            print(f"[Device] {phone} -> {device_info.brand} {device_info.device_name}")
            return True
            
        except Exception as e:
            print(f"[Device] Ошибка обновления {phone}: {e}")
            return False
    
    def generate_for_all_sessions(self, sessions_dir: Path = None) -> Dict[str, DeviceInfo]:
        """Сгенерировать устройства для всех сессий"""
        if sessions_dir is None:
            sessions_dir = self.storage_path / "sessions"
        
        if not sessions_dir.exists():
            return {}
        
        generated = {}
        
        for phone_dir in sessions_dir.iterdir():
            if not phone_dir.is_dir():
                continue
            
            phone = phone_dir.name
            if not phone.isdigit():
                continue
            
            device = self.get_device_for_phone(phone)
            self.update_session_json(phone, phone_dir)
            generated[phone] = device
        
        return generated
    
    def get_status(self) -> Dict:
        """Получить статус устройств"""
        brands_count = {}
        for device in self.assignments.values():
            brands_count[device.brand] = brands_count.get(device.brand, 0) + 1
        
        return {
            "total_assigned": len(self.assignments),
            "unique_combinations": len(self.used_combinations),
            "available_devices": len(ANDROID_DEVICES),
            "available_versions": len(TELEGRAM_VERSIONS),
            "brands_distribution": brands_count,
            "devices": {phone: device.to_dict() for phone, device in self.assignments.items()}
        }
    
    def clear_assignments(self):
        """Очистить все назначения"""
        self.assignments = {}
        self.used_combinations = set()
        if self.devices_file.exists():
            self.devices_file.unlink()


# Глобальный экземпляр
device_generator: Optional[DeviceGenerator] = None


def get_device_generator(storage_path: str = "local-storage") -> DeviceGenerator:
    """Получить или создать генератор устройств"""
    global device_generator
    if device_generator is None:
        device_generator = DeviceGenerator(storage_path)
    return device_generator

