#!/bin/bash
# 📊 CONTINUOUS MONITORING SCRIPT
# Runs every 5 minutes via cron: */5 * * * * /path/to/monitor.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/seo-farm/monitoring.log"
ALERT_FILE="/var/log/seo-farm/alerts.log"

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$(dirname "$ALERT_FILE")"

# Timestamp function
timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# Logging function
log_monitor() {
    echo "$(timestamp) $1" >> "$LOG_FILE"
}

# Alert function
send_alert() {
    local service_name=$1
    local issue_description=$2
    local timestamp=$(timestamp)
    
    # Log alert
    echo "$timestamp ALERT: $service_name - $issue_description" >> "$ALERT_FILE"
    
    # Try to auto-restart the service
    log_monitor "ALERT: $service_name - $issue_description. Attempting auto-restart..."
    
    case $service_name in
        "Backend")
            restart_backend
            ;;
        "Worker")
            restart_worker
            ;;
        "Frontend")
            restart_frontend
            ;;
    esac
}

# Service restart functions
restart_backend() {
    log_monitor "Attempting backend restart..."
    cd "$PROJECT_DIR"
    
    # Kill existing
    pkill -f uvicorn 2>/dev/null || true
    sleep 5
    
    # Start new
    source venv/bin/activate 2>/dev/null || true
    export $(grep -v '^#' .env | xargs) 2>/dev/null || true
    nohup python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend_restart_$(date +%H%M).log 2>&1 &
    
    # Check if successful
    sleep 10
    if check_backend_health; then
        log_monitor "✅ Backend restart successful"
        return 0
    else
        log_monitor "❌ Backend restart failed"
        return 1
    fi
}

restart_worker() {
    log_monitor "Attempting worker restart..."
    cd "$PROJECT_DIR"
    
    # Kill existing
    pkill -f production_worker 2>/dev/null || true
    sleep 5
    
    # Start new
    source venv/bin/activate 2>/dev/null || true
    export $(grep -v '^#' .env | xargs) 2>/dev/null || true
    nohup python production_worker.py > worker_restart_$(date +%H%M).log 2>&1 &
    
    # Check if successful
    sleep 5
    if check_worker_health; then
        log_monitor "✅ Worker restart successful"
        return 0
    else
        log_monitor "❌ Worker restart failed"
        return 1
    fi
}

restart_frontend() {
    log_monitor "Attempting frontend restart..."
    cd "$PROJECT_DIR"
    
    # Kill existing
    pkill -f "npm.*start\|next-server" 2>/dev/null || true
    sleep 5
    
    # Start new
    if [ -d "web-frontend" ] && command -v npm &> /dev/null; then
        cd web-frontend
        nohup npm run start -- -p 3001 > ../frontend_restart_$(date +%H%M).log 2>&1 &
        cd ..
        
        # Check if successful
        sleep 10
        if check_frontend_health; then
            log_monitor "✅ Frontend restart successful"
            return 0
        else
            log_monitor "❌ Frontend restart failed"
            return 1
        fi
    else
        log_monitor "⚠️ Frontend restart skipped (not available)"
        return 1
    fi
}

# Health check functions
check_backend_health() {
    curl -f -s -m 10 http://localhost:8000/health >/dev/null 2>&1
}

check_frontend_health() {
    curl -f -s -m 10 http://localhost:3001 >/dev/null 2>&1
}

check_worker_health() {
    ps aux | grep -q production_worker && ! ps aux | grep production_worker | grep -q grep
}

check_database_health() {
    cd "$PROJECT_DIR"
    python3 -c "
import asyncio
import sys
import os
sys.path.append('.')

async def test_db():
    try:
        from backend.api.database import get_prisma_client
        client = await get_prisma_client()
        await client.workflowrun.count()
        return True
    except:
        return False

result = asyncio.run(test_db())
sys.exit(0 if result else 1)
" 2>/dev/null
}

# Service monitoring function
check_service() {
    local service_name=$1
    local check_function=$2
    
    if $check_function; then
        log_monitor "✅ $service_name: OK"
        return 0
    else
        log_monitor "❌ $service_name: FAILED"
        send_alert "$service_name" "Service check failed"
        return 1
    fi
}

# System resource monitoring
check_system_resources() {
    # Memory usage
    MEMORY_USAGE=$(free | awk 'NR==2{printf "%.1f", $3*100/$2}')
    if [ $(echo "$MEMORY_USAGE > 90" | bc 2>/dev/null || echo "0") -eq 1 ]; then
        log_monitor "⚠️ HIGH MEMORY USAGE: ${MEMORY_USAGE}%"
    fi
    
    # Disk usage
    DISK_USAGE=$(df / | awk 'NR==2{print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 90 ]; then
        log_monitor "⚠️ HIGH DISK USAGE: ${DISK_USAGE}%"
    fi
    
    # Load average
    LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    log_monitor "📊 System stats - Memory: ${MEMORY_USAGE}%, Disk: ${DISK_USAGE}%, Load: ${LOAD_AVG}"
}

# Workflow limit monitoring
check_workflow_limit() {
    cd "$PROJECT_DIR"
    WORKFLOW_COUNT=$(curl -s -m 10 "http://localhost:8000/api/workflow-runs" 2>/dev/null | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(len(data))
except:
    print(0)
" 2>/dev/null)

    if [ "$WORKFLOW_COUNT" -le 50 ]; then
        log_monitor "⚠️ WORKFLOW LIMIT ISSUE: Only $WORKFLOW_COUNT workflows returned (should be >50)"
        send_alert "WorkflowLimit" "API returning only $WORKFLOW_COUNT workflows"
    else
        log_monitor "✅ Workflow limit OK: $WORKFLOW_COUNT workflows"
    fi
}

# Main monitoring routine
main() {
    log_monitor "🔍 Starting monitoring cycle"
    
    # Change to project directory
    cd "$PROJECT_DIR" || {
        log_monitor "❌ Cannot access project directory: $PROJECT_DIR"
        exit 1
    }
    
    # Check all services
    check_service "Backend" check_backend_health
    check_service "Frontend" check_frontend_health
    check_service "Worker" check_worker_health
    check_service "Database" check_database_health
    
    # Check system resources
    check_system_resources
    
    # Check workflow functionality
    check_workflow_limit
    
    # Log file rotation (keep last 1000 lines)
    if [ -f "$LOG_FILE" ] && [ $(wc -l < "$LOG_FILE") -gt 1000 ]; then
        tail -n 1000 "$LOG_FILE" > "${LOG_FILE}.tmp"
        mv "${LOG_FILE}.tmp" "$LOG_FILE"
    fi
    
    log_monitor "✅ Monitoring cycle completed"
}

# Run monitoring
main

# Exit codes:
# 0 - All services healthy
# 1 - Some services failed but auto-restart attempted
# 2 - Critical failure, manual intervention required

exit 0

