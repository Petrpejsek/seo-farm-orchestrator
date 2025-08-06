#!/bin/bash

# 🛠️ LOCAL DEVELOPMENT ENVIRONMENT SETUP SCRIPT
# ===============================================
# Nastavení pro lokální development s production workerem

echo "🛠️ === LOCAL DEVELOPMENT ENVIRONMENT SETUP ==="
echo ""

# 🌍 CORE ENVIRONMENT
export ENVIRONMENT=development
export HOSTNAME=localhost

# 🌐 API & NETWORKING (LOCAL)
export API_BASE_URL=http://localhost:8000
export TEMPORAL_HOST=localhost:7233
export TEMPORAL_NAMESPACE=default

# 👤 USER & SECURITY
export WORKER_USER=$(whoami)
export LOG_LEVEL=DEBUG

# 🐍 PYTHON
export PYTHON_EXECUTABLE=python3

# ⏱️ TIMEOUTS
export HEALTH_CHECK_INTERVAL=30
export MAX_STARTUP_WAIT=60
export GRACEFUL_SHUTDOWN_TIMEOUT=30

# 🗄️ DATABASE - REMOTE PostgreSQL (už nastavené)
export DATABASE_URL=postgresql://seo_user:silne-heslo@91.99.210.104:5432/seo_farm

# 📁 LOCAL PATHS
export WORKER_SCRIPT=./production_worker.py
export PID_FILE=./worker.pid
export LOCK_FILE=/tmp/temporal_worker_dev.lock
export LOG_FILE=./worker.log

echo "✅ Local development environment variables nastaveny:"
echo "   ENVIRONMENT: $ENVIRONMENT"
echo "   API_BASE_URL: $API_BASE_URL"
echo "   TEMPORAL_HOST: $TEMPORAL_HOST"
echo "   DATABASE_URL: ${DATABASE_URL:0:50}..."
echo ""

# Vytvoření aliasu pro snadné použití
echo "🔧 Vytvářím alias pro local development..."
alias start_worker="./master_worker_manager_production.sh start"
alias stop_worker="./master_worker_manager_production.sh stop"
alias restart_worker="./master_worker_manager_production.sh restart"
alias status_worker="./master_worker_manager_production.sh status"
alias health_worker="./master_worker_manager_production.sh health"

echo ""
echo "🚀 READY FOR LOCAL DEVELOPMENT!"
echo ""
echo "📋 Dostupné příkazy:"
echo "   start_worker    # Spustí worker"
echo "   stop_worker     # Zastaví worker"
echo "   restart_worker  # Restartuje worker"
echo "   status_worker   # Status worker"
echo "   health_worker   # Health check worker"
echo ""
echo "   Nebo přímo: ./master_worker_manager_production.sh [command]"
echo ""
echo "🎯 Pro spuštění: source local_env_setup.sh && start_worker"
echo ""