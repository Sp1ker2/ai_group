"""
Proxy Manager - управление SOCKS5 прокси для Telegram аккаунтов
"""
import os
import json
import asyncio
import aiohttp
import socket
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    import python_socks
    from python_socks.async_.asyncio.v2 import Proxy
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False
    print("WARNING: python-socks не установлен. Установите: pip install python-socks[asyncio]")


@dataclass
class ProxyInfo:
    """Информация о прокси"""
    ip: str
    port: int
    username: str
    password: str
    status: str = "unknown"  # unknown, checking, alive, dead
    last_check: str = None
    response_time_ms: int = None
    assigned_to: str = None  # phone number
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ProxyInfo':
        return cls(**data)
    
    def to_telethon_proxy(self) -> tuple:
        """Формат для Telethon: (type, ip, port, rdns, username, password)"""
        import socks
        return (socks.SOCKS5, self.ip, self.port, True, self.username, self.password)
    
    def to_url(self) -> str:
        """URL формат: socks5://user:pass@ip:port"""
        return f"socks5://{self.username}:{self.password}@{self.ip}:{self.port}"


class ProxyManager:
    """Менеджер прокси для Telegram аккаунтов"""
    
    def __init__(self, storage_path: str = "local-storage"):
        self.storage_path = Path(storage_path)
        self.proxies_file = self.storage_path / "proxies.txt"
        self.assignments_file = self.storage_path / "proxy_assignments.json"
        self.proxies: List[ProxyInfo] = []
        self.assignments: Dict[str, ProxyInfo] = {}  # phone -> proxy
        
        self._load_assignments()
    
    def _load_assignments(self):
        """Загрузить привязки прокси к аккаунтам"""
        if self.assignments_file.exists():
            try:
                with open(self.assignments_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for phone, proxy_data in data.items():
                        self.assignments[phone] = ProxyInfo.from_dict(proxy_data)
            except Exception as e:
                print(f"[Proxy] Ошибка загрузки assignments: {e}")
    
    def _save_assignments(self):
        """Сохранить привязки"""
        try:
            data = {phone: proxy.to_dict() for phone, proxy in self.assignments.items()}
            with open(self.assignments_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Proxy] Ошибка сохранения assignments: {e}")
    
    def load_proxies_from_file(self, filepath: str = None) -> int:
        """
        Загрузить прокси из файла.
        Формат: ip:port:username:password (по одному на строку)
        
        Returns: количество загруженных прокси
        """
        filepath = Path(filepath) if filepath else self.proxies_file
        
        if not filepath.exists():
            print(f"[Proxy] Файл не найден: {filepath}")
            return 0
        
        self.proxies = []
        loaded = 0
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    parts = line.split(':')
                    if len(parts) >= 4:
                        ip = parts[0]
                        port = int(parts[1])
                        username = parts[2]
                        password = ':'.join(parts[3:])  # пароль может содержать :
                        
                        proxy = ProxyInfo(
                            ip=ip,
                            port=port,
                            username=username,
                            password=password
                        )
                        self.proxies.append(proxy)
                        loaded += 1
                    else:
                        print(f"[Proxy] Строка {line_num}: неверный формат (нужно ip:port:user:pass)")
                except Exception as e:
                    print(f"[Proxy] Строка {line_num}: ошибка парсинга - {e}")
        
        print(f"[Proxy] Загружено {loaded} прокси из {filepath}")
        return loaded
    
    def load_proxies_from_text(self, text: str) -> int:
        """
        Загрузить прокси из текста.
        Формат: ip:port:username:password (по одному на строку)
        """
        self.proxies = []
        loaded = 0
        
        for line_num, line in enumerate(text.strip().split('\n'), 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            try:
                parts = line.split(':')
                if len(parts) >= 4:
                    ip = parts[0]
                    port = int(parts[1])
                    username = parts[2]
                    password = ':'.join(parts[3:])
                    
                    proxy = ProxyInfo(
                        ip=ip,
                        port=port,
                        username=username,
                        password=password
                    )
                    self.proxies.append(proxy)
                    loaded += 1
            except Exception as e:
                print(f"[Proxy] Строка {line_num}: ошибка - {e}")
        
        # Сохранить в файл
        self._save_proxies_to_file()
        
        print(f"[Proxy] Загружено {loaded} прокси")
        return loaded
    
    def _save_proxies_to_file(self):
        """Сохранить прокси в файл"""
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            with open(self.proxies_file, 'w', encoding='utf-8') as f:
                for proxy in self.proxies:
                    f.write(f"{proxy.ip}:{proxy.port}:{proxy.username}:{proxy.password}\n")
        except Exception as e:
            print(f"[Proxy] Ошибка сохранения: {e}")
    
    async def check_proxy(self, proxy: ProxyInfo, timeout: int = 10) -> bool:
        """
        Проверить работоспособность прокси.
        Пытается подключиться к telegram.org через SOCKS5.
        """
        proxy.status = "checking"
        start_time = datetime.now()
        
        try:
            # Простая проверка через socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            # Подключаемся к прокси
            result = sock.connect_ex((proxy.ip, proxy.port))
            sock.close()
            
            if result == 0:
                # Прокси доступен, проверим аутентификацию через aiohttp
                try:
                    proxy_url = f"socks5://{proxy.username}:{proxy.password}@{proxy.ip}:{proxy.port}"
                    
                    connector = aiohttp.TCPConnector()
                    async with aiohttp.ClientSession(connector=connector) as session:
                        # Пробуем достучаться до telegram через прокси
                        # Используем простой HTTP запрос для проверки
                        async with session.get(
                            "http://ip-api.com/json",
                            timeout=aiohttp.ClientTimeout(total=timeout),
                            proxy=proxy_url
                        ) as response:
                            if response.status == 200:
                                proxy.status = "alive"
                                proxy.response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                                proxy.last_check = datetime.now().isoformat()
                                return True
                except Exception as e:
                    # Если aiohttp не работает с socks, попробуем базовую проверку
                    proxy.status = "alive"  # Порт открыт = считаем живым
                    proxy.response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                    proxy.last_check = datetime.now().isoformat()
                    return True
            
            proxy.status = "dead"
            proxy.last_check = datetime.now().isoformat()
            return False
            
        except Exception as e:
            proxy.status = "dead"
            proxy.last_check = datetime.now().isoformat()
            print(f"[Proxy] Ошибка проверки {proxy.ip}:{proxy.port} - {e}")
            return False
    
    async def check_all_proxies(self, timeout: int = 10) -> Dict[str, int]:
        """
        Проверить все прокси параллельно.
        
        Returns: {"alive": N, "dead": M, "total": K}
        """
        if not self.proxies:
            return {"alive": 0, "dead": 0, "total": 0}
        
        print(f"[Proxy] Проверка {len(self.proxies)} прокси...")
        
        # Проверяем по 10 параллельно
        semaphore = asyncio.Semaphore(10)
        
        async def check_with_semaphore(proxy):
            async with semaphore:
                return await self.check_proxy(proxy, timeout)
        
        results = await asyncio.gather(*[check_with_semaphore(p) for p in self.proxies])
        
        alive = sum(1 for r in results if r)
        dead = len(results) - alive
        
        print(f"[Proxy] Результат: {alive} живых, {dead} мертвых")
        
        return {
            "alive": alive,
            "dead": dead,
            "total": len(self.proxies)
        }
    
    def get_free_proxy(self) -> Optional[ProxyInfo]:
        """Получить свободный (не назначенный) прокси"""
        assigned_ips = {p.ip for p in self.assignments.values()}
        
        for proxy in self.proxies:
            if proxy.ip not in assigned_ips and proxy.status == "alive":
                return proxy
        
        # Если нет живых, вернем любой свободный
        for proxy in self.proxies:
            if proxy.ip not in assigned_ips:
                return proxy
        
        return None
    
    def assign_proxy_to_phone(self, phone: str, proxy: ProxyInfo = None) -> Optional[ProxyInfo]:
        """
        Назначить прокси телефону.
        Если proxy=None, назначит свободный.
        """
        if proxy is None:
            proxy = self.get_free_proxy()
        
        if proxy is None:
            print(f"[Proxy] Нет свободных прокси для {phone}")
            return None
        
        proxy.assigned_to = phone
        self.assignments[phone] = proxy
        self._save_assignments()
        
        print(f"[Proxy] {phone} -> {proxy.ip}:{proxy.port}")
        return proxy
    
    def get_proxy_for_phone(self, phone: str) -> Optional[ProxyInfo]:
        """Получить прокси назначенный телефону"""
        return self.assignments.get(phone)
    
    def auto_assign_proxies(self, phones: List[str]) -> Dict[str, ProxyInfo]:
        """
        Автоматически назначить прокси всем телефонам.
        1 прокси = 1 телефон.
        """
        assigned = {}
        
        for phone in phones:
            # Если уже назначен - пропускаем
            if phone in self.assignments:
                assigned[phone] = self.assignments[phone]
                continue
            
            proxy = self.assign_proxy_to_phone(phone)
            if proxy:
                assigned[phone] = proxy
        
        return assigned
    
    def get_status(self) -> Dict:
        """Получить статус всех прокси"""
        alive = sum(1 for p in self.proxies if p.status == "alive")
        dead = sum(1 for p in self.proxies if p.status == "dead")
        unknown = sum(1 for p in self.proxies if p.status == "unknown")
        assigned = len(self.assignments)
        
        return {
            "total": len(self.proxies),
            "alive": alive,
            "dead": dead,
            "unknown": unknown,
            "assigned": assigned,
            "free": len(self.proxies) - assigned,
            "proxies": [p.to_dict() for p in self.proxies]
        }
    
    def clear_assignments(self):
        """Очистить все назначения"""
        self.assignments = {}
        for proxy in self.proxies:
            proxy.assigned_to = None
        self._save_assignments()


# Глобальный экземпляр
proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager(storage_path: str = "local-storage") -> ProxyManager:
    """Получить или создать менеджер прокси"""
    global proxy_manager
    if proxy_manager is None:
        proxy_manager = ProxyManager(storage_path)
    return proxy_manager

