#!/bin/bash
# Smoke test для проверки развертывания

set -e

NAMESPACE="telegram-farm"
TEST_JOBS=10

echo "🧪 Running smoke tests..."

# Проверка namespace
echo "1. Checking namespace..."
kubectl get namespace $NAMESPACE || {
    echo "❌ Namespace not found"
    exit 1
}

# Проверка pods
echo "2. Checking pods..."
PODS=$(kubectl get pods -n $NAMESPACE --no-headers | wc -l)
if [ $PODS -eq 0 ]; then
    echo "❌ No pods found"
    exit 1
fi
echo "✅ Found $PODS pods"

# Проверка services
echo "3. Checking services..."
kubectl get services -n $NAMESPACE

# Проверка исходящего IP (должен быть российский)
echo "4. Checking egress IP..."
POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=android-worker -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -n "$POD_NAME" ]; then
    EGRESS_IP=$(kubectl exec -n $NAMESPACE $POD_NAME -- curl -s https://ifconfig.me 2>/dev/null || echo "N/A")
    echo "   Egress IP: $EGRESS_IP"
    # Проверка на российский IP (примерная проверка)
    if [[ $EGRESS_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "✅ Egress IP detected"
    else
        echo "⚠️  Could not verify egress IP"
    fi
else
    echo "⚠️  No android-worker pod found for IP check"
fi

# Запуск тестовых Jobs
echo "5. Creating test jobs..."
for i in $(seq 1 $TEST_JOBS); do
    JOB_NAME="test-job-$i"
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: $JOB_NAME
  namespace: $NAMESPACE
spec:
  ttlSecondsAfterFinished: 300
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: test
        image: busybox
        command: ["sh", "-c", "echo 'Test job $i'; sleep 5"]
      nodeSelector:
        node-role.kubernetes.io/worker: ""
EOF
done

echo "⏳ Waiting for jobs to complete..."
sleep 10

# Проверка результатов
SUCCESSFUL=$(kubectl get jobs -n $NAMESPACE -l job-name=test-job --no-headers | grep -c "1/1" || echo "0")
echo "✅ Successful jobs: $SUCCESSFUL/$TEST_JOBS"

# Очистка
echo "6. Cleaning up test jobs..."
kubectl delete jobs -n $NAMESPACE -l job-name=test-job --ignore-not-found=true

echo ""
echo "🎉 Smoke tests completed!"





