# SEO Farm Orchestrator - Makefile
# Usnadňuje spouštění běžných operací

.PHONY: help dev backend frontend smoke-test smoke-test-quick install clean

# Default target
help:
	@echo "🔧 SEO Farm Orchestrator - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  make dev              - Start both backend and frontend servers"
	@echo "  make backend          - Start only backend server"
	@echo "  make frontend         - Start only frontend server"
	@echo ""
	@echo "Testing:"
	@echo "  make smoke-test       - Run full smoke test (25 min timeout)"
	@echo "  make smoke-test-quick - Run quick smoke test (5 min timeout)"
	@echo ""
	@echo "Setup:"
	@echo "  make install          - Install dependencies for both backend and frontend"
	@echo "  make clean            - Clean build artifacts and caches"

# Development servers
dev:
	@echo "🚀 Starting SEO Farm Orchestrator (backend + frontend)..."
	./run-dev.sh

backend:
	@echo "🐍 Starting backend server..."
	cd backend && uvicorn main:app --port 8000 --reload

frontend:
	@echo "⚛️  Starting frontend server..."
	cd web-frontend && NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev -- --port 3001

# Testing
smoke-test:
	@echo "🧪 Running full smoke test..."
	python3 scripts/smoke_test.py --api-url http://localhost:8000 --timeout 1500

smoke-test-quick:
	@echo "🧪 Running quick smoke test..."
	python3 scripts/smoke_test.py --api-url http://localhost:8000 --timeout 300

# Setup and maintenance
install:
	@echo "📦 Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "📦 Installing frontend dependencies..."
	cd web-frontend && npm install
	@echo "✅ All dependencies installed"

clean:
	@echo "🧹 Cleaning build artifacts..."
	cd web-frontend && rm -rf .next node_modules/.cache
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Clean completed"

# Database commands
db-setup:
	@echo "🗄️ Setting up database..."
	npm install
	npm run db:migrate
	npm run db:generate
	@echo "✅ Database setup completed"

db-migrate:
	@echo "🔄 Running database migration..."
	npm run db:migrate

db-seed:
	@echo "🌱 Seeding database with test data..."
	python3 scripts/db_seed.py

db-studio:
	@echo "🔍 Opening Prisma Studio..."
	npm run db:studio

db-reset:
	@echo "⚠️  Resetting database (all data will be lost)..."
	npm run db:reset

test-api:
	@echo "🧪 Testing API endpoints..."
	@echo "Projects:"
	curl -s http://localhost:8000/api/projects | python3 -m json.tool
	@echo "\nAssistant functions:"
	curl -s http://localhost:8000/api/assistant-functions | python3 -m json.tool 