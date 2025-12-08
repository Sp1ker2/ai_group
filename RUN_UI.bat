@echo off
chcp 65001 >nul
title Telegram Farm UI
color 0A

echo.
echo ========================================
echo   Запуск Telegram Farm Control UI
echo ========================================
echo.

cd /d %~dp0docker\control-api

REM Использовать Python 3 явно
set PYTHON3=C:\Users\User\AppData\Local\Programs\Python\Python310\python.exe
if not exist "%PYTHON3%" (
    echo Поиск Python 3...
    where python3 >nul 2>&1
    if %errorlevel%==0 (
        set PYTHON3=python3
    ) else (
        where py >nul 2>&1
        if %errorlevel%==0 (
            set PYTHON3=py -3
        ) else (
            echo ERROR: Python 3 не найден!
            echo Установите Python 3.8+ с python.org
            pause
            exit /b 1
        )
    )
)

echo Используется: %PYTHON3%
%PYTHON3% --version
echo.

echo Установка зависимостей...
%PYTHON3% -m pip install --quiet --upgrade pip
%PYTHON3% -m pip install fastapi uvicorn jinja2 python-multipart aiofiles
if errorlevel 1 (
    echo ERROR: Не удалось установить зависимости
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Запуск API на порту 8001
echo ========================================
echo.
echo Откройте в браузере:
echo   http://localhost:8001
echo.
echo Нажмите Ctrl+C для остановки
echo.
echo ========================================
echo.

%PYTHON3% main.py

pause





