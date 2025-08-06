#!/bin/bash

# 🏭 PRODUCTION ENVIRONMENT SETUP SCRIPT
# =======================================
# Kompletní nastavení produkčního prostředí pro SEO Farm Orchestrator

echo "🏭 === PRODUCTION ENVIRONMENT SETUP ==="
echo ""

# 🌍 CORE ENVIRONMENT
export ENVIRONMENT=production
export HOSTNAME=${HOSTNAME:-prod-server-01}

# 🌐 API & NETWORKING
export API_BASE_URL=https://api.seo-farm.com
export TEMPORAL_HOST=temporal.seo-farm.com:7233
export TEMPORAL_NAMESPACE=production

# 👤 SECURITY & USER
export WORKER_USER=seouser
export LOG_LEVEL=INFO

# 🐍 PYTHON CONFIGURATION  
export PYTHON_EXECUTABLE=python3

# ⏱️ TIMEOUTS & PERFORMANCE
export HEALTH_CHECK_INTERVAL=30
export MAX_STARTUP_WAIT=60
export GRACEFUL_SHUTDOWN_TIMEOUT=30
export MAX_CONCURRENT_ACTIVITIES=3

# 🗄️ DATABASE - PRODUCTION PostgreSQL (už funguje)
export DATABASE_URL=postgresql://seo_user:silne-heslo@91.99.210.104:5432/seo_farm

# 📊 MONITORING & LOGGING
export SAVE_TO_DB=true
export LOG_ROTATION=true

# 📁 PRODUCTION PATHS
export WORKER_SCRIPT=/opt/seo-farm/production_worker.py
export PID_FILE=/var/run/seo-farm/worker.pid
export LOCK_FILE=/var/lock/seo-farm/temporal_worker.lock
export LOG_FILE=/var/log/seo-farm/worker.log

echo "✅ Production environment variables nastaveny:"
echo "   ENVIRONMENT: $ENVIRONMENT"
echo "   API_BASE_URL: $API_BASE_URL"
echo "   TEMPORAL_HOST: $TEMPORAL_HOST"
echo "   DATABASE_URL: ${DATABASE_URL:0:50}..."
echo ""

# Ověření, že máme master_worker_manager_production.sh
if [[ -f "./master_worker_manager_production.sh" ]]; then
    echo "✅ master_worker_manager_production.sh nalezen"
else
    echo "❌ master_worker_manager_production.sh NENALEZEN!"
    exit 1
fi

# Vytvoření aliasu pro snadné použití
echo "🔧 Vytvářím alias pro production worker..."
alias start_production_worker="./master_worker_manager_production.sh start"
alias stop_production_worker="./master_worker_manager_production.sh stop"
alias restart_production_worker="./master_worker_manager_production.sh restart"
alias status_production_worker="./master_worker_manager_production.sh status"
alias health_production_worker="./master_worker_manager_production.sh health"

echo ""
echo "🚀 READY FOR PRODUCTION!"
echo ""
echo "📋 Dostupné příkazy:"
echo "   start_production_worker    # Spustí production worker"
echo "   stop_production_worker     # Zastaví production worker"
echo "   restart_production_worker  # Restartuje production worker"
echo "   status_production_worker   # Status production worker"
echo "   health_production_worker   # Health check production worker"
echo ""
echo "   Nebo přímo: ./master_worker_manager_production.sh [command]"
echo ""
echo "🎯 Pro spuštění: source production_env_setup.sh && start_production_worker"
echo ""