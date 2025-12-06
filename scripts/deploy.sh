#!/bin/bash
# Скрипт развертывания Telegram Farm

set -e

NAMESPACE="telegram-farm"
KUBECONFIG="${KUBECONFIG:-~/.kube/config}"

echo "🚀 Starting Telegram Farm deployment..."

# Проверка kubectl
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl."
    exit 1
fi

# Проверка подключения к кластеру
echo "📡 Checking cluster connection..."
kubectl cluster-info || {
    echo "❌ Cannot connect to cluster. Check your kubeconfig."
    exit 1
}

# Создание namespace
echo "📦 Creating namespace..."
kubectl apply -f k8s/namespace.yaml

# Создание secrets (требует ручного ввода)
echo "🔐 Please create secrets manually (see k8s/secrets/README.md)"
read -p "Press Enter after creating secrets..."

# Развертывание Redis
echo "📦 Deploying Redis..."
kubectl apply -f k8s/redis/

# Развертывание Postgres
echo "📦 Deploying Postgres..."
kubectl apply -f k8s/postgres/

# Ожидание готовности БД
echo "⏳ Waiting for databases to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s

# Развертывание WireGuard proxy
echo "🔒 Deploying WireGuard proxy..."
kubectl apply -f k8s/wg-proxy/

# Развертывание Control Node (через Helm или kubectl)
if command -v helm &> /dev/null; then
    echo "📦 Deploying Control Node via Helm..."
    helm install control-node ./helm/control-node -n $NAMESPACE
else
    echo "⚠️  Helm not found. Skipping Control Node deployment."
    echo "   Install Helm and run: helm install control-node ./helm/control-node -n $NAMESPACE"
fi

# Проверка статуса
echo "✅ Deployment complete!"
echo ""
echo "📊 Checking status..."
kubectl get pods -n $NAMESPACE
kubectl get services -n $NAMESPACE

echo ""
echo "🎉 Deployment finished!"
echo ""
echo "Next steps:"
echo "1. Verify all pods are running: kubectl get pods -n $NAMESPACE"
echo "2. Check logs: kubectl logs -f <pod-name> -n $NAMESPACE"
echo "3. Test a job: kubectl apply -f k8s/android-worker/job-example.yaml"






