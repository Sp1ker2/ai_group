@echo off
chcp 65001 >nul
echo ========================================
echo   Запуск Telegram Farm Control API
echo ========================================
echo.

cd /d %~dp0docker\control-api

echo Проверка Python...
python --version
if errorlevel 1 (
    echo ОШИБКА: Python не найден!
    echo Установите Python 3.8+ с python.org
    pause
    exit /b 1
)

echo.
echo Проверка зависимостей...
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo Установка зависимостей...
    pip install fastapi uvicorn jinja2 python-multipart aiofiles
    if errorlevel 1 (
        echo ОШИБКА: Не удалось установить зависимости
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo   API запускается на порту 8001
echo ========================================
echo.
echo Откройте в браузере:
echo   http://localhost:8001
echo.
echo Нажмите Ctrl+C для остановки
echo.
echo ========================================
echo.

python main.py

pause



