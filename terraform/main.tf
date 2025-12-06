terraform {
  required_version = ">= 1.0"
  
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.20"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.9"
    }
  }
  
  # Настройка backend для вашего провайдера
  # backend "s3" {
  #   bucket = "terraform-state"
  #   key    = "telegram-farm/terraform.tfstate"
  #   region = "ru-1"
  # }
}

# Переменные для конфигурации
variable "environment" {
  description = "Environment: pilot or production"
  type        = string
  default     = "pilot"
}

variable "region" {
  description = "Region (Moscow, SPB, etc.)"
  type        = string
  default     = "moscow"
}

variable "worker_node_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 3
}

variable "worker_instance_type" {
  description = "Worker node instance type"
  type        = string
  default     = "16vCPU-64GB"
}

variable "control_instance_type" {
  description = "Control node instance type"
  type        = string
  default     = "8vCPU-32GB"
}

# Provider configuration
# Адаптируйте под ваш провайдер (Selectel, TimeWeb, Yandex Cloud, etc.)
# provider "kubernetes" {
#   config_path = "~/.kube/config"
# }

# provider "helm" {
#   kubernetes {
#     config_path = "~/.kube/config"
#   }
# }

# Локальные значения
locals {
  namespace = "telegram-farm"
  
  common_labels = {
    app     = "telegram-farm"
    env     = var.environment
    managed = "terraform"
  }
  
  pilot_config = {
    worker_nodes = 3
    worker_cpu   = 16
    worker_ram   = 64
    worker_disk  = 500
  }
  
  prod_config = {
    worker_nodes = 40
    worker_cpu   = 4
    worker_ram   = 8
    worker_disk  = 200
  }
  
  config = var.environment == "pilot" ? local.pilot_config : local.prod_config
}

# Namespace
resource "kubernetes_namespace" "main" {
  metadata {
    name   = local.namespace
    labels = local.common_labels
  }
}

# Outputs
output "namespace" {
  value = kubernetes_namespace.main.metadata[0].name
}

output "kubeconfig_path" {
  value = "~/.kube/config"
  description = "Path to kubeconfig file"
}





