@echo off
chcp 65001 >nul
title Telegram Farm Control API
color 0A

echo.
echo ========================================
echo   Telegram Farm Control API
echo ========================================
echo.

cd /d %~dp0docker\control-api

echo [1/3] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден!
    echo.
    echo Установите Python 3.8+ с https://www.python.org/
    echo.
    pause
    exit /b 1
)
python --version
echo [OK] Python найден
echo.

echo [2/3] Установка зависимостей...
python -m pip install --quiet --upgrade pip
python -m pip install fastapi uvicorn jinja2 python-multipart aiofiles
if errorlevel 1 (
    echo [ERROR] Не удалось установить зависимости
    echo.
    echo Попробуйте:
    echo   python -m pip install --upgrade pip
    echo   python -m pip install fastapi uvicorn jinja2 python-multipart aiofiles
    echo.
    pause
    exit /b 1
)
echo [OK] Зависимости установлены
echo.

echo [3/3] Запуск API...
echo.
echo ========================================
echo   API запускается на порту 8001
echo ========================================
echo.
echo Откройте в браузере:
echo   http://localhost:8001
echo.
echo Страницы:
echo   - Главная:    http://localhost:8001
echo   - Dashboard:  http://localhost:8001/dashboard
echo   - Sessions:   http://localhost:8001/sessions
echo   - Groups:     http://localhost:8001/groups
echo   - Jobs:       http://localhost:8001/jobs
echo.
echo Нажмите Ctrl+C для остановки
echo.
echo ========================================
echo.

python main.py

pause



