@echo off
chcp 65001 >nul
title Проверка установки
color 0A

echo.
echo ========================================
echo   Проверка установки зависимостей
echo ========================================
echo.

set PYTHON3=C:\Users\User\AppData\Local\Programs\Python\Python310\python.exe

echo [1/4] Проверка Python...
%PYTHON3% --version
if errorlevel 1 (
    echo [ERROR] Python не найден!
    pause
    exit /b 1
)
echo [OK] Python найден
echo.

echo [2/4] Проверка установленных пакетов...
%PYTHON3% -m pip list | findstr /i "fastapi uvicorn telethon jinja2 aiofiles"
echo.

echo [3/4] Установка/обновление зависимостей...
%PYTHON3% -m pip install --upgrade pip -q
%PYTHON3% -m pip install fastapi uvicorn jinja2 python-multipart aiofiles telethon -q
if errorlevel 1 (
    echo [ERROR] Не удалось установить зависимости
    pause
    exit /b 1
)
echo [OK] Зависимости установлены
echo.

echo [4/4] Проверка импортов...
%PYTHON3% -c "import fastapi; import uvicorn; import telethon; import jinja2; print('[OK] Все модули импортируются')"
if errorlevel 1 (
    echo [ERROR] Ошибка импорта модулей
    pause
    exit /b 1
)
echo.

echo ========================================
echo   ✅ ВСЕ ГОТОВО!
echo ========================================
echo.
echo Запустите API:
echo   RUN_UI.bat
echo.
pause




