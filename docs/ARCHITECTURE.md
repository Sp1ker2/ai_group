# Архитектура системы

## Общая схема

```
┌─────────────────┐
│   Operator      │  (Web UI)
│   (Browser)     │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐
│  Control Node   │  (API + UI)
│  (LoadBalancer) │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌──────┐  ┌──────┐
│Redis │  │Postgres│
│Queue │  │  DB   │
└──────┘  └──────┘
         │
         ▼
┌─────────────────┐
│ Kubernetes      │
│   Cluster       │
│  (RF regions)   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌──────────┐
│wg-proxy │ │  Worker  │
│DaemonSet│ │   Jobs   │
└────┬────┘ └────┬─────┘
     │          │
     └────┬─────┘
          │ WireGuard
          ▼
    ┌──────────┐
    │  VDS RF  │
    │  (IP)    │
    └────┬─────┘
         │
         ▼
┌─────────────────┐
│  Telegram API   │
│   (Servers)     │
└─────────────────┘
```

## Компоненты

### 1. Control Node

**Назначение**: Центральный узел управления

**Компоненты**:
- FastAPI/Django backend
- React frontend
- REST API для управления задачами
- WebSocket для real-time обновлений

**Ресурсы**:
- CPU: 2-8 vCPU
- RAM: 4-32 GB
- Replicas: 2+ (HA)

**Endpoints**:
- `/api/v1/jobs` - управление задачами
- `/api/v1/accounts` - управление аккаунтами
- `/api/v1/reports` - отчеты о выполнении

### 2. Queue (Redis)

**Назначение**: Очередь задач

**Конфигурация**:
- Режим: Cluster (3 nodes)
- Persistence: AOF
- Memory: 1-2 GB per node

### 3. Database (Postgres)

**Назначение**: Хранение данных

**Схема**:
- `accounts` - аккаунты Telegram
- `jobs` - задачи на выполнение
- `reports` - результаты выполнения
- `sessions` - метаданные сессий

**HA**: Primary + Replica

### 4. WireGuard Proxy (DaemonSet)

**Назначение**: Туннелирование трафика через российские IP

**Принцип работы**:
1. DaemonSet запускается на каждом worker node
2. Создает WireGuard интерфейс `wg0`
3. Настраивает маршрутизацию всего исходящего трафика через туннель
4. Туннель ведет на VDS в РФ с российским IP

**Требования**:
- `privileged: true`
- `NET_ADMIN` capability
- Доступ к `/lib/modules`

### 5. Android Worker (Jobs)

**Назначение**: Выполнение warm-up задач

**Жизненный цикл**:
1. Control Node создает Job через API
2. Job запускает Pod с android-worker контейнером
3. Контейнер:
   - Инициализирует Telegram клиент
   - Выполняет warm-up скрипт
   - Отправляет результаты в Control API
4. Job завершается, Pod удаляется (TTL)

**Ресурсы на Job**:
- CPU: 1-2 vCPU
- RAM: 2-4 GB
- Disk: 10 GB (ephemeral)

**Параллелизм**:
- Pilot: ~100 concurrent jobs
- Production: ~300-1000 concurrent jobs

## Сетевой поток

### Исходящий трафик

```
Pod (android-worker)
  ↓
Node Network Interface
  ↓
WireGuard Interface (wg0) [DaemonSet]
  ↓
WireGuard Tunnel
  ↓
VDS в РФ (российский IP)
  ↓
Telegram Servers
```

### Входящий трафик (Control Node)

```
Internet
  ↓
LoadBalancer (публичный IP)
  ↓
Ingress Controller
  ↓
Control Node Service
  ↓
Control Node Pods
```

## Масштабирование

### Горизонтальное

- **Control Node**: HPA по CPU/Memory
- **Worker Jobs**: Создаются по требованию
- **Redis**: Cluster mode (3+ nodes)
- **Postgres**: Read replicas для чтения

### Вертикальное

- Увеличение ресурсов worker nodes
- Увеличение ресурсов Control Node

## Безопасность

### Network Policies

```yaml
# Изоляция namespace
# Только Control Node может общаться с БД
# Worker Jobs не могут общаться друг с другом
```

### RBAC

- Операторы: только чтение
- Администраторы: полный доступ
- Service Accounts: минимальные права

### Secrets Management

- K8s Secrets (базовый уровень)
- Sealed Secrets (рекомендуется)
- External Secrets Operator (production)

## Мониторинг

### Метрики

- Prometheus собирает метрики со всех компонентов
- Grafana дашборды:
  - Job success rate
  - Average execution time
  - Resource utilization
  - Network throughput

### Логи

- Loki собирает логи всех Pods
- Хранение: 7 дней (hot), 30 дней (cold)

### Алерты

- Job failure rate > 5%
- Control Node недоступен
- Database connection errors
- WireGuard tunnel down

## Резервное копирование

### Postgres

- Ежедневные snapshots
- Point-in-time recovery (PITR)
- Репликация в другой регион

### Sessions

- Синхронизация в S3
- Versioning включен
- Lifecycle policy: 90 дней

### Конфигурация

- GitOps (ArgoCD/Flux)
- Версионирование всех манифестов

## Производительность

### Целевые показатели

- Job execution time: < 10 минут
- API response time: < 200ms (p95)
- Throughput: 1000+ jobs/hour
- Availability: 99.9%

### Оптимизация

- Connection pooling для БД
- Redis caching для частых запросов
- Batch processing для отчетов
- CDN для статических ресурсов UI





