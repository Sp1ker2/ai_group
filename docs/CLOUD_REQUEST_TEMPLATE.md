# Шаблон запроса в облако

## Краткий запрос (для первого контакта)

```
Тема: Запрос ресурсов для Kubernetes-кластера (Russia only) — Pilot → Production

Добрый день!

Просьба подготовить предложение по развертыванию Kubernetes-кластера для пилотного проекта.

Pilot конфигурация:
- Managed Kubernetes или VM-based cluster
- 3 worker nodes: 16 vCPU, 64GB RAM, 500GB SSD, статический IPv4
- 1 control node: 8 vCPU, 32GB RAM, 200GB SSD
- LoadBalancer для публичного доступа
- S3-compatible storage
- VPC/private network

Production (ориентир):
- 40 worker nodes: 4 vCPU, 8-16GB RAM, 200GB SSD
- 2 control nodes
- 2 DB nodes (Postgres HA)
- 3 Redis nodes

Требования:
- Все ресурсы в регионах РФ (Москва, СПб приоритет)
- Статические публичные IPv4 (1 на worker node)
- Поддержка WireGuard/статических маршрутов
- Автомасштабирование (Cluster Autoscaler)
- Ежедневные бэкапы

Просьба предоставить:
- Коммерческое предложение
- Оценку сроков развертывания
- SLA
- Список доступных регионов в РФ

С уважением,
[Имя, контакты]
```

## Детальное письмо

См. оригинальный документ пользователя, раздел "# 2. Запрос в облако — детальное письмо (пример)".

## Чек-лист для провайдера

```
☐ Подготовить Kubernetes cluster (kubeconfig + admin user)
☐ Создать NodePools: control, worker-large, worker-small
☐ Выдать статические public IPv4 × N (Pilot/Prod)
☐ Настроить internal VPC / subnets
☐ Предоставить S3-compatible bucket + credentials
☐ Предоставить LoadBalancer + ingress
☐ Настроить security groups (SSH only from management IPs)
☐ Развернуть Helm, Cert-Manager (letsencrypt), Nginx ingress
☐ SLA и цены по каждому ресурсу
☐ Документация по доступу и управлению
```

## Acceptance Criteria

```
☐ kubeconfig успешно подключается
☐ Тестовый pod запускается и работает
☐ DaemonSet wg-proxy поднят на всех nodes
☐ Исходящий IP из pod = российский IP (проверка через curl https://ifconfig.me)
☐ 10 test Jobs успешно выполнились
☐ Latency: Job выполняется < 10 минут
☐ Prometheus собирает метрики
☐ Grafana dashboard доступен
☐ Ежедневный бэкап Postgres работает
☐ SSH доступ только с разрешённых IP
```






