# PowerShell скрипт для тестирования всех компонентов

Write-Host "🧪 Тестирование всех компонентов Telegram Farm..." -ForegroundColor Cyan
Write-Host ""

$allPassed = $true

# Функция проверки
function Test-Service {
    param(
        [string]$Name,
        [scriptblock]$TestCommand
    )
    
    Write-Host -NoNewline "Проверка $Name... "
    try {
        $result = & $TestCommand
        if ($LASTEXITCODE -eq 0 -or $result) {
            Write-Host "✓ OK" -ForegroundColor Green
            return $true
        } else {
            Write-Host "✗ FAILED" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "✗ FAILED" -ForegroundColor Red
        return $false
    }
}

# 1. Проверка Docker контейнеров
Write-Host "📦 Проверка Docker контейнеров:" -ForegroundColor Yellow
$allPassed = (Test-Service "Postgres" { docker exec bip-postgres-1 pg_isready -U telegram_farm 2>&1 | Out-Null }) -and $allPassed
$allPassed = (Test-Service "Redis" { docker exec bip-redis-1 redis-cli ping 2>&1 | Select-String "PONG" }) -and $allPassed
$allPassed = (Test-Service "MinIO" { docker exec bip-minio-1 curl -f http://localhost:9000/minio/health/live 2>&1 | Out-Null }) -and $allPassed

# 2. Проверка Control API
Write-Host ""
Write-Host "🌐 Проверка Control API:" -ForegroundColor Yellow
try {
    $health = Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing -ErrorAction Stop
    if ($health.Content -match "healthy") {
        Write-Host "  Health endpoint ✓ OK" -ForegroundColor Green
    } else {
        Write-Host "  Health endpoint ✗ FAILED" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host "  Health endpoint ✗ FAILED" -ForegroundColor Red
    $allPassed = $false
}

try {
    $status = Invoke-WebRequest -Uri http://localhost:8000/api/v1/status -UseBasicParsing -ErrorAction Stop
    if ($status.Content -match "running") {
        Write-Host "  Status endpoint ✓ OK" -ForegroundColor Green
    } else {
        Write-Host "  Status endpoint ✗ FAILED" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host "  Status endpoint ✗ FAILED" -ForegroundColor Red
    $allPassed = $false
}

try {
    $root = Invoke-WebRequest -Uri http://localhost:8000/ -UseBasicParsing -ErrorAction Stop
    if ($root.Content -match "message") {
        Write-Host "  Root endpoint ✓ OK" -ForegroundColor Green
    } else {
        Write-Host "  Root endpoint ✗ FAILED" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host "  Root endpoint ✗ FAILED" -ForegroundColor Red
    $allPassed = $false
}

# 3. Проверка Docker образов
Write-Host ""
Write-Host "🐳 Проверка Docker образов:" -ForegroundColor Yellow
$images = docker images --format "{{.Repository}}"
if ($images -match "telegram-farm/android-worker") {
    Write-Host "  Android Worker image ✓ OK" -ForegroundColor Green
} else {
    Write-Host "  Android Worker image ✗ NOT FOUND" -ForegroundColor Red
    $allPassed = $false
}

if ($images -match "bip-control-api") {
    Write-Host "  Control API image ✓ OK" -ForegroundColor Green
} else {
    Write-Host "  Control API image ✗ NOT FOUND" -ForegroundColor Red
    $allPassed = $false
}

# 4. Тест подключения к БД
Write-Host ""
Write-Host "💾 Тест подключения к базе данных:" -ForegroundColor Yellow
$dbTest = docker exec bip-postgres-1 psql -U telegram_farm -d telegram_farm -c "SELECT 1;" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Postgres connection ✓ OK" -ForegroundColor Green
} else {
    Write-Host "  Postgres connection ✗ FAILED" -ForegroundColor Red
    $allPassed = $false
}

# 5. Тест Redis
Write-Host ""
Write-Host "📮 Тест Redis:" -ForegroundColor Yellow
docker exec bip-redis-1 redis-cli set test_key "test_value" 2>&1 | Out-Null
$redisValue = docker exec bip-redis-1 redis-cli get test_key 2>&1
if ($redisValue -match "test_value") {
    Write-Host "  Redis read/write ✓ OK" -ForegroundColor Green
    docker exec bip-redis-1 redis-cli del test_key 2>&1 | Out-Null
} else {
    Write-Host "  Redis read/write ✗ FAILED" -ForegroundColor Red
    $allPassed = $false
}

# 6. Показ статуса контейнеров
Write-Host ""
Write-Host "📊 Статус контейнеров:" -ForegroundColor Yellow
docker-compose ps

Write-Host ""
if ($allPassed) {
    Write-Host "✅ Все проверки пройдены успешно!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Некоторые проверки не прошли" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Доступные сервисы:" -ForegroundColor Cyan
Write-Host "  - Control API: http://localhost:8000" -ForegroundColor White
Write-Host "  - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)" -ForegroundColor White
Write-Host "  - Postgres: localhost:5432" -ForegroundColor White
Write-Host "  - Redis: localhost:6379" -ForegroundColor White






