# Структура проекта

```
bip/
├── README.md                    # Основной README
├── PROJECT_STRUCTURE.md         # Этот файл
├── Makefile                     # Команды для управления проектом
├── docker-compose.yml           # Локальная разработка
├── .gitignore                   # Git ignore правила
│
├── terraform/                   # Terraform модули
│   ├── main.tf                  # Основная конфигурация
│   ├── variables.tf             # Переменные
│   ├── outputs.tf               # Outputs
│   ├── README.md                # Документация Terraform
│   └── providers/              # Примеры для провайдеров
│       ├── example-selectel.tf  # Selectel
│       └── example-yandex.tf    # Yandex Cloud
│
├── helm/                        # Helm charts
│   ├── control-node/            # Control Node chart
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       ├── deployment.yaml
│   │       ├── service.yaml
│   │       ├── ingress.yaml
│   │       ├── hpa.yaml
│   │       ├── serviceaccount.yaml
│   │       └── _helpers.tpl
│   └── wg-proxy/                # WireGuard Proxy chart
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│           ├── daemonset.yaml
│           ├── serviceaccount.yaml
│           └── _helpers.tpl
│
├── k8s/                         # Raw Kubernetes manifests
│   ├── namespace.yaml           # Namespace
│   ├── android-worker/          # Android Worker Jobs
│   │   ├── job-template.yaml    # Шаблон Job
│   │   └── job-example.yaml     # Пример Job
│   ├── wg-proxy/                # WireGuard Proxy
│   │   ├── daemonset.yaml
│   │   ├── serviceaccount.yaml
│   │   └── configmap.yaml
│   ├── redis/                   # Redis
│   │   ├── statefulset.yaml
│   │   ├── service.yaml
│   │   └── configmap.yaml
│   ├── postgres/                # Postgres
│   │   ├── statefulset.yaml
│   │   └── service.yaml
│   └── secrets/                 # Secrets документация
│       └── README.md
│
├── docker/                      # Docker образы
│   └── android-worker/          # Android Worker образ
│       ├── Dockerfile
│       ├── worker.py            # Python worker скрипт
│       ├── requirements.txt    # Python зависимости
│       └── .dockerignore
│
├── scripts/                     # Скрипты развертывания
│   ├── deploy.sh               # Основной скрипт развертывания
│   ├── smoke-test.sh           # Smoke тесты
│   └── create-secrets.sh       # Создание secrets
│
└── docs/                        # Документация
    ├── DEPLOYMENT.md            # Детальное руководство по развертыванию
    ├── ARCHITECTURE.md          # Архитектура системы
    ├── QUICKSTART.md            # Быстрый старт
    └── CLOUD_REQUEST_TEMPLATE.md # Шаблоны запросов в облако
```

## Описание компонентов

### Terraform
Инфраструктура как код. Создает Kubernetes кластер, сети, IP адреса.

### Helm Charts
Готовые пакеты для развертывания:
- **control-node**: API и UI для управления
- **wg-proxy**: WireGuard туннелирование

### K8s Manifests
Raw манифесты для прямого развертывания через kubectl.

### Docker
Образы контейнеров:
- **android-worker**: Worker для выполнения Telegram задач

### Scripts
Автоматизация развертывания и тестирования.

### Docs
Полная документация по развертыванию и использованию.

## Использование

1. **Быстрый старт**: См. `docs/QUICKSTART.md`
2. **Полное развертывание**: См. `docs/DEPLOYMENT.md`
3. **Архитектура**: См. `docs/ARCHITECTURE.md`
4. **Запрос в облако**: См. `docs/CLOUD_REQUEST_TEMPLATE.md`

## Команды

Используйте `make help` для списка всех доступных команд.





