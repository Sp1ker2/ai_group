# Пример конфигурации для Yandex Cloud
# Скопируйте этот файл в terraform/ и адаптируйте под ваши нужды

terraform {
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = "~> 0.95"
    }
  }
}

provider "yandex" {
  token     = var.yandex_token
  cloud_id  = var.yandex_cloud_id
  folder_id = var.yandex_folder_id
  zone      = "ru-central1-a"
}

# VPC
resource "yandex_vpc_network" "main" {
  name = "${var.cluster_name}-network"
}

resource "yandex_vpc_subnet" "main" {
  name           = "${var.cluster_name}-subnet"
  zone           = "ru-central1-a"
  network_id     = yandex_vpc_network.main.id
  v4_cidr_blocks = ["10.0.0.0/24"]
}

# Kubernetes cluster
resource "yandex_kubernetes_cluster" "main" {
  name       = var.cluster_name
  network_id = yandex_vpc_network.main.id
  
  master {
    regional {
      region = "ru-central1"
      location {
        zone      = yandex_vpc_subnet.main.zone
        subnet_id = yandex_vpc_subnet.main.id
      }
    }
    
    version = "1.28"
  }
  
  service_account_id      = yandex_iam_service_account.cluster.id
  node_service_account_id = yandex_iam_service_account.nodes.id
}

# Node group
resource "yandex_kubernetes_node_group" "workers" {
  cluster_id = yandex_kubernetes_cluster.main.id
  name       = "workers"
  
  instance_template {
    platform_id = "standard-v2"
    resources {
      cores  = var.worker_cpu
      memory = var.worker_ram_gb * 1024
    }
    
    boot_disk {
      type = "network-ssd"
      size = var.worker_disk_gb
    }
    
    network_interface {
      nat        = true
      subnet_ids = [yandex_vpc_subnet.main.id]
    }
  }
  
  scale_policy {
    fixed_scale {
      size = var.worker_node_count
    }
  }
}

# Service accounts
resource "yandex_iam_service_account" "cluster" {
  name = "${var.cluster_name}-cluster-sa"
}

resource "yandex_iam_service_account" "nodes" {
  name = "${var.cluster_name}-nodes-sa"
}

# Outputs
output "kubeconfig" {
  value     = yandex_kubernetes_cluster.main.kubeconfig
  sensitive = true
}









