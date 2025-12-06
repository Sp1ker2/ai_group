.PHONY: help deploy build test clean

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

deploy: ## Развернуть все компоненты
	@echo "🚀 Deploying Telegram Farm..."
	@bash scripts/deploy.sh

build-worker: ## Собрать Docker образ android-worker
	@echo "🔨 Building android-worker image..."
	@cd docker/android-worker && docker build -t registry.telegram-farm.local/android-worker:latest .

push-worker: build-worker ## Собрать и загрузить образ android-worker
	@echo "📤 Pushing android-worker image..."
	@docker push registry.telegram-farm.local/android-worker:latest

test: ## Запустить smoke тесты
	@echo "🧪 Running smoke tests..."
	@bash scripts/smoke-test.sh

terraform-init: ## Инициализировать Terraform
	@cd terraform && terraform init

terraform-plan: terraform-init ## Планировать изменения Terraform
	@cd terraform && terraform plan

terraform-apply: terraform-init ## Применить изменения Terraform
	@cd terraform && terraform apply

helm-install: ## Установить все Helm charts
	@echo "📦 Installing Helm charts..."
	@helm install wg-proxy ./helm/wg-proxy -n telegram-farm --create-namespace
	@helm install control-node ./helm/control-node -n telegram-farm

helm-upgrade: ## Обновить все Helm charts
	@echo "⬆️  Upgrading Helm charts..."
	@helm upgrade wg-proxy ./helm/wg-proxy -n telegram-farm
	@helm upgrade control-node ./helm/control-node -n telegram-farm

clean: ## Очистить временные файлы
	@echo "🧹 Cleaning up..."
	@rm -rf .terraform
	@rm -f terraform/*.tfstate*
	@kubectl delete namespace telegram-farm --ignore-not-found=true

status: ## Показать статус развертывания
	@echo "📊 Deployment status:"
	@kubectl get all -n telegram-farm
	@echo ""
	@echo "📈 HPA status:"
	@kubectl get hpa -n telegram-farm
	@echo ""
	@echo "🔒 Secrets:"
	@kubectl get secrets -n telegram-farm

logs-control: ## Показать логи Control Node
	@kubectl logs -f deployment/control-node -n telegram-farm

logs-wg: ## Показать логи WireGuard proxy
	@kubectl logs -f daemonset/wg-proxy -n telegram-farm

check-ip: ## Проверить исходящий IP
	@echo "🌐 Checking egress IP..."
	@kubectl run check-ip-$$(date +%s) -n telegram-farm --image=curlimages/curl --rm -it --restart=Never -- curl -s https://ifconfig.me






