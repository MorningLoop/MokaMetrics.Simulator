# MokaMetrics Simulator - Docker Management

.PHONY: help build dev prod test clean logs status stop restart health

# Default target
help:
	@echo "🐳 MokaMetrics Simulator - Docker Management"
	@echo "============================================"
	@echo ""
	@echo "Available commands:"
	@echo "  make dev        - Start development environment"
	@echo "  make dev-ui     - Start development with Kafka UI"
	@echo "  make prod       - Start production environment"
	@echo "  make build      - Build Docker image"
	@echo "  make test       - Test deployment"
	@echo "  make logs       - View logs"
	@echo "  make status     - Check container status"
	@echo "  make health     - Check health endpoint"
	@echo "  make stop       - Stop containers"
	@echo "  make restart    - Restart containers"
	@echo "  make clean      - Clean up containers and images"
	@echo "  make help       - Show this help"

# Development environment
dev:
	@echo "🚀 Starting development environment..."
	./deploy.sh --dev

# Development with Kafka UI
dev-ui:
	@echo "🚀 Starting development environment with Kafka UI..."
	./deploy.sh --dev --kafka-ui

# Production environment
prod:
	@echo "🚀 Starting production environment..."
	./deploy.sh --prod

# Build Docker image
build:
	@echo "🔨 Building Docker image..."
	docker compose build

# Test deployment
test:
	@echo "🧪 Testing deployment..."
	./test_docker_deployment.sh

# View logs
logs:
	@if [ -f docker-compose.prod.yml ] && docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then \
		docker-compose -f docker-compose.prod.yml logs -f; \
	elif [ -f docker-compose.dev.yml ] && docker-compose -f docker-compose.dev.yml ps | grep -q "Up"; then \
		docker-compose -f docker-compose.dev.yml logs -f; \
	else \
		docker-compose logs -f; \
	fi

# Check container status
status:
	@echo "📊 Container Status:"
	@docker-compose ps 2>/dev/null || echo "No containers found with default compose file"
	@docker-compose -f docker-compose.dev.yml ps 2>/dev/null || echo "No dev containers found"
	@docker-compose -f docker-compose.prod.yml ps 2>/dev/null || echo "No prod containers found"

# Check health endpoint
health:
	@echo "🏥 Checking health endpoint..."
	@curl -s http://localhost:8083/health | python -m json.tool 2>/dev/null || \
		echo "❌ Health endpoint not accessible"

# Stop containers
stop:
	@echo "🛑 Stopping containers..."
	@docker-compose down 2>/dev/null || true
	@docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
	@docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

# Restart containers
restart:
	@echo "🔄 Restarting containers..."
	@if [ -f docker-compose.prod.yml ] && docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then \
		docker-compose -f docker-compose.prod.yml restart; \
	elif [ -f docker-compose.dev.yml ] && docker-compose -f docker-compose.dev.yml ps | grep -q "Up"; then \
		docker-compose -f docker-compose.dev.yml restart; \
	else \
		docker-compose restart; \
	fi

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	@docker-compose down --rmi all --volumes --remove-orphans 2>/dev/null || true
	@docker-compose -f docker-compose.dev.yml down --rmi all --volumes --remove-orphans 2>/dev/null || true
	@docker-compose -f docker-compose.prod.yml down --rmi all --volumes --remove-orphans 2>/dev/null || true
	@docker system prune -f

# Quick development setup
setup-dev: build dev test
	@echo "✅ Development environment ready!"

# Quick production setup
setup-prod: build prod test
	@echo "✅ Production environment ready!"
