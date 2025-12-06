variable "cluster_name" {
  description = "Name of the Kubernetes cluster"
  type        = string
  default     = "telegram-farm-cluster"
}

variable "environment" {
  description = "Environment name (pilot, production)"
  type        = string
  default     = "pilot"
  
  validation {
    condition     = contains(["pilot", "production"], var.environment)
    error_message = "Environment must be 'pilot' or 'production'."
  }
}

variable "region" {
  description = "Cloud region"
  type        = string
  default     = "moscow"
}

variable "worker_node_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 3
}

variable "worker_cpu" {
  description = "CPU cores per worker node"
  type        = number
  default     = 16
}

variable "worker_ram_gb" {
  description = "RAM in GB per worker node"
  type        = number
  default     = 64
}

variable "worker_disk_gb" {
  description = "Disk size in GB per worker node"
  type        = number
  default     = 500
}

variable "public_ip_count" {
  description = "Number of public IPs needed"
  type        = number
  default     = 3
}

variable "management_ips" {
  description = "CIDR blocks for management access"
  type        = list(string)
  default     = []
}

variable "ssh_public_keys" {
  description = "SSH public keys for access"
  type        = list(string)
  default     = []
}

variable "s3_bucket_name" {
  description = "S3 bucket name for storage"
  type        = string
  default     = "telegram-farm-storage"
}

variable "enable_monitoring" {
  description = "Enable monitoring stack"
  type        = bool
  default     = true
}

variable "enable_backups" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}






