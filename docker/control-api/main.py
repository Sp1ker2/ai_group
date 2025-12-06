"""
Control API с веб-интерфейсом для управления Telegram Farm
"""
# Увеличить таймаут SQLite для избежания "database is locked"
import sqlite3
original_connect = sqlite3.connect
def patched_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 30.0)  # 30 секунд таймаут
    return original_connect(*args, **kwargs)
sqlite3.connect = patched_connect

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import json
import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime

app = FastAPI(title="Telegram Farm Control API", version="1.0.0")

# Настройка шаблонов и статических файлов
BASE_DIR = Path(__file__).parent
templates_dir = BASE_DIR / "templates"
static_dir = BASE_DIR / "static"

# Создать папки если их нет
templates_dir.mkdir(parents=True, exist_ok=True)
static_dir.mkdir(parents=True, exist_ok=True)
(static_dir / "css").mkdir(parents=True, exist_ok=True)
(static_dir / "js").mkdir(parents=True, exist_ok=True)

try:
    templates = Jinja2Templates(directory=str(templates_dir))
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
except Exception as e:
    print(f"Warning: Templates/Static files not available: {e}")
    templates = None

# Пути к данным (относительно корня проекта)
# В Docker: /app/../local-storage (монтируется через volume)
# Локально: ./local-storage
if Path("/app").exists():
    BASE_PROJECT_DIR = Path("/app").parent
else:
    BASE_PROJECT_DIR = Path(__file__).parent.parent.parent

SESSIONS_DIR = BASE_PROJECT_DIR / "local-storage" / "sessions"
PHONES_DIR = BASE_PROJECT_DIR / "local-storage" / "phones"
GROUPS_FILE = BASE_PROJECT_DIR / "local-storage" / "groups.json"
TOPICS_FILE = BASE_PROJECT_DIR / "local-storage" / "topics.json"

# Создать директории если их нет
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
PHONES_DIR.mkdir(parents=True, exist_ok=True)
GROUPS_FILE.parent.mkdir(parents=True, exist_ok=True)


class JobRequest(BaseModel):
    phone_number: str
    account_id: str
    script_id: str = "warmup_script_v1"
    enable_group_chat: bool = False
    group_id: Optional[str] = None


class GroupRequest(BaseModel):
    title: str
    admin_phone: str
    member_phones: List[str] = []


# ========== API Endpoints ==========

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Главная страница"""
    if templates:
        try:
            return templates.TemplateResponse("index.html", {"request": request})
        except:
            pass
    # Fallback если шаблоны не загружены
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head><title>Telegram Farm</title></head>
    <body style="font-family: Arial; padding: 20px;">
        <h1>🤖 Telegram Farm Control API</h1>
        <p>API работает! Но шаблоны не загружены.</p>
        <p><a href="/api/v1/status">Status</a> | <a href="/api/v1/sessions">Sessions API</a></p>
    </body>
    </html>
    """)


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/ready")
async def ready():
    return {"status": "ready"}


@app.get("/api/v1/status")
async def api_status():
    """Статус системы"""
    # Рекурсивный поиск всех .json файлов в подпапках
    sessions_count = 0
    if SESSIONS_DIR.exists():
        sessions_count = len(list(SESSIONS_DIR.rglob("*.json")))
    
    groups_count = 0
    if GROUPS_FILE.exists():
        try:
            groups_data = json.loads(GROUPS_FILE.read_text())
            if isinstance(groups_data, list):
                groups_count = len(groups_data)
            elif isinstance(groups_data, dict):
                groups_count = len(groups_data.get('groups', []))
        except json.JSONDecodeError as e:
            print(f"WARNING: Ошибка парсинга groups.json: {e}")
        except Exception as e:
            print(f"WARNING: Ошибка чтения groups.json: {e}")
    
    return {
        "api": "running",
        "database": "connected" if os.getenv("DATABASE_URL") else "not configured",
        "redis": "connected" if os.getenv("REDIS_URL") else "not configured",
        "sessions_count": sessions_count,
        "groups_count": groups_count
    }


@app.get("/api/v1/sessions", response_class=JSONResponse)
async def get_sessions():
    """Получить список всех сессий (включая подпапки)"""
    if not SESSIONS_DIR.exists():
        return {"sessions": []}
    
    sessions = []
    # Рекурсивный поиск всех .json файлов в подпапках
    for json_file in SESSIONS_DIR.rglob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as je:
                    # Если JSON невалидный, пропускаем файл
                    print(f"WARNING: Невалидный JSON в {json_file}: {je}")
                    continue
                
                # Поддержка разных форматов session файлов
                # Формат 1: Telethon (phone_number, account_id, session_string)
                phone = data.get('phone_number') or data.get('phone')
                account_id = data.get('account_id') or data.get('id')
                
                # Если нет phone в данных, используем имя папки или файла
                if not phone:
                    folder_name = json_file.parent.name if json_file.parent != SESSIONS_DIR else json_file.stem
                    phone = folder_name if folder_name.isdigit() else json_file.stem
                
                # Если нет account_id, используем phone
                if not account_id:
                    account_id = phone
                
                # Путь относительно SESSIONS_DIR
                relative_path = json_file.relative_to(SESSIONS_DIR)
                
                # Проверить наличие session_string или .session файла
                has_session_string = bool(data.get('session_string'))
                session_file = json_file.parent / f"{json_file.stem}.session"
                has_session_file = session_file.exists()
                
                sessions.append({
                    'phone': str(phone),
                    'filename': json_file.name,
                    'path': str(relative_path),
                    'full_path': str(json_file),
                    'has_session': has_session_string or has_session_file,
                    'has_session_string': has_session_string,
                    'has_session_file': has_session_file,
                    'created_at': data.get('created_at') or data.get('session_created_date') or data.get('last_connect_date') or 'unknown',
                    'account_id': str(account_id),
                    'first_name': data.get('first_name'),
                    'username': data.get('username'),
                    'twoFA': data.get('twoFA') or data.get('2fa') or data.get('password')
                })
        except Exception as e:
            # Если ошибка чтения файла, попробуем по имени файла/папки
            try:
                folder_name = json_file.parent.name if json_file.parent != SESSIONS_DIR else json_file.stem
                phone = folder_name if folder_name.isdigit() else json_file.stem
                relative_path = json_file.relative_to(SESSIONS_DIR)
                
                # Проверить наличие .session файла
                session_file = json_file.parent / f"{json_file.stem}.session"
                has_session_file = session_file.exists()
                
                sessions.append({
                    'phone': phone,
                    'filename': json_file.name,
                    'path': str(relative_path),
                    'full_path': str(json_file),
                    'has_session': has_session_file,
                    'has_session_string': False,
                    'has_session_file': has_session_file,
                    'created_at': 'unknown',
                    'account_id': phone
                })
            except Exception as e2:
                print(f"WARNING: Ошибка обработки {json_file}: {e2}")
                continue
    
    return {"sessions": sessions, "total": len(sessions)}


