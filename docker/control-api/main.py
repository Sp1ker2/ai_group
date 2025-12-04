"""
Минимальный Control API для локальной разработки
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os

app = FastAPI(title="Telegram Farm Control API", version="1.0.0")


@app.get("/")
async def root():
    return {"message": "Telegram Farm Control API", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/ready")
async def ready():
    return {"status": "ready"}


@app.get("/api/v1/status")
async def api_status():
    return {
        "api": "running",
        "database": "connected" if os.getenv("DATABASE_URL") else "not configured",
        "redis": "connected" if os.getenv("REDIS_URL") else "not configured"
    }


@app.post("/api/v1/jobs/report")
async def report_job(job_data: dict):
    """Эндпоинт для получения отчетов от worker'ов"""
    return {"status": "received", "job_id": job_data.get("account_id")}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

