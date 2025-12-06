output "cluster_name" {
  description = "Kubernetes cluster name"
  value       = var.cluster_name
}

output "namespace" {
  description = "Created namespace"
  value       = kubernetes_namespace.main.metadata[0].name
}

output "worker_node_count" {
  description = "Number of worker nodes"
  value       = var.worker_node_count
}

output "public_ips" {
  description = "Public IPs assigned to worker nodes"
  value       = [] # Заполняется провайдером
}

output "s3_bucket" {
  description = "S3 bucket name"
  value       = var.s3_bucket_name
}

output "kubeconfig_path" {
  description = "Path to kubeconfig"
  value       = "~/.kube/config"
}

output "next_steps" {
  description = "Next steps after infrastructure is ready"
  value = <<-EOT
    1. Configure kubectl: export KUBECONFIG=~/.kube/config
    2. Verify cluster: kubectl get nodes
    3. Deploy Helm charts: cd ../helm && helm install control-node ./control-node
    4. Deploy wg-proxy: helm install wg-proxy ./wg-proxy
    5. Run smoke tests: kubectl apply -f ../k8s/test/
  EOT
}