@app.get("/api/v1/groups", response_class=JSONResponse)
async def get_groups():
    """Получить список групп"""
    if not GROUPS_FILE.exists():
        return {"groups": []}
    
    try:
        with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
            try:
                groups = json.load(f)
                # Поддержка разных форматов
                if isinstance(groups, dict):
                    groups = groups.get('groups', [])
                if not isinstance(groups, list):
                    groups = []
                return {"groups": groups, "total": len(groups)}
            except json.JSONDecodeError as e:
                print(f"WARNING: Ошибка парсинга groups.json: {e}")
                return {"groups": [], "total": 0, "error": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        print(f"⚠️ Ошибка чтения groups.json: {e}")
        return {"groups": [], "total": 0, "error": str(e)}


@app.delete("/api/v1/groups/all", response_class=JSONResponse)
async def delete_all_groups():
    """Удалить все группы"""
    try:
        if GROUPS_FILE.exists():
            # Сохранить пустой файл
            with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
                json.dump({"groups": [], "schedule": {"enabled": False, "interval_minutes": 60}}, f, indent=2)
            return {"status": "success", "message": "Все группы удалены"}
        return {"status": "success", "message": "Файл групп не существует"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/groups/create", response_class=JSONResponse)
async def create_group(group: GroupRequest):
    """Создать группу"""
    try:
        # Импорт функции создания группы
        import sys
        import importlib.util
        
        script_path = BASE_PROJECT_DIR / "scripts" / "create-group-chat.py"
        if not script_path.exists():
            raise HTTPException(status_code=500, detail="Script not found")
        
        spec = importlib.util.spec_from_file_location("create_group_chat", str(script_path))
        create_group_chat = importlib.util.module_from_spec(spec)
        sys.modules["create_group_chat"] = create_group_chat
        spec.loader.exec_module(create_group_chat)
        
        result = await create_group_chat.create_group_with_members(
            group.title,
            group.admin_phone,
            group.member_phones
        )
        
        if result:
            # Сохранить в groups.json
            groups_data = []
            if GROUPS_FILE.exists():
                with open(GROUPS_FILE, 'r') as f:
                    groups_data = json.load(f)
            
            groups_data.append(result)
            GROUPS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(GROUPS_FILE, 'w') as f:
                json.dump(groups_data, f, indent=2)
        
        return {"status": "success", "group": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/jobs/report")
async def report_job(job_data: dict):
    """Эндпоинт для получения отчетов от worker'ов"""
    return {"status": "received", "job_id": job_data.get("account_id")}


@app.post("/api/v1/jobs/create", response_class=JSONResponse)
async def create_job(job: JobRequest):
    """Создать задачу warm-up"""
    # Проверить наличие сессии (искать в подпапках тоже)
    phone_clean = job.phone_number.replace('+', '').replace('-', '').replace(' ', '')
    
    # Сначала попробовать прямой путь
    session_file = SESSIONS_DIR / f"{phone_clean}.json"
    
    # Если нет, искать в подпапках
    if not session_file.exists():
        found = False
        for json_file in SESSIONS_DIR.rglob(f"{phone_clean}.json"):
            session_file = json_file
            found = True
            break
        
        # Также попробовать найти по папке с таким именем
        if not found:
            folder_path = SESSIONS_DIR / phone_clean
            if folder_path.exists() and folder_path.is_dir():
                session_file = folder_path / f"{phone_clean}.json"
                if session_file.exists():
                    found = True
        
        if not found:
            raise HTTPException(status_code=404, detail=f"Session not found for {job.phone_number}")
    
    # Здесь можно добавить логику создания Job в Kubernetes
    # Пока возвращаем успех
    return {
        "status": "created",
        "job_id": job.account_id,
        "phone": job.phone_number,
        "script_id": job.script_id
    }


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard страница"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/sessions", response_class=HTMLResponse)
async def sessions_page(request: Request):
    """Страница управления сессиями"""
    return templates.TemplateResponse("sessions.html", {"request": request})


@app.get("/groups", response_class=HTMLResponse)
async def groups_page(request: Request):
    """Страница управления группами"""
    return templates.TemplateResponse("groups.html", {"request": request})


@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request):
    """Страница управления задачами"""
    return templates.TemplateResponse("jobs.html", {"request": request})


class GetCodeRequest(BaseModel):
    phone_number: str


class VerifyCodeRequest(BaseModel):
    phone_number: str
    phone_code_hash: Optional[str] = None  # Опционально, если используется verify-code-direct
    code: str
    password: Optional[str] = None


class VerifyCodeDirectRequest(BaseModel):
    """Для кода, запрошенного через обычный Telegram (без phone_code_hash)"""
    phone_number: str
    code: str
    password: Optional[str] = None


# Хранилище для ожидающих кодов (в реальном приложении использовать Redis)
pending_codes = {}
received_codes = {}  # Коды полученные автоматически

async def check_existing_session(phone_number: str, api_id: str, api_hash: str):
    """Проверить и использовать существующий session файл"""
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        
        phone_filename = phone_number.replace('+', '').replace('-', '').replace(' ', '')
        
        # 1. Проверить .json файл в подпапке
        session_json = SESSIONS_DIR / phone_filename / f"{phone_filename}.json"
        if session_json.exists():
            with open(session_json, 'r', encoding='utf-8') as f:
                try:
                    session_data = json.load(f)
                    session_string = session_data.get('session_string')
                    if session_string:
                        # Использовать api_id/api_hash из файла или из параметров
                        file_api_id = session_data.get('api_id') or api_id
                        file_api_hash = session_data.get('api_hash') or api_hash
                        
                        client = TelegramClient(
                            StringSession(session_string),
                            int(file_api_id),
                            file_api_hash
                        )
                        try:
                            await client.connect()
                            if await client.is_user_authorized():
                                me = await client.get_me()
                                await client.disconnect()
                                return {
                                    "status": "session_exists",
                                    "phone_number": phone_number,
                                    "account_id": str(me.id),
                                    "message": "Найден существующий session. Аккаунт уже авторизован.",
                                    "session_file": str(session_json)
                                }
                        finally:
                            await client.disconnect()
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    print(f"WARNING: Ошибка проверки session: {e}")
        
        # 2. Проверить .session файл в подпапке
        session_file = SESSIONS_DIR / phone_filename / f"{phone_filename}.session"
        if session_file.exists():
            try:
                client = TelegramClient(
                    str(session_file),
                    int(api_id),
                    api_hash
                )
                try:
                    await client.connect()
                    if await client.is_user_authorized():
                        me = await client.get_me()
                        await client.disconnect()
                        return {
                            "status": "session_exists",
                            "phone_number": phone_number,
                            "account_id": str(me.id),
                            "message": "Найден существующий .session файл. Аккаунт уже авторизован.",
                            "session_file": str(session_file)
                        }
                finally:
                    await client.disconnect()
            except Exception as e:
                print(f"WARNING: Ошибка проверки .session файла: {e}")
        
        return None
    except Exception as e:
        print(f"WARNING: Ошибка проверки существующего session: {e}")
        return None


@app.post("/api/v1/sessions/get-code", response_class=JSONResponse)
async def get_code(request: GetCodeRequest):
    """
    Получить phone_code_hash для верификации кода
    СНАЧАЛА проверяет существующие session файлы - если они есть, использует их без запроса кода
    """
    try:
        # Получить API credentials из .env или переменных окружения
        api_id = os.getenv('TELEGRAM_API_ID')
        api_hash = os.getenv('TELEGRAM_API_HASH')
        
        # Попробовать загрузить из .env файла
        if not api_id or not api_hash:
            env_file = BASE_PROJECT_DIR / ".env"
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            if key.strip() == 'TELEGRAM_API_ID':
                                api_id = value.strip()
                            elif key.strip() == 'TELEGRAM_API_HASH':
                                api_hash = value.strip()
        
        # Если все еще нет - попробовать найти в существующих сессиях
        if not api_id or not api_hash:
            for json_file in SESSIONS_DIR.rglob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                        if 'app_id' in session_data and 'app_hash' in session_data:
                            api_id = str(session_data['app_id'])
                            api_hash = session_data['app_hash']
                            print(f"Используются API credentials из сессии: {json_file}")
                            break
                except:
                    continue
        
        if not api_id or not api_hash:
            raise HTTPException(
                status_code=400, 
                detail="TELEGRAM_API_ID и TELEGRAM_API_HASH не установлены. Добавьте в .env файл или используйте сессию с app_id/app_hash"
            )
        
        # НЕ проверяем существующий session - всегда запрашиваем код если пользователь явно нажал "Запросить код"
        # Это позволяет переавторизоваться или получить код для уже авторизованного номера
        
        # Запросить код через Telegram API - код придет в Telegram на этот номер
        print(f"Запрос кода для {request.phone_number} через Telegram API...")
        
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
            
            temp_session = StringSession()
            temp_client = TelegramClient(temp_session, int(api_id), api_hash)
            try:
                await temp_client.connect()
                print(f"Отправка кода на {request.phone_number} через Telegram...")
                result = await temp_client.send_code_request(request.phone_number)
                phone_code_hash = result.phone_code_hash
                print(f"Код успешно отправлен на {request.phone_number}! phone_code_hash получен.")
                
                # Сохранить для последующей верификации
                pending_codes[request.phone_number] = {
                    "phone_code_hash": phone_code_hash,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Запустить мониторинг для автоматического получения кода и авторизации
                try:
                    asyncio.create_task(monitor_and_verify_code(request.phone_number, api_id, api_hash, phone_code_hash))
                except Exception as e:
                    print(f"Не удалось запустить мониторинг: {e}")
                
            finally:
                await temp_client.disconnect()
        except Exception as e:
            error_msg = str(e)
            print(f"ОШИБКА при отправке кода на {request.phone_number}: {error_msg}")
            import traceback
            print(traceback.format_exc())
            raise HTTPException(
                status_code=500, 
                detail=f"Ошибка при отправке кода: {error_msg}. Проверьте TELEGRAM_API_ID и TELEGRAM_API_HASH."
            )
        
        return {
            "status": "code_sent",
            "phone_number": request.phone_number,
            "phone_code_hash": pending_codes.get(request.phone_number, {}).get("phone_code_hash"),
            "message": f"Код отправлен на {request.phone_number}! Проверьте Telegram - код должен прийти в течение минуты."
        }
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        # Безопасный вывод ошибки без emoji
        try:
            print(f"Error in get_code: {error_detail}")
            tb_str = traceback.format_exc()
            # Убрать emoji из traceback если есть
            tb_str = tb_str.encode('ascii', 'ignore').decode('ascii')
            print(tb_str)
        except:
            print(f"Error in get_code: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Ошибка при поиске кода: {error_detail}")


async def monitor_and_verify_code(phone_number: str, api_id: str, api_hash: str, phone_code_hash: str):
    """Мониторинг Telegram для автоматического получения кода и авторизации"""
    try:
        print(f"Запуск автоматического мониторинга кода для {phone_number}...")
        
        # Ждать получения кода (максимум 60 секунд)
        code = None
        for i in range(30):  # 30 проверок по 2 секунды = 60 секунд
            await asyncio.sleep(2)
            if phone_number in received_codes:
                code = received_codes.pop(phone_number)
                print(f"Код автоматически получен: {code}")
                break
        
        if not code:
            print(f"Код не получен автоматически за 60 секунд для {phone_number}")
            return
        
        # Автоматически использовать код для авторизации
        try:
            await auto_verify_code(phone_number, code, phone_code_hash, api_id, api_hash)
        except Exception as e:
            print(f"Ошибка автоматической верификации кода: {e}")
            # Сохранить код для ручного ввода
            received_codes[phone_number] = code
    except Exception as e:
        print(f"Ошибка автоматического мониторинга: {e}")


async def auto_verify_code(phone_number: str, code: str, phone_code_hash: str, api_id: str, api_hash: str):
    """Автоматически верифицировать код и создать session"""
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from datetime import datetime
        
        print(f"Автоматическая верификация кода для {phone_number}...")
        
        session = StringSession()
        client = TelegramClient(session, int(api_id), api_hash)
        
        try:
            await client.connect()
            await client.sign_in(phone_number, code, phone_code_hash=phone_code_hash)
            print(f"Авторизация успешна для {phone_number}")
            
            # Получить информацию об аккаунте
            me = await client.get_me()
            session_string = client.session.save()
            
            # Подготовить данные
            phone_filename = phone_number.replace('+', '').replace('-', '').replace(' ', '')
            
            session_data = {
                "account_id": str(me.id),
                "phone_number": phone_number,
                "username": me.username,
                "first_name": me.first_name,
                "last_name": me.last_name,
                "session_string": session_string,
                "api_id": api_id,
                "api_hash": api_hash,
                "created_at": datetime.now().isoformat()
            }
            
            # Сохранить в подпапку
            session_folder = SESSIONS_DIR / phone_filename
            session_folder.mkdir(parents=True, exist_ok=True)
            
            # Сохранить .session файл
            session_file = session_folder / f"{phone_filename}.session"
            client.session.save(str(session_file))
            
            # Сохранить .json файл
            json_file = session_folder / f"{phone_filename}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            print(f"Session автоматически создан для {phone_number}: {json_file}")
            
        finally:
            await client.disconnect()
            
    except Exception as e:
        print(f"Ошибка автоматической верификации: {e}")
        raise


async def monitor_code_from_telegram(phone_number: str, api_id: str, api_hash: str):
    """Мониторинг Telegram для автоматического получения кода - парсит ВСЕ чаты"""
    try:
        print(f"Начало мониторинга кода для {phone_number}...")
        print(f"Используются API: api_id={api_id}, api_hash={api_hash[:10]}...")
        phone_clean = phone_number.replace('+', '').replace('-', '').replace(' ', '')
        
        # Попробовать найти авторизованный аккаунт для мониторинга
        for json_file in SESSIONS_DIR.rglob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    
                # Попробовать использовать .session файл (приоритет) или session_string
                phone_filename = session_data.get('phone', session_data.get('phone_number', ''))
                session_string = session_data.get('session_string')
                session_file = None
                
                if phone_filename:
                    phone_file_clean = str(phone_filename).replace('+', '').replace('-', '').replace(' ', '')
                    session_file = SESSIONS_DIR / phone_file_clean / f"{phone_file_clean}.session"
                    if not session_file.exists():
                        # Если нет .session файла, проверить session_string
                        if not session_string:
                            continue
                else:
                    if not session_string:
                        continue
                
                from telethon import TelegramClient, events
                from telethon.sessions import StringSession
                import re
                from datetime import datetime, timezone
                
                # Создать клиент - приоритет .session файлу
                if session_file and session_file.exists():
                    # Использовать .session файл (Telethon формат)
                    monitor_client = TelegramClient(
                        str(session_file),
                        int(api_id),
                        api_hash
                    )
                elif session_string:
                    # Использовать session_string
                    monitor_client = TelegramClient(
                        StringSession(session_string),
                        int(api_id),
                        api_hash
                    )
                else:
                    continue
                
                await monitor_client.connect()
                
                # Проверить что аккаунт авторизован
                if not await monitor_client.is_user_authorized():
                    await monitor_client.disconnect()
                    continue
                
                monitor_phone = session_data.get('phone_number') or session_data.get('phone', 'unknown')
                print(f"Парсинг всех чатов через аккаунт {monitor_phone} для поиска кода {phone_number}...")
                
                from datetime import datetime, timezone
                import re
                
                # ПРИОРИТЕТ 1: Парсить сообщения от Telegram (ID 777000)
                try:
                    print(f"Получение сообщений от Telegram (777000)...")
                    telegram_service = await monitor_client.get_entity(777000)
                    print(f"Telegram service найден: {telegram_service}")
                    
                    # Получить последние сообщения от Telegram (до 100)
                    messages = await monitor_client.get_messages(telegram_service, limit=100)
                    print(f"Получено {len(messages)} сообщений от Telegram")
                    
                    for msg in messages:
                        if not msg.text:
                            continue
                        
                        msg_text = msg.text
                        text_lower = msg_text.lower()
                        
                        # Искать паттерн "Код для входа в Telegram: XXXXX" или просто код
                        # Telegram отправляет: "Код для входа в Telegram: 34703"
                        if "код для входа" in text_lower or "code" in text_lower or "код" in text_lower:
                            # Искать код (5-6 цифр)
                            code_match = re.search(r'\b(\d{5,6})\b', msg_text)
                            if code_match:
                                code = code_match.group(1)
                                if len(code) >= 5:
                                    # Проверить свежесть сообщения
                                    if msg.date:
                                        now = datetime.now(timezone.utc)
                                        msg_time = msg.date.replace(tzinfo=timezone.utc) if msg.date.tzinfo else msg.date.replace(tzinfo=timezone.utc)
                                        time_diff = (now - msg_time).total_seconds()
                                        
                                        if time_diff < 600:  # 10 минут
                                            # Сохранить код для всех вариантов номера
                                            received_codes[phone_number] = code
                                            received_codes[phone_clean] = code
                                            received_codes[phone_number.replace('+', '')] = code
                                            print(f"Код найден в сообщении от Telegram: {code}")
                                            print(f"Код сохранен в received_codes для {phone_number}: {code}")
                                            await monitor_client.disconnect()
                                            return
                except Exception as e:
                    print(f"Ошибка получения сообщений от Telegram: {e}")
                    import traceback
                    print(traceback.format_exc())
                
                # ПРИОРИТЕТ 2: Парсить все диалоги
                try:
                    print(f"Получение всех диалогов...")
                    dialogs = await monitor_client.get_dialogs(limit=None)  # ВСЕ диалоги
                    print(f"Найдено {len(dialogs)} диалогов. Парсинг...")
                    
                    for idx, dialog in enumerate(dialogs):
                        try:
                            if idx % 50 == 0:
                                print(f"Проверено {idx}/{len(dialogs)} диалогов...")
                            
                            # Читать последние сообщения из каждого диалога
                            messages = await monitor_client.get_messages(dialog.entity, limit=20)
                            
                            for msg in messages:
                                if not msg.text:
                                    continue
                                
                                msg_text = msg.text
                                text_lower = msg_text.lower()
                                
                                # Искать код если в сообщении есть номер или слова связанные с кодом
                                if (phone_clean in msg_text or 
                                    phone_number.replace('+', '') in msg_text or
                                    phone_number.replace('+', '').replace(' ', '') in msg_text or
                                    "code" in text_lower or "код" in text_lower or
                                    "verification" in text_lower or "подтверждение" in text_lower or
                                    "login code" in text_lower):
                                    
                                    # Искать код (5-6 цифр)
                                    code_match = re.search(r'\b(\d{5,6})\b', msg_text)
                                    if code_match:
                                        code = code_match.group(1)
                                        if len(code) >= 5:
                                            # Проверить свежесть сообщения
                                            if msg.date:
                                                now = datetime.now(timezone.utc)
                                                msg_time = msg.date.replace(tzinfo=timezone.utc) if msg.date.tzinfo else msg.date.replace(tzinfo=timezone.utc)
                                                time_diff = (now - msg_time).total_seconds()
                                                
                                                if time_diff < 600:  # 10 минут
                                                    received_codes[phone_number] = code
                                                    print(f"Код найден в диалоге '{dialog.name}': {code}")
                                                    print(f"Код сохранен в received_codes для {phone_number}: {code}")
                                                    await monitor_client.disconnect()
                                                    return
                        except Exception as e:
                            continue
                    
                    print(f"Проверены все {len(dialogs)} диалогов")
                except Exception as e:
                    print(f"Ошибка парсинга диалогов: {e}")
                
                # Получить entity Telegram для проверки новых сообщений
                telegram_service = None
                try:
                    telegram_service = await monitor_client.get_entity(777000)
                except:
                    try:
                        telegram_service = await monitor_client.get_entity('Telegram')
                    except:
                        telegram_service = None
                
                # Слушать новые сообщения в реальном времени и продолжать парсинг
                code_found = False
                phone_clean = phone_number.replace('+', '').replace('-', '').replace(' ', '')
                
                @monitor_client.on(events.NewMessage)
                async def handler(event):
                    nonlocal code_found
                    if code_found:
                        return
                    
                    msg_text = event.message.text or ""
                    text = msg_text.lower()
                    
                    # Искать код в сообщениях от Telegram или содержащих номер
                    if (phone_clean in msg_text or 
                        phone_number.replace('+', '') in msg_text or
                        "telegram" in text or "code" in text or "код" in text):
                        
                        code_match = re.search(r'\b(\d{5,6})\b', msg_text)
                        if code_match:
                            code = code_match.group(1)
                            if len(code) >= 5:
                                received_codes[phone_number] = code
                                code_found = True
                                print(f"Код автоматически получен из нового сообщения для {phone_number}: {code}")
                                await monitor_client.disconnect()
                
                # Периодически проверять новые сообщения (каждые 2 секунды)
                for i in range(30):  # 30 проверок по 2 секунды = 60 секунд
                    await asyncio.sleep(2)
                    
                    # Проверить новые сообщения от Telegram (777000) - ПРИОРИТЕТ
                    try:
                        if telegram_service:
                            new_messages = await monitor_client.get_messages(telegram_service, limit=10)
                            for msg in new_messages:
                                if not msg.text:
                                    continue
                                msg_text = msg.text
                                text = msg_text.lower()
                                
                                # Искать код в сообщениях от Telegram
                                if "код для входа" in text or "code" in text or "код" in text:
                                    code_match = re.search(r'\b(\d{5,6})\b', msg_text)
                                    if code_match:
                                        code = code_match.group(1)
                                        if len(code) >= 5:
                                            if msg.date:
                                                from datetime import datetime, timezone
                                                now = datetime.now(timezone.utc)
                                                msg_time = msg.date.replace(tzinfo=timezone.utc) if msg.date.tzinfo else msg.date.replace(tzinfo=timezone.utc)
                                                time_diff = (now - msg_time).total_seconds()
                                                
                                                if time_diff < 600:  # 10 минут
                                                    # Сохранить для всех вариантов
                                                    received_codes[phone_number] = code
                                                    received_codes[phone_clean] = code
                                                    received_codes[phone_number.replace('+', '')] = code
                                                    print(f"Код найден в новых сообщениях от Telegram для {phone_number}: {code}")
                                                    await monitor_client.disconnect()
                                                    return
                    except Exception as e:
                        print(f"Ошибка проверки новых сообщений от Telegram: {e}")
                    
                    if phone_number in received_codes:
                        break
                
                await monitor_client.disconnect()
                break
            except Exception as e:
                print(f"Ошибка при мониторинге через {json_file}: {e}")
                continue
    except Exception as e:
        print(f"Ошибка мониторинга: {e}")


@app.get("/api/v1/sessions/check-code/{phone_number}", response_class=JSONResponse)
async def check_code(phone_number: str):
    """Проверить есть ли автоматически полученный код или созданный session"""
    # Проверить есть ли код в хранилище (проверяем разные форматы номера)
    phone_variants = [
        phone_number,
        phone_number.replace('+', ''),
        phone_number.replace('+', '').replace('-', '').replace(' ', ''),
        f"+{phone_number}" if not phone_number.startswith('+') else phone_number
    ]
    
    for phone_var in phone_variants:
        if phone_var in received_codes:
            code = received_codes.pop(phone_var)
            print(f"Код найден для {phone_number} (вариант {phone_var}): {code}")
            return {
                "status": "code_found",
                "code": code,
                "message": "Код получен автоматически!"
            }
    
    # Отладочная информация
    if received_codes:
        print(f"Проверка кода для {phone_number}. Доступные ключи в received_codes: {list(received_codes.keys())}")
    
    # Проверить был ли создан session автоматически
    phone_filename = phone_number.replace('+', '').replace('-', '').replace(' ', '')
    session_json = SESSIONS_DIR / phone_filename / f"{phone_filename}.json"
    if session_json.exists():
        # Проверить что файл свежий (создан недавно)
        import time
        file_time = session_json.stat().st_mtime
        current_time = time.time()
        if (current_time - file_time) < 120:  # Файл создан менее 2 минут назад
            return {
                "status": "session_created",
                "message": "Session создан автоматически!",
                "filename": session_json.name
            }
    
    return {
        "status": "no_code",
        "message": "Ожидание кода..."
    }


@app.post("/api/v1/sessions/verify-code", response_class=JSONResponse)
async def verify_code(request: VerifyCodeRequest):
    """Проверить код и получить session (требует phone_code_hash от get-code)"""
    try:
        # Попробовать импортировать telethon
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
        except ImportError:
            raise HTTPException(
                status_code=500, 
                detail="Telethon не установлен. Установите: pip install telethon"
            )
        
        from datetime import datetime
        
        # Получить API credentials
        api_id = os.getenv('TELEGRAM_API_ID')
        api_hash = os.getenv('TELEGRAM_API_HASH')
        
        # Попробовать загрузить из .env файла
        if not api_id or not api_hash:
            env_file = BASE_PROJECT_DIR / ".env"
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            if key.strip() == 'TELEGRAM_API_ID':
                                api_id = value.strip()
                            elif key.strip() == 'TELEGRAM_API_HASH':
                                api_hash = value.strip()
        
        if not api_id or not api_hash:
            raise HTTPException(status_code=400, detail="TELEGRAM_API_ID и TELEGRAM_API_HASH не установлены")
        
        # Если phone_code_hash не передан, попробовать получить из pending_codes
        phone_code_hash = request.phone_code_hash
        if not phone_code_hash:
            pending = pending_codes.get(request.phone_number, {})
            phone_code_hash = pending.get("phone_code_hash")
        
        if not phone_code_hash:
            raise HTTPException(
                status_code=400, 
                detail="phone_code_hash не найден. Сначала вызовите /api/v1/sessions/get-code или используйте /api/v1/sessions/verify-code-direct"
            )
        
        # Создать клиента
        session = StringSession()
        client = TelegramClient(session, int(api_id), api_hash)
        
        try:
            await client.connect()
            
            # Войти с кодом (код который пришел в Telegram)
            print(f"Проверка кода для {request.phone_number}...")
            try:
                await client.sign_in(request.phone_number, request.code, phone_code_hash=phone_code_hash)
                print("Код принят, авторизация успешна")
            except Exception as e:
                error_str = str(e).lower()
                # Если требуется пароль 2FA
                if "password" in error_str or "2fa" in error_str or "two" in error_str:
                    if not request.password:
                        print("Требуется пароль 2FA")
                        return {
                            "status": "need_password",
                            "detail": "Требуется пароль 2FA. Введите пароль ниже."
                        }
                    print("Проверка пароля 2FA...")
                    await client.sign_in(password=request.password)
                    print("Пароль 2FA принят")
                else:
                    print(f"Ошибка при входе: {e}")
                    raise
            
            # Получить информацию об аккаунте
            me = await client.get_me()
            session_string = client.session.save()
            
            # Подготовить данные
            phone_filename = request.phone_number.replace('+', '').replace('-', '').replace(' ', '')
            
            session_data = {
                "account_id": str(me.id),
                "phone_number": request.phone_number,
                "username": me.username,
                "first_name": me.first_name,
                "last_name": me.last_name,
                "session_string": session_string,
                "api_id": api_id,
                "api_hash": api_hash,
                "created_at": datetime.now().isoformat()
            }
            
            # Сохранить в подпапку
            session_folder = SESSIONS_DIR / phone_filename
            session_folder.mkdir(parents=True, exist_ok=True)
            
            # Сохранить .session файл
            session_file = session_folder / f"{phone_filename}.session"
            client.session.save(str(session_file))
            
            # Сохранить .json файл
            json_file = session_folder / f"{phone_filename}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            return {
                "status": "success",
                "phone_number": request.phone_number,
                "account_id": str(me.id),
                "filename": json_file.name,
                "path": str(json_file.relative_to(SESSIONS_DIR))
            }
            
        finally:
            await client.disconnect()
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Error in verify_code: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка при проверке кода: {error_detail}")


@app.post("/api/v1/sessions/verify-code-direct", response_class=JSONResponse)
async def verify_code_direct(request: VerifyCodeDirectRequest):
    """
    Проверить код, полученный через обычный Telegram (без предварительного get-code)
    ИСПОЛЬЗУЙТЕ ЭТОТ ENDPOINT, если вы запросили код через обычный Telegram приложение
    """
    try:
        # Попробовать импортировать telethon
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
        except ImportError:
            raise HTTPException(
                status_code=500, 
                detail="Telethon не установлен. Установите: pip install telethon"
            )
        
        from datetime import datetime
        
        # Получить API credentials
        api_id = os.getenv('TELEGRAM_API_ID')
        api_hash = os.getenv('TELEGRAM_API_HASH')
        
        # Попробовать загрузить из .env файла
        if not api_id or not api_hash:
            env_file = BASE_PROJECT_DIR / ".env"
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            if key.strip() == 'TELEGRAM_API_ID':
                                api_id = value.strip()
                            elif key.strip() == 'TELEGRAM_API_HASH':
                                api_hash = value.strip()
        
        if not api_id or not api_hash:
            raise HTTPException(status_code=400, detail="TELEGRAM_API_ID и TELEGRAM_API_HASH не установлены")
        
        # Создать клиента
        session = StringSession()
        client = TelegramClient(session, int(api_id), api_hash)
        
        try:
            await client.connect()
            
            # Попробовать получить phone_code_hash через API
            # ВАЖНО: Это отправит НОВЫЙ код, но мы попробуем использовать введенный код
            print(f"Попытка использовать код для {request.phone_number}...")
            phone_code_hash = None
            
            try:
                result = await client.send_code_request(request.phone_number)
                phone_code_hash = result.phone_code_hash
                print(f"INFO: Получен phone_code_hash. Попытка использовать введенный код...")
                print(f"WARNING: ВНИМАНИЕ! Отправлен НОВЫЙ код в Telegram. Если введенный код не подойдет, используйте новый код.")
            except Exception as e:
                print(f"WARNING: Не удалось получить phone_code_hash: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Не удалось инициализировать авторизацию: {str(e)}. Попробуйте запросить код через систему."
                )
            
            # Попробовать войти с введенным кодом
            print(f"Проверка введенного кода для {request.phone_number}...")
            try:
                await client.sign_in(request.phone_number, request.code, phone_code_hash=phone_code_hash)
                print("Код принят, авторизация успешна")
            except Exception as e:
                error_str = str(e).lower()
                
                # Если код не подошел
                if "phone_code_hash" in error_str or "code" in error_str or "invalid" in error_str:
                    print(f"WARNING: Введенный код не подошел.")
                    raise HTTPException(
                        status_code=400,
                        detail="Введенный код не подошел. В Telegram был отправлен НОВЫЙ код - используйте его. Или запросите код через систему и используйте код, который придет после запроса."
                    )
                
                # Если требуется пароль 2FA
                if "password" in error_str or "2fa" in error_str or "two" in error_str:
                    if not request.password:
                        print("Требуется пароль 2FA")
                        return {
                            "status": "need_password",
                            "detail": "Требуется пароль 2FA. Введите пароль ниже."
                        }
                    print("Проверка пароля 2FA...")
                    await client.sign_in(password=request.password)
                    print("Пароль 2FA принят")
                else:
                    print(f"Ошибка при входе: {e}")
                    raise
            
            # Получить информацию об аккаунте
            me = await client.get_me()
            session_string = client.session.save()
            
            # Подготовить данные
            phone_filename = request.phone_number.replace('+', '').replace('-', '').replace(' ', '')
            
            session_data = {
                "account_id": str(me.id),
                "phone_number": request.phone_number,
                "username": me.username,
                "first_name": me.first_name,
                "last_name": me.last_name,
                "session_string": session_string,
                "api_id": api_id,
                "api_hash": api_hash,
                "created_at": datetime.now().isoformat()
            }
            
            # Сохранить в подпапку
            session_folder = SESSIONS_DIR / phone_filename
            session_folder.mkdir(parents=True, exist_ok=True)
            
            # Сохранить .session файл
            session_file = session_folder / f"{phone_filename}.session"
            client.session.save(str(session_file))
            
            # Сохранить .json файл
            json_file = session_folder / f"{phone_filename}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            return {
                "status": "success",
                "phone_number": request.phone_number,
                "account_id": str(me.id),
                "filename": json_file.name,
                "path": str(json_file.relative_to(SESSIONS_DIR))
            }
            
        finally:
            await client.disconnect()
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Error in verify_code_direct: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка при проверке кода: {error_detail}")


