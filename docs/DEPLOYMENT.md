# Руководство по развертыванию

Полное руководство по развертыванию Telegram Farm в Kubernetes.

## Предварительные требования

1. **Kubernetes кластер** (версия >= 1.24)
2. **kubectl** настроен и подключен к кластеру
3. **Helm** (версия >= 3.8) - опционально
4. **Docker** для сборки образов
5. **Доступ к приватному registry** (или публичный Docker Hub)

## Этап 1: Подготовка инфраструктуры

### 1.1 Terraform (если используете)

```bash
cd terraform
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply
```

### 1.2 Проверка кластера

```bash
kubectl cluster-info
kubectl get nodes
```

## Этап 2: Создание Secrets

Перед развертыванием создайте необходимые secrets:

```bash
# Postgres
kubectl create secret generic postgres-secrets \
  --from-literal=username=telegram_farm \
  --from-literal=password='YOUR_SECURE_PASSWORD' \
  -n telegram-farm

# Control Node
kubectl create secret generic control-node-secrets \
  --from-literal=database-url='postgresql://user:pass@postgres:5432/telegram_farm' \
  --from-literal=redis-url='redis://redis:6379' \
  --from-literal=secret-key='YOUR_SECRET_KEY' \
  -n telegram-farm

# Android Worker
kubectl create secret generic android-worker-secrets \
  --from-literal=api-token='YOUR_API_TOKEN' \
  -n telegram-farm
```

## Этап 3: Развертывание компонентов

### 3.1 Namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

### 3.2 Redis

```bash
kubectl apply -f k8s/redis/
```

### 3.3 Postgres

```bash
kubectl apply -f k8s/postgres/
```

Дождитесь готовности:

```bash
kubectl wait --for=condition=ready pod -l app=postgres -n telegram-farm --timeout=300s
```

### 3.4 WireGuard Proxy (DaemonSet)

```bash
# Обновите k8s/wg-proxy/configmap.yaml с реальными ключами
kubectl apply -f k8s/wg-proxy/
```

### 3.5 Control Node

**Вариант A: Через Helm**

```bash
helm install control-node ./helm/control-node -n telegram-farm
```

**Вариант B: Через kubectl**

```bash
# Если у вас есть готовые манифесты
kubectl apply -f k8s/control-node/
```

### 3.6 Ingress и Cert-Manager

```bash
# Установка cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Установка ingress-nginx
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace
```

## Этап 4: Сборка и загрузка образов

### 4.1 Android Worker

```bash
cd docker/android-worker
docker build -t registry.telegram-farm.local/android-worker:latest .
docker push registry.telegram-farm.local/android-worker:latest
```

### 4.2 Control API (если есть)

```bash
# Соберите и загрузите образ Control API
```

## Этап 5: Проверка развертывания

### 5.1 Статус компонентов

```bash
kubectl get pods -n telegram-farm
kubectl get services -n telegram-farm
kubectl get ingress -n telegram-farm
```

### 5.2 Проверка исходящего IP

```bash
# Запустите тестовый pod
kubectl run test-ip -n telegram-farm --image=curlimages/curl --rm -it -- sh
# Внутри pod:
curl https://ifconfig.me
# Должен вернуть российский IP
```

### 5.3 Smoke тесты

```bash
chmod +x scripts/smoke-test.sh
./scripts/smoke-test.sh
```

## Этап 6: Запуск тестового Job

```bash
# Отредактируйте k8s/android-worker/job-example.yaml
kubectl apply -f k8s/android-worker/job-example.yaml

# Проверка логов
kubectl logs -f job/warmup-account-12345 -n telegram-farm
```

## Мониторинг

### Prometheus + Grafana

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
```

### Логи

```bash
# Просмотр логов
kubectl logs -f deployment/control-node -n telegram-farm
kubectl logs -f daemonset/wg-proxy -n telegram-farm
```

## Масштабирование

### Горизонтальное масштабирование Control Node

```bash
kubectl scale deployment control-node -n telegram-farm --replicas=5
```

### Автомасштабирование (HPA)

HPA уже настроен в Helm chart. Проверьте:

```bash
kubectl get hpa -n telegram-farm
```

## Резервное копирование

### Postgres

```bash
# Создайте CronJob для бэкапов
kubectl apply -f k8s/backups/postgres-backup.yaml
```

### Sessions (S3)

Настройте автоматическую синхронизацию `/data/sessions` в S3.

## Troubleshooting

### Проблема: Pods не запускаются

```bash
kubectl describe pod <pod-name> -n telegram-farm
kubectl logs <pod-name> -n telegram-farm
```

### Проблема: WireGuard не работает

```bash
kubectl logs -f daemonset/wg-proxy -n telegram-farm
kubectl exec -it <wg-proxy-pod> -n telegram-farm -- wg show
```

### Проблема: Jobs падают

```bash
kubectl describe job <job-name> -n telegram-farm
kubectl logs job/<job-name> -n telegram-farm
```

## Обновление

### Обновление Control Node

```bash
helm upgrade control-node ./helm/control-node -n telegram-farm
```

### Обновление Android Worker

```bash
# Пересоберите образ
docker build -t registry.telegram-farm.local/android-worker:v2 .
docker push registry.telegram-farm.local/android-worker:v2

# Обновите image в Job template
```

## Безопасность

1. **Secrets**: Используйте Sealed Secrets или External Secrets Operator
2. **RBAC**: Настройте правильные права доступа
3. **Network Policies**: Ограничьте сетевой трафик
4. **Pod Security**: Используйте Pod Security Standards

## Поддержка

При возникновении проблем:
1. Проверьте логи компонентов
2. Проверьте статус ресурсов: `kubectl get all -n telegram-farm`
3. Проверьте события: `kubectl get events -n telegram-farm --sort-by='.lastTimestamp'`

