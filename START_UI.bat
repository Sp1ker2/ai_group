@echo off
echo Starting Telegram Farm Control API...
echo.

cd docker\control-api

echo Installing dependencies...
pip install fastapi uvicorn jinja2 python-multipart aiofiles

echo.
echo Starting server...
echo.
echo ========================================
echo   UI доступен по адресу:
echo   http://localhost:8000
echo ========================================
echo.
echo Нажмите Ctrl+C для остановки
echo.

python main.py




