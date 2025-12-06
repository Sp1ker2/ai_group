# Terraform Infrastructure

Terraform модули для создания инфраструктуры Kubernetes-кластера.

## Использование

### 1. Настройка провайдера

Отредактируйте `main.tf` и добавьте конфигурацию вашего провайдера:

```hcl
provider "selectel" {
  token = var.selectel_token
}

provider "kubernetes" {
  host = selectel_vpc_k8s_cluster_v1.main.api_endpoint
  # ...
}
```

### 2. Создание файла переменных

Создайте `terraform.tfvars`:

```hcl
environment        = "pilot"
region             = "moscow"
worker_node_count  = 3
worker_cpu         = 16
worker_ram_gb      = 64
worker_disk_gb     = 500
public_ip_count    = 3

management_ips = [
  "1.2.3.4/32",  # Ваш офисный IP
]

ssh_public_keys = [
  "ssh-rsa AAAAB3NzaC1yc2E... user@example.com"
]

s3_bucket_name = "telegram-farm-storage"
```

### 3. Инициализация и применение

```bash
terraform init
terraform plan
terraform apply
```

## Переменные

См. `variables.tf` для полного списка переменных.

## Outputs

После применения Terraform выведет:
- Имя кластера
- Namespace
- Количество worker nodes
- Public IPs
- Инструкции по следующим шагам






