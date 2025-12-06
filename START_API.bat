@echo off
chcp 65001 >nul
title Telegram Farm API
color 0A

echo.
echo ========================================
echo   Запуск Telegram Farm Control API
echo ========================================
echo.

cd /d %~dp0docker\control-api

set PYTHON3=C:\Users\User\AppData\Local\Programs\Python\Python310\python.exe

echo Используется: %PYTHON3%
%PYTHON3% --version
echo.

echo Проверка порта 8001...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001 ^| findstr LISTENING') do (
    echo Порт 8001 занят процессом %%a. Остановка...
    taskkill /PID %%a /F >nul 2>&1
    timeout /t 1 /nobreak >nul
)

echo Запуск API на порту 8001...
echo.
echo ========================================
echo   Откройте в браузере:
echo   http://localhost:8001
echo ========================================
echo.
echo Нажмите Ctrl+C для остановки
echo.

%PYTHON3% main.py

pause

