#!/bin/bash
# Скрипт для создания всех необходимых secrets

set -e

NAMESPACE="telegram-farm"

echo "🔐 Creating secrets for Telegram Farm..."

# Создание namespace если не существует
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Postgres secrets
echo "Creating Postgres secrets..."
read -p "Postgres username [telegram_farm]: " PG_USER
PG_USER=${PG_USER:-telegram_farm}
read -sp "Postgres password: " PG_PASS
echo ""

kubectl create secret generic postgres-secrets \
  --from-literal=username="$PG_USER" \
  --from-literal=password="$PG_PASS" \
  -n $NAMESPACE \
  --dry-run=client -o yaml | kubectl apply -f -

# Control Node secrets
echo "Creating Control Node secrets..."
read -p "Control API secret key: " SECRET_KEY
read -p "Database URL [postgresql://$PG_USER:$PG_PASS@postgres:5432/telegram_farm]: " DB_URL
DB_URL=${DB_URL:-"postgresql://$PG_USER:$PG_PASS@postgres:5432/telegram_farm"}
read -p "Redis URL [redis://redis:6379]: " REDIS_URL
REDIS_URL=${REDIS_URL:-"redis://redis:6379"}

kubectl create secret generic control-node-secrets \
  --from-literal=database-url="$DB_URL" \
  --from-literal=redis-url="$REDIS_URL" \
  --from-literal=secret-key="$SECRET_KEY" \
  -n $NAMESPACE \
  --dry-run=client -o yaml | kubectl apply -f -

# Android Worker secrets
echo "Creating Android Worker secrets..."
read -p "Control API token: " API_TOKEN

kubectl create secret generic android-worker-secrets \
  --from-literal=api-token="$API_TOKEN" \
  -n $NAMESPACE \
  --dry-run=client -o yaml | kubectl apply -f -

# WireGuard secrets (опционально)
read -p "Create WireGuard secrets? (y/n) [n]: " CREATE_WG
if [[ $CREATE_WG == "y" || $CREATE_WG == "Y" ]]; then
    read -p "WireGuard private key: " WG_PRIVATE_KEY
    read -p "WireGuard peer public key: " WG_PEER_PUBLIC_KEY
    
    kubectl create secret generic wg-proxy-private-key \
      --from-literal=private-key="$WG_PRIVATE_KEY" \
      --from-literal=peer-public-key="$WG_PEER_PUBLIC_KEY" \
      -n $NAMESPACE \
      --dry-run=client -o yaml | kubectl apply -f -
fi

echo ""
echo "✅ Secrets created successfully!"
echo ""
echo "To verify:"
echo "  kubectl get secrets -n $NAMESPACE"