class ParseCodeRequest(BaseModel):
    """Запрос на парсинг кода из сообщений Telegram"""
    phone_number: str


@app.post("/api/v1/sessions/parse-code", response_class=JSONResponse)
async def parse_code_from_telegram(request: ParseCodeRequest):
    """
    Парсить входящие сообщения Telegram через авторизованную сессию и найти код авторизации.
    Использует существующий .session файл для подключения.
    """
    try:
        from telethon import TelegramClient
        from datetime import datetime, timezone
        import re
        
        phone_clean = request.phone_number.replace('+', '').replace('-', '').replace(' ', '')
        
        # Найти .session файл
        session_file = SESSIONS_DIR / phone_clean / f"{phone_clean}.session"
        json_file = SESSIONS_DIR / phone_clean / f"{phone_clean}.json"
        
        if not session_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Session файл не найден: {session_file}"
            )
        
        # Загрузить app_id и app_hash из JSON
        app_id = None
        app_hash = None
        
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    app_id = session_data.get('app_id') or session_data.get('api_id')
                    app_hash = session_data.get('app_hash') or session_data.get('api_hash')
            except Exception as e:
                print(f"Ошибка чтения JSON: {e}")
        
        # Если нет в JSON, попробовать из .env
        if not app_id or not app_hash:
            app_id = os.getenv('TELEGRAM_API_ID')
            app_hash = os.getenv('TELEGRAM_API_HASH')
            
            # Попробовать загрузить из .env файла
            if not app_id or not app_hash:
                env_file = BASE_PROJECT_DIR / ".env"
                if env_file.exists():
                    with open(env_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                if key.strip() == 'TELEGRAM_API_ID':
                                    app_id = value.strip()
                                elif key.strip() == 'TELEGRAM_API_HASH':
                                    app_hash = value.strip()
        
        if not app_id or not app_hash:
            raise HTTPException(
                status_code=400,
                detail="Не найдены app_id/app_hash. Укажите в JSON файле сессии или в .env"
            )
        
        print(f"Подключение к Telegram через сессию {phone_clean}...")
        
        # Создать клиент с файловой сессией
        client = TelegramClient(
            str(session_file),
            int(app_id),
            app_hash
        )
        
        codes_found = []
        
        try:
            await client.connect()
            
            if not await client.is_user_authorized():
                raise HTTPException(
                    status_code=401,
                    detail="Сессия не авторизована. Требуется повторная авторизация."
                )
            
            me = await client.get_me()
            print(f"Авторизован как: {me.first_name} ({me.phone})")
            
            # Получить сообщения от Telegram (ID 777000)
            all_messages = []
            try:
                telegram_service = await client.get_entity(777000)
                messages = await client.get_messages(telegram_service, limit=100)
                
                print(f"Получено {len(messages)} сообщений от Telegram")
                
                now = datetime.now(timezone.utc)
                
                # Вывести первые 3 сообщения для отладки
                for i, msg in enumerate(messages[:3]):
                    if msg.text:
                        print(f"Сообщение {i+1}: {msg.text[:100]}...")
                
                for msg in messages:
                    if not msg.text:
                        continue
                    
                    msg_text = msg.text
                    text_lower = msg_text.lower()
                    
                    # Вычислить время сообщения
                    time_diff = 0
                    if msg.date:
                        msg_time = msg.date.replace(tzinfo=timezone.utc) if msg.date.tzinfo is None else msg.date
                        time_diff = (now - msg_time).total_seconds()
                    
                    # Сохранить все сообщения для отладки
                    all_messages.append({
                        "text": msg_text[:200],
                        "time": msg.date.isoformat() if msg.date else None,
                        "seconds_ago": int(time_diff) if msg.date else None
                    })
                    
                    # Искать код в ЛЮБЫХ сообщениях (5-6 цифр подряд)
                    code_matches = re.findall(r'\b(\d{5,6})\b', msg_text)
                    for code in code_matches:
                        if len(code) >= 5:
                            codes_found.append({
                                "code": code,
                                "message": msg_text[:200] + "..." if len(msg_text) > 200 else msg_text,
                                "time": msg.date.isoformat() if msg.date else None,
                                "seconds_ago": int(time_diff) if msg.date else None,
                                "hours_ago": round(time_diff / 3600, 1) if time_diff else 0
                            })
                
            except Exception as e:
                print(f"Ошибка получения сообщений от Telegram: {e}")
                # Попробовать искать по всем диалогам
                try:
                    dialogs = await client.get_dialogs(limit=10)
                    for dialog in dialogs:
                        if "telegram" in str(dialog.name).lower():
                            messages = await client.get_messages(dialog.entity, limit=50)
                            for msg in messages:
                                if not msg.text:
                                    continue
                                
                                msg_text = msg.text
                                
                                time_diff = 0
                                if msg.date:
                                    msg_time = msg.date.replace(tzinfo=timezone.utc) if msg.date.tzinfo is None else msg.date
                                    time_diff = (now - msg_time).total_seconds()
                                
                                # Искать коды без ограничения по времени
                                code_matches = re.findall(r'\b(\d{5,6})\b', msg_text)
                                for code in code_matches:
                                    if len(code) >= 5:
                                        codes_found.append({
                                            "code": code,
                                            "message": msg_text[:200] + "..." if len(msg_text) > 200 else msg_text,
                                            "time": msg.date.isoformat() if msg.date else None,
                                            "seconds_ago": int(time_diff) if msg.date else None,
                                            "hours_ago": round(time_diff / 3600, 1) if time_diff else 0
                                        })
                except Exception as e2:
                    print(f"Ошибка поиска по диалогам: {e2}")
        
        finally:
            await client.disconnect()
        
        if codes_found:
            # Вернуть самый свежий код
            codes_found.sort(key=lambda x: x.get('seconds_ago', 9999))
            return {
                "status": "found",
                "code": codes_found[0]["code"],
                "all_codes": codes_found,
                "all_messages": all_messages[:10],  # Первые 10 сообщений для отладки
                "message": f"Найден код: {codes_found[0]['code']}",
                "session_phone": phone_clean
            }
        else:
            return {
                "status": "not_found",
                "code": None,
                "all_messages": all_messages[:10],  # Первые 10 сообщений для отладки
                "message": "Код не найден. Проверьте сообщения выше.",
                "session_phone": phone_clean
            }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Error in parse_code_from_telegram: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {error_detail}")


# ========== Group Chat with AI (Groq FREE / OpenAI) ==========

# AI Provider: "groq" (бесплатный) или "openai"
# Groq работает когда VPN выключен
AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")

# Groq API Key (бесплатный! Получить: https://console.groq.com)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# OpenAI API Key (платный)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Выбор активного ключа (мутабельные для динамической смены)
AI_API_KEY = GROQ_API_KEY if AI_PROVIDER == "groq" else OPENAI_API_KEY

# Хранилище активных групп и их состояния
active_chat_groups = {}
chat_logs = {}


class SetAIKeyRequest(BaseModel):
    """Запрос на установку AI ключа"""
    api_key: str
    provider: str = "groq"  # "groq" (бесплатный) или "openai"


class AutoGroupRequest(BaseModel):
    """Запрос на автоматическое создание групп"""
    min_group_size: int = 5  # Минимальный размер группы
    max_group_size: int = 10  # Максимальный размер группы
    random_size: bool = True  # Рандомный размер для каждой группы
    assign_topics: bool = True  # Назначать случайные темы группам
    create_telegram: bool = True  # Сразу создавать TG группы


# Глобальная переменная для автоматического чата
auto_chat_active = {}  # group_id -> True/False

# Глобальные логи для отображения в UI
live_logs = []  # Последние 100 сообщений
progress_status = {"active": False, "current": 0, "total": 0, "message": ""}


class StartChatRequest(BaseModel):
    """Запрос на запуск чата в группе"""
    group_id: str
    topic_id: str = "travel"  # ID темы для обсуждения
    messages_per_member: int = 2  # Сообщений на участника


# ========== Topics API ==========

@app.get("/api/v1/topics", response_class=JSONResponse)
async def get_topics():
    """Получить все доступные темы для обсуждения"""
    try:
        if not TOPICS_FILE.exists():
            # Вернуть базовые темы
            return {"topics": [
                {"id": "travel", "name": "Путешествия", "prompt": "Обсуди любимые места для путешествий"},
                {"id": "games", "name": "Игры", "prompt": "Обсуди любимые видеоигры"},
                {"id": "music", "name": "Музыка", "prompt": "Обсуди любимую музыку и исполнителей"},
                {"id": "movies", "name": "Фильмы", "prompt": "Обсуди любимые фильмы"}
            ]}
        
        with open(TOPICS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Если есть "topics" - вернуть как есть
        if "topics" in data:
            return data
        
        # Если нет - сформировать из структуры
        return {"topics": data.get("topics", [
            {"id": "general", "name": "Общение", "prompt": "Веди дружескую беседу"}
        ])}
    except Exception as e:
        return {"topics": [{"id": "general", "name": "Общение", "prompt": "Веди беседу"}], "error": str(e)}


@app.post("/api/v1/topics", response_class=JSONResponse)
async def add_topic(topic: dict):
    """Добавить новую тему"""
    try:
        if not TOPICS_FILE.exists():
            data = {"topics": [], "default_topic": "travel"}
        else:
            with open(TOPICS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        # Добавить тему
        data["topics"].append(topic)
        
        with open(TOPICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return {"status": "success", "message": "Тема добавлена"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/groups/auto-create", response_class=JSONResponse)
async def auto_create_groups(request: AutoGroupRequest):
    """
    Автоматически создать группы из всех доступных сессий.
    Разбивает сессии на группы по group_size человек.
    """
    import random
    
    try:
        # Получить все авторизованные сессии
        authorized_sessions = []
        
        for session_folder in SESSIONS_DIR.iterdir():
            if not session_folder.is_dir():
                continue
            
            phone = session_folder.name
            session_file = session_folder / f"{phone}.session"
            json_file = session_folder / f"{phone}.json"
            
            if session_file.exists() and json_file.exists():
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    authorized_sessions.append({
                        "phone": phone,
                        "first_name": data.get("first_name", "User"),
                        "session_file": str(session_file),
                        "json_file": str(json_file),
                        "app_id": data.get("app_id"),
                        "app_hash": data.get("app_hash")
                    })
                except Exception as e:
                    print(f"Ошибка чтения сессии {phone}: {e}")
                    continue
        
        if len(authorized_sessions) < 2:
            raise HTTPException(
                status_code=400,
                detail=f"Недостаточно сессий. Найдено: {len(authorized_sessions)}, минимум: 2"
            )
        
        # Перемешать сессии
        random.shuffle(authorized_sessions)
        
        # Загрузить темы если нужно назначать
        available_topics = []
        if request.assign_topics and TOPICS_FILE.exists():
            try:
                with open(TOPICS_FILE, 'r', encoding='utf-8') as f:
                    topics_data = json.load(f)
                    available_topics = topics_data.get("topics", [])
            except:
                pass
        
        # Разбить на группы с РАНДОМНЫМ размером
        groups_created = []
        remaining_sessions = list(authorized_sessions)  # Копия списка
        group_number = 1
        
        while len(remaining_sessions) >= request.min_group_size:
            # Рандомный размер группы
            if request.random_size:
                max_possible = min(request.max_group_size, len(remaining_sessions))
                group_size = random.randint(request.min_group_size, max_possible)
            else:
                group_size = min(request.min_group_size, len(remaining_sessions))
            
            # Взять участников для группы
            group_members = remaining_sessions[:group_size]
            remaining_sessions = remaining_sessions[group_size:]
            
            if len(group_members) < 2:
                break
            
            group_id = f"group_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{group_number}"
            
            # Первый участник - админ
            admin = group_members[0]
            members = group_members[1:]
            
            # Назначить случайную тему
            assigned_topic = None
            if available_topics:
                assigned_topic = random.choice(available_topics)
            
            # Название группы = название темы
            group_title = assigned_topic["name"] if assigned_topic else f"Группа {group_number}"
            
            group_data = {
                "id": group_id,
                "title": group_title,
                "admin": admin,
                "members": members,
                "all_phones": [m["phone"] for m in group_members],
                "member_count": len(group_members),
                "created_at": datetime.now().isoformat(),
                "chat_active": False,
                "status": "ready",  # Сразу готово к чату
                "assigned_topic": assigned_topic
            }
            
            groups_created.append(group_data)
            group_number += 1
        
        # Сохранить группы
        groups_file_data = {"groups": [], "schedule": {"enabled": False, "interval_minutes": 60}}
        if GROUPS_FILE.exists():
            try:
                with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
                    groups_file_data = json.load(f)
                    if isinstance(groups_file_data, list):
                        groups_file_data = {"groups": groups_file_data, "schedule": {"enabled": False, "interval_minutes": 60}}
            except:
                pass
        
        groups_file_data["groups"].extend(groups_created)
        
        with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(groups_file_data, f, indent=2, ensure_ascii=False)
        
        # Создать реальные Telegram группы если включено
        telegram_created = 0
        if request.create_telegram:
            from telethon import TelegramClient
            from telethon.tl.functions.messages import CreateChatRequest
            from telethon.tl.functions.contacts import ImportContactsRequest
            from telethon.tl.types import InputPhoneContact
            
            add_log(f"Создание TG групп: {len(groups_created)} шт.", "info")
            
            for idx, group in enumerate(groups_created):
                try:
                    add_log(f"[{idx+1}/{len(groups_created)}] Создаю группу: {group['title']}", "info")
                    
                    admin = group["admin"]
                    admin_phone = admin["phone"]
                    admin_session = SESSIONS_DIR / admin_phone / f"{admin_phone}.session"
                    
                    if not admin_session.exists():
                        add_log(f"Session не найден: {admin_phone}", "error")
                        continue
                    
                    app_id = admin.get("app_id") or int(os.getenv('TELEGRAM_API_ID', 2040))
                    app_hash = admin.get("app_hash") or os.getenv('TELEGRAM_API_HASH', "b18441a1ff607e10a989891a5462e627")
                    
                    admin_client = TelegramClient(str(admin_session), app_id, app_hash)
                    await admin_client.connect()
                    
                    if not await admin_client.is_user_authorized():
                        add_log(f"Админ не авторизован: {admin_phone}", "error")
                        await admin_client.disconnect()
                        continue
                    
                    add_log(f"Админ подключен: {admin_phone}", "success")
                    
                    # Сначала добавить контакты
                    contacts_to_add = []
                    for i, member in enumerate(group["members"]):
                        member_phone = member["phone"]
                        contacts_to_add.append(InputPhoneContact(
                            client_id=i,
                            phone=f"+{member_phone}",
                            first_name=member.get("first_name", f"User{i}"),
                            last_name=member.get("last_name", "")
                        ))
                    
                    if contacts_to_add:
                        add_log(f"Добавляю {len(contacts_to_add)} контактов...", "info")
                        try:
                            result = await admin_client(ImportContactsRequest(contacts_to_add))
                            add_log(f"Импортировано: {len(result.users)} контактов", "success")
                            await asyncio.sleep(2)
                        except Exception as e:
                            add_log(f"Ошибка импорта контактов: {str(e)[:40]}", "error")
                    
                    # Теперь получить entities
                    member_entities = []
                    for member in group["members"]:
                        try:
                            member_phone = member["phone"]
                            entity = await admin_client.get_entity(f"+{member_phone}")
                            member_entities.append(entity)
                            add_log(f"Найден: +{member_phone}", "success")
                        except Exception as e:
                            add_log(f"Не найден: +{member.get('phone', '?')}", "warning")
                    
                    if member_entities:
                        add_log(f"Создаю группу с {len(member_entities)} участниками...", "info")
                        
                        # Создать группу
                        result = await admin_client(CreateChatRequest(
                            users=member_entities,
                            title=group["title"]
                        ))
                        
                        # Получить ID группы (разные варианты структуры ответа)
                        tg_id = None
                        try:
                            if hasattr(result, 'chats') and result.chats:
                                tg_id = result.chats[0].id
                            elif hasattr(result, 'updates') and hasattr(result.updates, '__iter__'):
                                for upd in result.updates:
                                    if hasattr(upd, 'chat_id'):
                                        tg_id = upd.chat_id
                                        break
                            elif hasattr(result, 'chat'):
                                tg_id = result.chat.id
                            elif hasattr(result, 'chat_id'):
                                tg_id = result.chat_id
                            
                            # Если ничего не нашли, попробуем получить из диалогов
                            if not tg_id:
                                dialogs = await admin_client.get_dialogs(limit=5)
                                for d in dialogs:
                                    if d.title == group["title"]:
                                        tg_id = d.id
                                        break
                        except Exception as e:
                            add_log(f"Ошибка получения ID: {str(e)[:30]}", "warning")
                        
                        if tg_id:
                            group["telegram_group_id"] = tg_id
                            group["status"] = "created"
                            telegram_created += 1
                            add_log(f"ГРУППА СОЗДАНА: {group['title']} (ID: {tg_id})", "success")
                        else:
                            # Группа создана но ID не получен - попробуем найти
                            add_log(f"Группа создана, ищу ID...", "info")
                            await asyncio.sleep(1)
                            dialogs = await admin_client.get_dialogs(limit=10)
                            for d in dialogs:
                                if d.title == group["title"]:
                                    tg_id = d.id
                                    group["telegram_group_id"] = tg_id
                                    group["status"] = "created"
                                    telegram_created += 1
                                    add_log(f"ГРУППА НАЙДЕНА: {group['title']} (ID: {tg_id})", "success")
                                    break
                    else:
                        group["status"] = "no_members"
                        add_log(f"Нет участников для группы: {group['title']}", "error")
                    
                    await admin_client.disconnect()
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    add_log(f"Ошибка: {str(e)[:50]}", "error")
                    group["status"] = "error"
            
            # Сохранить обновлённые статусы
            with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
                json.dump(groups_file_data, f, indent=2, ensure_ascii=False)
            
            add_log(f"Готово! Создано {telegram_created} TG групп", "success")
        
        # Статистика по группам
        group_stats = []
        for g in groups_created:
            topic_name = g["assigned_topic"]["name"] if g.get("assigned_topic") else "Без темы"
            group_stats.append({
                "title": g["title"],
                "members": g["member_count"],
                "topic": topic_name,
                "status": g.get("status", "ready")
            })
        
        leftover = len(remaining_sessions)
        
        return {
            "status": "success",
            "message": f"Создано {len(groups_created)} групп, {telegram_created} в Telegram",
            "summary": {
                "total_contacts": len(authorized_sessions),
                "groups_created": len(groups_created),
                "telegram_created": telegram_created,
                "contacts_distributed": len(authorized_sessions) - leftover,
                "leftover": leftover
            },
            "group_stats": group_stats,
            "groups": groups_created
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in auto_create_groups: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/groups/{group_id}/create-telegram", response_class=JSONResponse)
async def create_telegram_group(group_id: str):
    """
    Создать Telegram группу для указанной группы.
    
    Процесс:
    1. Каждый участник пишет админу приветствие (создает контакт)
    2. Админ отвечает каждому с приглашением
    3. Админ создает группу с участниками
    """
    import random
    
    try:
        from telethon import TelegramClient
        from telethon.tl.functions.messages import CreateChatRequest
        from telethon.tl.functions.contacts import ImportContactsRequest
        from telethon.tl.types import InputPhoneContact
        
        # Загрузить группы
        if not GROUPS_FILE.exists():
            raise HTTPException(status_code=404, detail="Файл групп не найден")
        
        with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
            groups_data = json.load(f)
        
        if isinstance(groups_data, list):
            groups_data = {"groups": groups_data}
        
        # Найти группу
        group = None
        group_index = -1
        for i, g in enumerate(groups_data.get("groups", [])):
            if g["id"] == group_id:
                group = g
                group_index = i
                break
        
        if not group:
            raise HTTPException(status_code=404, detail=f"Группа {group_id} не найдена")
        
        admin = group["admin"]
        admin_phone = admin["phone"]
        admin_session = SESSIONS_DIR / admin_phone / f"{admin_phone}.session"
        
        if not admin_session.exists():
            raise HTTPException(status_code=400, detail=f"Session файл админа не найден: {admin_phone}")
        
        app_id = admin.get("app_id") or 2040
        app_hash = admin.get("app_hash") or "b18441a1ff607e10a989891a5462e627"
        
        # Сообщения для приглашений
        invite_messages = [
            "Привет! Я тебя где-то видел, давай общаться!",
            "Здравствуй! Интересно пообщаться, вступай в наш чат!",
            "Привет! Собираем компанию для общения, присоединяйся!",
            "Хей! Создаю группу для общения, будешь с нами?",
            "Приветик! Давно хотел написать, создаю чат - вступай!"
        ]
        
        member_entities = []
        messages_sent = []
        
        # Шаг 1: Каждый участник пишет админу приветствие
        print("Шаг 1: Участники пишут админу...")
        
        for member in group["members"]:
            member_phone = member["phone"]
            member_session = SESSIONS_DIR / member_phone / f"{member_phone}.session"
            
            if not member_session.exists():
                print(f"Session не найден: {member_phone}")
                continue
            
            member_app_id = member.get("app_id") or 2040
            member_app_hash = member.get("app_hash") or "b18441a1ff607e10a989891a5462e627"
            
            try:
                member_client = TelegramClient(str(member_session), int(member_app_id), member_app_hash)
                await member_client.connect()
                
                if not await member_client.is_user_authorized():
                    print(f"Не авторизован: {member_phone}")
                    await member_client.disconnect()
                    continue
                
                me = await member_client.get_me()
                
                # Импортировать контакт админа
                admin_phone_formatted = "+" + admin_phone if not admin_phone.startswith("+") else admin_phone
                contact = InputPhoneContact(
                    client_id=random.randint(1, 999999),
                    phone=admin_phone_formatted,
                    first_name="Admin",
                    last_name=""
                )
                await member_client(ImportContactsRequest([contact]))
                
                # Получить entity админа
                try:
                    admin_entity = await member_client.get_entity(admin_phone_formatted)
                    
                    # Написать админу приветствие
                    greeting = random.choice([
                        "Привет!",
                        "Здравствуй!",
                        "Приветик!",
                        "Хей!"
                    ])
                    # Typing эффект (реалистичнее!)
                    typing_time = random.uniform(1, 3)
                    async with member_client.action(admin_entity, 'typing'):
                        await asyncio.sleep(typing_time)
                    await member_client.send_message(admin_entity, greeting)
                    print(f"{member_phone} написал админу: {greeting}")
                    messages_sent.append(f"{member_phone} -> админ: {greeting}")
                    
                except Exception as e:
                    print(f"Не удалось написать админу от {member_phone}: {e}")
                
                await member_client.disconnect()
                await asyncio.sleep(1)  # Пауза
                
            except Exception as e:
                print(f"Ошибка с {member_phone}: {e}")
        
        await asyncio.sleep(2)
        
        # Шаг 2: Админ отвечает и добавляет в контакты
        print("Шаг 2: Админ отвечает участникам...")
        
        admin_client = TelegramClient(str(admin_session), int(app_id), app_hash)
        await admin_client.connect()
        
        if not await admin_client.is_user_authorized():
            raise HTTPException(status_code=401, detail=f"Админ {admin_phone} не авторизован")
        
        for i, member in enumerate(group["members"]):
            member_phone = member["phone"]
            member_phone_formatted = "+" + member_phone if not member_phone.startswith("+") else member_phone
            
            try:
                # Импортировать контакт участника
                contact = InputPhoneContact(
                    client_id=random.randint(1, 999999),
                    phone=member_phone_formatted,
                    first_name=member.get("first_name", f"User{i+1}"),
                    last_name=""
                )
                await admin_client(ImportContactsRequest([contact]))
                
                # Получить entity участника
                member_entity = await admin_client.get_entity(member_phone_formatted)
                member_entities.append(member_entity)
                
                # Отправить приглашение с typing эффектом
                invite_msg = random.choice(invite_messages)
                typing_time = random.uniform(2, 4)
                async with admin_client.action(member_entity, 'typing'):
                    await asyncio.sleep(typing_time)
                await admin_client.send_message(member_entity, invite_msg)
                print(f"Админ -> {member_phone}: {invite_msg}")
                messages_sent.append(f"Админ -> {member_phone}: {invite_msg}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Не удалось ответить {member_phone}: {e}")
        
        await asyncio.sleep(2)
        
        # Шаг 3: Создать группу
        print(f"Шаг 3: Создание группы '{group['title']}'...")
        
        telegram_group_id = None
        
        if member_entities:
            try:
                result = await admin_client(CreateChatRequest(
                    users=member_entities,
                    title=group["title"]
                ))
                
                # Получить ID группы
                if hasattr(result, 'chats') and result.chats:
                    telegram_group_id = result.chats[0].id
                elif hasattr(result, 'updates'):
                    for chat in getattr(result, 'chats', []):
                        telegram_group_id = chat.id
                        break
                
                if telegram_group_id:
                    print(f"Группа создана! ID: {telegram_group_id}")
                    
                    # Отправить приветственное сообщение в группу с typing
                    typing_time = random.uniform(2, 4)
                    async with admin_client.action(telegram_group_id, 'typing'):
                        await asyncio.sleep(typing_time)
                    await admin_client.send_message(
                        telegram_group_id,
                        "Привет всем! Рад что вы здесь. Давайте общаться!"
                    )
                    
            except Exception as e:
                print(f"Ошибка создания группы: {e}")
                telegram_group_id = "error"
        
        await admin_client.disconnect()
        
        if not telegram_group_id:
            telegram_group_id = "pending"
        
        # Обновить данные группы
        groups_data["groups"][group_index]["telegram_group_id"] = telegram_group_id
        groups_data["groups"][group_index]["status"] = "created" if telegram_group_id and telegram_group_id != "pending" else "invites_sent"
        groups_data["groups"][group_index]["messages_sent"] = messages_sent
        
        with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(groups_data, f, indent=2, ensure_ascii=False)
        
        return {
            "status": "success",
            "message": f"Группа создана! Отправлено {len(messages_sent)} приглашений.",
            "telegram_group_id": telegram_group_id,
            "members_invited": len(member_entities),
            "messages": messages_sent
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error creating Telegram group: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ai/set-key", response_class=JSONResponse)
async def set_ai_key(request: SetAIKeyRequest):
    """
    Установить API ключ для AI (Groq бесплатный или OpenAI).
    
    Groq: https://console.groq.com (бесплатно, 14400 запросов/день)
    OpenAI: https://platform.openai.com (платно)
    """
    global AI_API_KEY, AI_PROVIDER, GROQ_API_KEY, OPENAI_API_KEY
    
    try:
        AI_PROVIDER = request.provider
        AI_API_KEY = request.api_key
        
        if request.provider == "groq":
            GROQ_API_KEY = request.api_key
        else:
            OPENAI_API_KEY = request.api_key
        
        # Сбросить менеджер чата для использования нового ключа
        from openai_chat import reset_chat_manager
        reset_chat_manager()
        
        provider_name = "Groq (FREE)" if request.provider == "groq" else "OpenAI"
        print(f"[AI] {provider_name} key set successfully")
        
        return {
            "status": "success",
            "provider": request.provider,
            "message": f"{provider_name} ключ успешно установлен!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/ai/status", response_class=JSONResponse)
async def get_ai_status():
    """Получить статус AI провайдера"""
    return {
        "provider": AI_PROVIDER,
        "provider_name": "Groq (FREE)" if AI_PROVIDER == "groq" else "OpenAI",
        "has_key": bool(AI_API_KEY),
        "key_preview": f"{AI_API_KEY[:10]}..." if AI_API_KEY else None
    }


@app.post("/api/v1/groups/{group_id}/start-chat", response_class=JSONResponse)
async def start_group_chat(group_id: str, request: StartChatRequest = None):
    """
    Запустить общение в группе через AI (Groq FREE или OpenAI).
    Каждый участник отправляет сообщения.
    """
    try:
        from telethon import TelegramClient
        from openai_chat import get_chat_manager, PERSONALITIES
        import random
        
        if request is None:
            request = StartChatRequest(group_id=group_id)
        
        # Загрузить группы
        if not GROUPS_FILE.exists():
            raise HTTPException(status_code=404, detail="Файл групп не найден")
        
        with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
            groups_data = json.load(f)
        
        if isinstance(groups_data, list):
            groups_data = {"groups": groups_data}
        
        # Найти группу
        group = None
        for g in groups_data.get("groups", []):
            if g["id"] == group_id:
                group = g
                break
        
        if not group:
            raise HTTPException(status_code=404, detail=f"Группа {group_id} не найдена")
        
        telegram_group_id = group.get("telegram_group_id")
        # Если Telegram группа не создана, будем отправлять в личные сообщения между участниками
        use_personal_chat = not telegram_group_id
        
        # Инициализировать ChatManager с темами (Groq бесплатный!)
        chat_manager = get_chat_manager(AI_API_KEY, AI_PROVIDER)
        chat_manager.set_topics_file(str(TOPICS_FILE))
        
        # Загрузить тему
        topic = chat_manager.topic_manager.get_topic(request.topic_id)
        if not topic:
            topic = chat_manager.topic_manager.get_topic("travel")
        
        print(f"Запуск чата на тему: {topic.get('name', 'Общение')}")
        
        # Собрать всех участников
        all_members = [group["admin"]] + group["members"]
        
        # Назначить личности
        member_personalities = {}
        for i, member in enumerate(all_members):
            member_personalities[member["phone"]] = {
                "personality": PERSONALITIES[i % len(PERSONALITIES)],
                "name": member.get("first_name", f"User{i+1}")
            }
        
        messages_sent = []
        
        # Каждый участник отправляет сообщения
        for round_num in range(request.messages_per_member):
            # Перемешать порядок участников
            shuffled_members = all_members.copy()
            random.shuffle(shuffled_members)
            
            for member in shuffled_members:
                phone = member["phone"]
                session_file = SESSIONS_DIR / phone / f"{phone}.session"
                
                if not session_file.exists():
                    print(f"Session не найден: {phone}")
                    continue
                
                app_id = member.get("app_id") or 2040
                app_hash = member.get("app_hash") or "b18441a1ff607e10a989891a5462e627"
                
                personality_data = member_personalities[phone]
                
                # Генерировать сообщение
                context = chat_manager.get_context(group_id)
                is_first = len(context) == 0
                
                message = await chat_manager.generate_message(
                    group_id=group_id,
                    sender_name=personality_data["name"],
                    sender_personality=personality_data["personality"],
                    topic=topic,
                    context=context,
                    is_first_message=is_first
                )
                
                # Отправить сообщение в Telegram
                try:
                    client = TelegramClient(str(session_file), int(app_id), app_hash)
                    await client.connect()
                    
                    if await client.is_user_authorized():
                        if use_personal_chat:
                            # Отправить в личный чат случайному участнику
                            other_members = [m for m in all_members if m["phone"] != phone]
                            if other_members:
                                target = random.choice(other_members)
                                try:
                                    # Typing эффект
                                    typing_time = random.uniform(2, 5)
                                    target_entity = await client.get_entity(target["phone"])
                                    async with client.action(target_entity, 'typing'):
                                        await asyncio.sleep(typing_time)
                                    await client.send_message(target_entity, message)
                                except:
                                    pass
                        else:
                            # Показать "typing..." перед отправкой (реалистичнее!)
                            typing_duration = random.uniform(2, 5)  # 2-5 секунд набора
                            async with client.action(telegram_group_id, 'typing'):
                                await asyncio.sleep(typing_duration)
                            # Отправить в группу
                            await client.send_message(telegram_group_id, message)
                        
                        # Сохранить в историю
                        chat_manager.add_to_history(group_id, personality_data["name"], message)
                        
                        messages_sent.append({
                            "sender": personality_data["name"],
                            "phone": phone,
                            "message": message,
                            "time": datetime.now().isoformat()
                        })
                        
                        print(f"[{personality_data['name']}]: {message}")
                    
                    await client.disconnect()
                
                except Exception as e:
                    print(f"Ошибка отправки от {phone}: {e}")
                
                # Пауза между сообщениями (имитация реального общения)
                await asyncio.sleep(random.uniform(2, 5))
        
        # Сохранить лог
        chat_logs[group_id] = messages_sent
        
        return {
            "status": "success",
            "message": f"Отправлено {len(messages_sent)} сообщений",
            "messages": messages_sent
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in start_group_chat: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/groups/chat-logs/{group_id}", response_class=JSONResponse)
async def get_chat_logs(group_id: str):
    """Получить логи чата группы"""
    return {
        "group_id": group_id,
        "messages": chat_logs.get(group_id, [])
    }


@app.post("/api/v1/auto-chat/start", response_class=JSONResponse)
async def start_auto_chat():
    """
    Запустить автоматический чат для ВСЕХ групп.
    Чат будет работать пока не остановишь.
    """
    global auto_chat_active
    
    try:
        from telethon import TelegramClient
        from openai_chat import get_chat_manager, PERSONALITIES
        import random
        
        # Загрузить группы
        if not GROUPS_FILE.exists():
            return {"status": "error", "message": "Нет групп"}
        
        with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
            groups_data = json.load(f)
        
        if isinstance(groups_data, list):
            groups_data = {"groups": groups_data}
        
        groups = groups_data.get("groups", [])
        if not groups:
            return {"status": "error", "message": "Нет групп"}
        
        # Пометить все группы как активные
        for g in groups:
            auto_chat_active[g["id"]] = True
        
        # Запустить фоновую задачу
        asyncio.create_task(run_auto_chat_loop(groups))
        
        return {
            "status": "success",
            "message": f"Авто-чат запущен для {len(groups)} групп",
            "groups": len(groups)
        }
    
    except Exception as e:
        import traceback
        print(f"Error starting auto chat: {e}")
        print(traceback.format_exc())
        return {"status": "error", "message": str(e)}


@app.post("/api/v1/auto-chat/stop", response_class=JSONResponse)
async def stop_auto_chat():
    """Остановить автоматический чат"""
    global auto_chat_active
    auto_chat_active = {}  # Очистить все
    return {"status": "success", "message": "Авто-чат остановлен"}


@app.get("/api/v1/auto-chat/status", response_class=JSONResponse)
async def get_auto_chat_status():
    """Получить статус авто-чата"""
    active_count = sum(1 for v in auto_chat_active.values() if v)
    return {
        "active": active_count > 0,
        "groups_count": active_count
    }


@app.post("/api/v1/groups/{group_id}/create-telegram", response_class=JSONResponse)
async def create_telegram_for_group(group_id: str):
    """Создать реальную Telegram группу для существующей группы"""
    from telethon import TelegramClient
    from telethon.tl.functions.messages import CreateChatRequest
    from telethon.tl.functions.contacts import ImportContactsRequest
    from telethon.tl.types import InputPhoneContact
    
    try:
        # Загрузить группы
        if not GROUPS_FILE.exists():
            raise HTTPException(status_code=404, detail="Группы не найдены")
        
        with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
            groups_data = json.load(f)
        
        if isinstance(groups_data, list):
            groups_data = {"groups": groups_data}
        
        # Найти группу
        group = None
        group_idx = None
        for i, g in enumerate(groups_data.get("groups", [])):
            if g["id"] == group_id:
                group = g
                group_idx = i
                break
        
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена")
        
        if group.get("telegram_group_id"):
            return {"status": "exists", "message": "TG группа уже создана", "telegram_group_id": group["telegram_group_id"]}
        
        add_log(f"Создаю TG группу: {group['title']}", "info")
        
        admin = group["admin"]
        admin_phone = admin["phone"]
        admin_session = SESSIONS_DIR / admin_phone / f"{admin_phone}.session"
        
        if not admin_session.exists():
            raise HTTPException(status_code=400, detail=f"Session админа не найден: {admin_phone}")
        
        app_id = admin.get("app_id") or int(os.getenv('TELEGRAM_API_ID', 2040))
        app_hash = admin.get("app_hash") or os.getenv('TELEGRAM_API_HASH', "b18441a1ff607e10a989891a5462e627")
        
        client = TelegramClient(str(admin_session), app_id, app_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            raise HTTPException(status_code=400, detail="Админ не авторизован")
        
        add_log(f"Админ подключен: {admin_phone}", "success")
        
        # Добавить контакты
        contacts_to_add = []
        for i, member in enumerate(group["members"]):
            member_phone = member["phone"]
            contacts_to_add.append(InputPhoneContact(
                client_id=i,
                phone=f"+{member_phone}",
                first_name=member.get("first_name", f"User{i}"),
                last_name=member.get("last_name", "")
            ))
        
        if contacts_to_add:
            add_log(f"Импортирую {len(contacts_to_add)} контактов...", "info")
            try:
                result = await client(ImportContactsRequest(contacts_to_add))
                add_log(f"Импортировано: {len(result.users)} пользователей", "success")
                await asyncio.sleep(2)
            except Exception as e:
                add_log(f"Ошибка импорта: {str(e)[:40]}", "warning")
        
        # Получить entities
        member_entities = []
        for member in group["members"]:
            try:
                entity = await client.get_entity(f"+{member['phone']}")
                member_entities.append(entity)
                add_log(f"Найден: {member['phone']}", "success")
            except Exception as e:
                add_log(f"Не найден: {member['phone']}", "warning")
        
        if not member_entities:
            await client.disconnect()
            raise HTTPException(status_code=400, detail="Не удалось найти ни одного участника")
        
        # Создать группу
        add_log(f"Создаю группу с {len(member_entities)} участниками...", "info")
        result = await client(CreateChatRequest(
            users=member_entities,
            title=group["title"]
        ))
        
        # Получить ID группы
        tg_id = None
        try:
            if hasattr(result, 'chats') and result.chats:
                tg_id = result.chats[0].id
            elif hasattr(result, 'chat'):
                tg_id = result.chat.id
            elif hasattr(result, 'chat_id'):
                tg_id = result.chat_id
            
            # Если не нашли - ищем в диалогах
            if not tg_id:
                await asyncio.sleep(1)
                dialogs = await client.get_dialogs(limit=10)
                for d in dialogs:
                    if d.title == group["title"]:
                        tg_id = d.id
                        break
        except Exception as e:
            add_log(f"Ошибка получения ID: {str(e)[:30]}", "warning")
        
        await client.disconnect()
        
        if tg_id:
            # Обновить группу
            groups_data["groups"][group_idx]["telegram_group_id"] = tg_id
            groups_data["groups"][group_idx]["status"] = "created"
            
            with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
                json.dump(groups_data, f, indent=2, ensure_ascii=False)
            
            add_log(f"ГРУППА СОЗДАНА! ID: {tg_id}", "success")
            return {"status": "success", "message": f"TG группа создана! ID: {tg_id}", "telegram_group_id": tg_id}
        else:
            raise HTTPException(status_code=500, detail="Не удалось получить ID группы")
    
    except HTTPException:
        raise
    except Exception as e:
        add_log(f"Ошибка: {str(e)[:50]}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/live-logs", response_class=JSONResponse)
async def get_live_logs():
    """Получить последние логи в реальном времени"""
    return {
        "logs": live_logs[-50:],  # Последние 50
        "progress": progress_status
    }


def add_log(message: str, log_type: str = "info"):
    """Добавить сообщение в лог"""
    global live_logs
    from datetime import datetime
    live_logs.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "type": log_type,
        "message": message
    })
    # Ограничить 100 сообщениями
    if len(live_logs) > 100:
        live_logs = live_logs[-100:]
    # Убрать эмодзи для Windows консоли
    safe_msg = message.encode('ascii', 'replace').decode('ascii')
    print(f"[{log_type.upper()}] {safe_msg}")


async def run_auto_chat_loop(groups):
    """Фоновый цикл автоматического чата - ЖИВОЕ ОБЩЕНИЕ!"""
    global progress_status
    from telethon import TelegramClient
    import random
    
    add_log("=== АВТО-ЧАТ ЗАПУЩЕН ===", "success")
    add_log(f"Активных групп: {len(groups)}", "info")
    
    # Новые темы для вброса когда разговор затухает
    NEW_TOPICS = [
        "кстати а чо думаете про...",
        "о слушайте вспомнил прикол один",
        "народ а вот вопрос есть",
        "бля совсем забыл сказать",
        "кста кто шарит в этом подскажите",
        "ребзя а вы знали что...",
        "ой пока молчал вспомнил историю",
        "лан давайте о другом поговорим",
        "а вот интересно ваше мнение",
        "слыш а ты помнишь как мы...",
    ]
    
    # Короткие реакции (быстрые ответы)
    SHORT_REPLIES = [
        "да", "не", "ага", "ну", "хз", "пон", "ясн", "норм", "ок", "лан",
        "ваще", "прям", "точн", "база", "факт", "плюс", "жиза", "кек",
        "++", ")", "))", ")))", "хах", "ахах", "лол", "😂", "🔥", "👍",
    ]
    
    # Средние сообщения
    MEDIUM_MSGS = [
        "да не ну это понятно конечно",
        "согласен полностью с тобой тут",
        "хм интересная мысль кстати да",
        "ну такое себе если честно",
        "а вот тут не соглашусь)",
        "прикольно звучит надо попробовать",
        "я бы тоже так сделал наверн",
        "ну да логично получается в итоге",
    ]
    
    # Длинные сообщения (развёрнутые мысли)
    LONG_MSGS = [
        "слушай ну вот я тут подумал и пришел к выводу что на самом деле все не так просто как кажется на первый взгляд, тут много нюансов которые надо учитывать",
        "да бля я вот сам через это проходил и скажу честно - это был тот ещё опыт, многому научился но не хотел бы повторять если честно",
        "короче смотри тут такая тема - с одной стороны ты прав конечно, но с другой есть моменты о которых ты не подумал видимо",
        "ну вот смотри я тебе сейчас расскажу как было у меня и ты сам поймешь почему я так думаю, это прям показательная история",
    ]
    
    msg_count = 0
    topic_energy = 10  # Энергия темы (падает со временем, при 0 - новая тема)
    last_sender = None  # Чтобы не один человек спамил
    
    while any(auto_chat_active.values()):
        for i, group in enumerate(groups):
            group_id = group["id"]
            
            if not auto_chat_active.get(group_id, False):
                continue
            
            progress_status = {
                "active": True,
                "current": i + 1,
                "total": len(groups),
                "message": f"Группа: {group.get('title', 'unknown')}"
            }
            
            try:
                telegram_group_id = group.get("telegram_group_id")
                
                if not telegram_group_id:
                    add_log(f"[{group['title']}] Нет TG группы - пропуск", "warning")
                    continue
                
                all_members = [group["admin"]] + group["members"]
                
                # === ЖИВОЕ ОБЩЕНИЕ: 5-15 сообщений за раунд ===
                messages_this_round = random.randint(5, 15)
                add_log(f"[{group['title']}] === РАУНД: {messages_this_round} сообщений ===", "info")
                
                for msg_num in range(messages_this_round):
                    if not auto_chat_active.get(group_id, False):
                        break
                    
                    # Выбрать отправителя (не того же что и прошлый раз!)
                    available_senders = [m for m in all_members if m.get("phone") != last_sender]
                    if not available_senders:
                        available_senders = all_members
                    sender = random.choice(available_senders)
                    last_sender = sender.get("phone")
                    
                    phone = sender["phone"]
                    session_file = SESSIONS_DIR / phone / f"{phone}.session"
                    
                    if not session_file.exists():
                        continue
                    
                    app_id = sender.get("app_id") or 2040
                    app_hash = sender.get("app_hash") or "b18441a1ff607e10a989891a5462e627"
                    sender_name = sender.get("first_name", phone[-4:])
                    
                    # === ВЫБОР РАЗМЕРА СООБЩЕНИЯ ===
                    topic_energy -= 1
                    
                    # Когда тема затухает - пауза и новая тема!
                    if topic_energy <= 0:
                        add_log(f"[{group['title']}] Тема затухла... пауза 30 сек", "warning")
                        await asyncio.sleep(30)
                        message = random.choice(NEW_TOPICS)
                        topic_energy = random.randint(8, 15)  # Новая энергия
                        add_log(f"[{group['title']}] Новая тема вброшена!", "success")
                    else:
                        # Выбор типа сообщения по энергии и случайности
                        msg_type = random.choices(
                            ["short", "medium", "long", "ai"],
                            weights=[30, 25, 15, 30],  # 30% коротких, 30% AI
                            k=1
                        )[0]
                        
                        if msg_type == "short":
                            message = random.choice(SHORT_REPLIES)
                        elif msg_type == "medium":
                            message = random.choice(MEDIUM_MSGS)
                        elif msg_type == "long":
                            message = random.choice(LONG_MSGS)
                        else:
                            # AI сообщение
                            try:
                                from openai_chat import get_chat_manager, PERSONALITIES
                                chat_manager = get_chat_manager(AI_API_KEY, AI_PROVIDER)
                                personality = random.choice(PERSONALITIES)
                                context = chat_manager.get_context(group_id)
                                topic = group.get("assigned_topic", {})
                                
                                message = await chat_manager.generate_message(
                                    group_id=group_id,
                                    sender_name=sender_name,
                                    sender_personality=personality,
                                    topic=topic,
                                    context=context,
                                    is_first_message=len(context) == 0
                                )
                            except Exception as e:
                                message = random.choice(MEDIUM_MSGS)
                    
                    # === ОТПРАВКА В TELEGRAM ===
                    try:
                        client = TelegramClient(str(session_file), int(app_id), app_hash)
                        await client.connect()
                        
                        if await client.is_user_authorized():
                            chat_id = int(telegram_group_id)
                            
                            # Выбор действия: сообщение/реакция/ответ
                            action = random.choices(
                                ["msg", "react", "reply"],
                                weights=[50, 25, 25],
                                k=1
                            )[0]
                            
                            recent_msgs = []
                            try:
                                async for m in client.iter_messages(chat_id, limit=8):
                                    if m.text and m.id:
                                        recent_msgs.append(m)
                            except:
                                pass
                            
                            if action == "react" and recent_msgs:
                                # === РЕАКЦИЯ ===
                                target = random.choice(recent_msgs[:5])
                                emoji = random.choice(["👍", "❤️", "🔥", "😂", "🤔", "👏", "💯"])
                                try:
                                    from telethon.tl.functions.messages import SendReactionRequest
                                    from telethon.tl.types import ReactionEmoji
                                    await client(SendReactionRequest(
                                        peer=chat_id,
                                        msg_id=target.id,
                                        reaction=[ReactionEmoji(emoticon=emoji)]
                                    ))
                                    add_log(f"[{group['title']}] {sender_name}: {emoji}", "success")
                                    msg_count += 1
                                except:
                                    action = "msg"
                            
                            if action == "reply" and recent_msgs:
                                # === ОТВЕТ НА СООБЩЕНИЕ ===
                                target = random.choice(recent_msgs[:5])
                                typing_time = len(message) / random.uniform(4, 8)
                                typing_time = max(1, min(typing_time, 20))
                                
                                async with client.action(chat_id, 'typing'):
                                    await asyncio.sleep(typing_time)
                                
                                await client.send_message(chat_id, message, reply_to=target.id)
                                add_log(f"[{group['title']}] {sender_name} ответил: {message[:40]}...", "success")
                                msg_count += 1
                                
                            elif action == "msg" or not recent_msgs:
                                # === ОБЫЧНОЕ СООБЩЕНИЕ ===
                                typing_time = len(message) / random.uniform(3, 7)
                                typing_time = max(1, min(typing_time, 25))
                                
                                add_log(f"[{group['title']}] {sender_name} печатает... ({typing_time:.0f}s)", "info")
                                async with client.action(chat_id, 'typing'):
                                    await asyncio.sleep(typing_time)
                                
                                await client.send_message(chat_id, message)
                                add_log(f"[{group['title']}] {sender_name}: {message[:50]}...", "success")
                                
                                # Сохранить в историю
                                try:
                                    from openai_chat import get_chat_manager
                                    chat_manager = get_chat_manager(AI_API_KEY, AI_PROVIDER)
                                    chat_manager.add_to_history(group_id, sender_name, message)
                                except:
                                    pass
                                
                                msg_count += 1
                        
                        await client.disconnect()
                        
                    except Exception as e:
                        add_log(f"TG ошибка: {str(e)[:40]}", "error")
                    
                    # === ПАУЗА МЕЖДУ СООБЩЕНИЯМИ (живой чат!) ===
                    if len(message) < 10:
                        # Короткие сообщения - быстрые паузы
                        wait = random.uniform(2, 8)
                    elif topic_energy > 7:
                        # Активная тема - быстро
                        wait = random.uniform(5, 15)
                    else:
                        # Тема затухает - медленнее
                        wait = random.uniform(15, 35)
                    
                    add_log(f"... пауза {wait:.0f}с ...", "info")
                    await asyncio.sleep(wait)
                
            except Exception as e:
                add_log(f"Ошибка: {str(e)[:50]}", "error")
        
        add_log(f"=== РАУНД ЗАВЕРШЁН: {msg_count} сообщений ===", "success")
        
        # Пауза между раундами (5-15 сек)
        round_pause = random.uniform(5, 15)
        add_log(f"Следующий раунд через {round_pause:.0f} сек...", "info")
        await asyncio.sleep(round_pause)
    
    progress_status = {"active": False, "current": 0, "total": 0, "message": ""}
    add_log("=== АВТО-ЧАТ ОСТАНОВЛЕН ===", "warning")


if __name__ == "__main__":
    import uvicorn
    import sys
    
    # Порт из переменной окружения или по умолчанию 8001
    port = int(os.getenv("PORT", "8001"))
    
    print(f"Starting Telegram Farm Control API on http://0.0.0.0:{port}")
    print(f"Open in browser: http://localhost:{port}")
    print(f"   Dashboard: http://localhost:{port}/dashboard")
    print(f"   Sessions: http://localhost:{port}/sessions")
    print(f"   Groups: http://localhost:{port}/groups")
    print(f"   Jobs: http://localhost:{port}/jobs")
    print("\nPress Ctrl+C to stop\n")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
