# Пример конфигурации для Selectel
# Скопируйте этот файл в terraform/ и адаптируйте под ваши нужды

terraform {
  required_providers {
    selectel = {
      source  = "selectel/selectel"
      version = "~> 4.0"
    }
  }
}

provider "selectel" {
  token = var.selectel_token
}

# VPC
resource "selectel_vpc_project_v2" "main" {
  name = "${var.cluster_name}-project"
}

# Kubernetes cluster
resource "selectel_vpc_k8s_cluster_v1" "main" {
  name       = var.cluster_name
  region     = var.region
  k8s_version = "1.28"
  project_id = selectel_vpc_project_v2.main.id
  
  maintenance_window_start = "03:00:00"
}

# Node group для worker nodes
resource "selectel_vpc_k8s_nodegroup_v1" "workers" {
  cluster_id = selectel_vpc_k8s_cluster_v1.main.id
  name       = "workers"
  node_count = var.worker_node_count
  
  flavor_id = "g1-standard-16-64"  # 16 vCPU, 64 GB
  
  volume {
    size = var.worker_disk_gb
    type = "fast-ssd"
  }
  
  autoscaling {
    min_nodes = var.worker_node_count
    max_nodes = var.worker_node_count * 2
  }
}

# Floating IPs для worker nodes
resource "selectel_vpc_floatingip_v2" "workers" {
  count      = var.public_ip_count
  project_id = selectel_vpc_project_v2.main.id
  region     = var.region
}

# Outputs
output "kubeconfig" {
  value     = selectel_vpc_k8s_cluster_v1.main.kubeconfig
  sensitive = true
}

output "cluster_id" {
  value = selectel_vpc_k8s_cluster_v1.main.id
}

