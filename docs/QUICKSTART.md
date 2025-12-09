# Быстрый старт

Минимальная инструкция для быстрого развертывания.

## Предварительные требования

- Kubernetes кластер (версия >= 1.24)
- `kubectl` настроен и подключен
- `helm` (опционально, но рекомендуется)
- Доступ к Docker registry

## Шаг 1: Клонирование и подготовка

```bash
# Если еще не склонировали
git clone <repository>
cd bip

# Проверка подключения к кластеру
kubectl cluster-info
```

## Шаг 2: Создание Secrets

```bash
# Интерактивный скрипт
chmod +x scripts/create-secrets.sh
./scripts/create-secrets.sh

# Или вручную (см. k8s/secrets/README.md)
```

## Шаг 3: Развертывание базовых компонентов

```bash
# Namespace
kubectl apply -f k8s/namespace.yaml

# Redis
kubectl apply -f k8s/redis/

# Postgres
kubectl apply -f k8s/postgres/

# Ожидание готовности
kubectl wait --for=condition=ready pod -l app=postgres -n telegram-farm --timeout=300s
```

## Шаг 4: WireGuard Proxy

```bash
# Обновите k8s/wg-proxy/configmap.yaml с реальными ключами
kubectl apply -f k8s/wg-proxy/
```

## Шаг 5: Control Node

**Вариант A: Helm (рекомендуется)**

```bash
helm install control-node ./helm/control-node -n telegram-farm
```

**Вариант B: kubectl**

```bash
# Если у вас есть готовые манифесты
kubectl apply -f k8s/control-node/
```

## Шаг 6: Проверка

```bash
# Статус всех компонентов
kubectl get all -n telegram-farm

# Проверка исходящего IP
make check-ip

# Или вручную
kubectl run test-ip -n telegram-farm --image=curlimages/curl --rm -it --restart=Never -- curl -s https://ifconfig.me
```

## Шаг 7: Тестовый Job

```bash
# Отредактируйте k8s/android-worker/job-example.yaml
# Замените PHONE_NUMBER, ACCOUNT_ID на реальные значения

kubectl apply -f k8s/android-worker/job-example.yaml

# Проверка логов
kubectl logs -f job/warmup-account-12345 -n telegram-farm
```

## Использование Makefile

```bash
# Показать все команды
make help

# Развернуть все
make deploy

# Собрать образ worker
make build-worker

# Запустить тесты
make test

# Показать статус
make status
```

## Troubleshooting

### Pods не запускаются

```bash
kubectl describe pod <pod-name> -n telegram-farm
kubectl logs <pod-name> -n telegram-farm
```

### Проверка событий

```bash
kubectl get events -n telegram-farm --sort-by='.lastTimestamp'
```

### Проверка ресурсов

```bash
kubectl top nodes
kubectl top pods -n telegram-farm
```

## Следующие шаги

1. Настройте мониторинг (Prometheus + Grafana)
2. Настройте бэкапы
3. Настройте автоматическое масштабирование
4. Настройте CI/CD для обновлений

См. [DEPLOYMENT.md](DEPLOYMENT.md) для детальной информации.









