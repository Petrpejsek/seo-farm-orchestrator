#!/bin/bash
# 🏥 COMPREHENSIVE HEALTH CHECK SCRIPT

set -e

echo "🏥 COMPREHENSIVE HEALTH CHECK STARTED"
echo "📅 Timestamp: $(date)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall health
OVERALL_HEALTH=0

# Function to log results
log_result() {
    local test_name=$1
    local result=$2
    local details=$3
    
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✅ $test_name: PASSED${NC}"
        [ ! -z "$details" ] && echo "   $details"
    else
        echo -e "${RED}❌ $test_name: FAILED${NC}"
        [ ! -z "$details" ] && echo "   $details"
        OVERALL_HEALTH=1
    fi
}

# Check 1: Process status
echo ""
echo "1️⃣ PROCESS STATUS CHECK:"

check_process() {
    local process_name=$1
    local process_pattern=$2
    
    if ps aux | grep -q "$process_pattern" && ! ps aux | grep "$process_pattern" | grep -q grep; then
        PIDS=$(ps aux | grep "$process_pattern" | grep -v grep | awk '{print $2}' | tr '\n' ' ')
        log_result "$process_name Process" 0 "Running (PIDs: $PIDS)"
        return 0
    else
        log_result "$process_name Process" 1 "Not running"
        return 1
    fi
}

check_process "Backend" "uvicorn"
check_process "Worker" "production_worker"
check_process "Frontend" "npm.*start\|next-server"

# Check 2: Port availability
echo ""
echo "2️⃣ PORT AVAILABILITY CHECK:"

check_port() {
    local port=$1
    local service_name=$2
    
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        log_result "$service_name Port ($port)" 0 "Listening"
        return 0
    else
        log_result "$service_name Port ($port)" 1 "Not listening"
        return 1
    fi
}

check_port "8000" "Backend API"
check_port "3001" "Frontend"
check_port "7233" "Temporal Server"

# Check 3: HTTP endpoint responses
echo ""
echo "3️⃣ HTTP ENDPOINT RESPONSES:"

check_http() {
    local url=$1
    local service_name=$2
    local timeout=${3:-10}
    
    if curl -f -s -m $timeout "$url" >/dev/null 2>&1; then
        RESPONSE_SIZE=$(curl -s -m $timeout "$url" | wc -c)
        log_result "$service_name HTTP" 0 "Responding (${RESPONSE_SIZE} bytes)"
        return 0
    else
        log_result "$service_name HTTP" 1 "Not responding or error"
        return 1
    fi
}

check_http "http://localhost:8000/health" "Backend API Health"
check_http "http://localhost:8000/api/workflow-runs" "Backend API Workflows"
check_http "http://localhost:3001" "Frontend"

# Check 4: Database connectivity
echo ""
echo "4️⃣ DATABASE CONNECTIVITY:"

DB_TEST_RESULT=$(python3 -c "
import asyncio
import sys
sys.path.append('.')

async def test_db():
    try:
        from backend.api.database import get_prisma_client
        client = await get_prisma_client()
        
        # Test basic query
        count = await client.workflowrun.count()
        print(f'Database connection OK - {count} workflow runs found')
        return 0
    except Exception as e:
        print(f'Database connection failed: {str(e)}')
        return 1

result = asyncio.run(test_db())
sys.exit(result)
" 2>&1)

DB_EXIT_CODE=$?
if [ $DB_EXIT_CODE -eq 0 ]; then
    log_result "Database Connection" 0 "$DB_TEST_RESULT"
else
    log_result "Database Connection" 1 "$DB_TEST_RESULT"
fi

# Check 5: Workflow functionality
echo ""
echo "5️⃣ WORKFLOW FUNCTIONALITY:"

# Test workflow creation
PROJECT_ID="a5999892-ae09-46fd-a3c2-7a8af516f8ac"  # Default project ID
WORKFLOW_TEST=$(curl -X POST "http://localhost:8000/api/pipeline-run" \
    -H "Content-Type: application/json" \
    -d "{\"topic\": \"HEALTH-CHECK-$(date +%s)\", \"project_id\": \"$PROJECT_ID\"}" \
    -s -w "HTTP_CODE:%{http_code}" 2>/dev/null)

HTTP_CODE=$(echo "$WORKFLOW_TEST" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
RESPONSE_BODY=$(echo "$WORKFLOW_TEST" | sed 's/HTTP_CODE:[0-9]*$//')

if [ "$HTTP_CODE" = "200" ] && echo "$RESPONSE_BODY" | grep -q "started"; then
    WORKFLOW_ID=$(echo "$RESPONSE_BODY" | grep -o '"workflow_id":"[^"]*"' | cut -d'"' -f4)
    log_result "Workflow Creation" 0 "Successfully started workflow: $WORKFLOW_ID"
else
    log_result "Workflow Creation" 1 "Failed (HTTP: $HTTP_CODE, Response: $RESPONSE_BODY)"
fi

# Check 6: Workflow limit verification
echo ""
echo "6️⃣ WORKFLOW LIMIT VERIFICATION:"

WORKFLOW_COUNT=$(curl -s "http://localhost:8000/api/workflow-runs" 2>/dev/null | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(len(data))
except:
    print(0)
" 2>/dev/null)

if [ "$WORKFLOW_COUNT" -gt 50 ]; then
    log_result "Workflow Limit Fix" 0 "API returns $WORKFLOW_COUNT workflows (>50)"
else
    log_result "Workflow Limit Fix" 1 "API returns only $WORKFLOW_COUNT workflows (should be >50)"
fi

# Check 7: System resources
echo ""
echo "7️⃣ SYSTEM RESOURCES:"

# Memory usage
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.1f%%", $3*100/$2}')
MEMORY_USAGE_NUM=$(echo $MEMORY_USAGE | sed 's/%//')

if [ $(echo "$MEMORY_USAGE_NUM < 90" | bc 2>/dev/null || echo "1") -eq 1 ]; then
    log_result "Memory Usage" 0 "$MEMORY_USAGE"
else
    log_result "Memory Usage" 1 "$MEMORY_USAGE (HIGH)"
fi

# Disk usage
DISK_USAGE=$(df / | awk 'NR==2{print $5}' | sed 's/%//')

if [ "$DISK_USAGE" -lt 90 ]; then
    log_result "Disk Usage" 0 "${DISK_USAGE}%"
else
    log_result "Disk Usage" 1 "${DISK_USAGE}% (HIGH)"
fi

# Load average
LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
log_result "Load Average" 0 "$LOAD_AVG"

# Check 8: Log file health
echo ""
echo "8️⃣ LOG FILE HEALTH:"

check_log_file() {
    local log_file=$1
    local service_name=$2
    
    if [ -f "$log_file" ]; then
        LOG_SIZE=$(ls -lh "$log_file" | awk '{print $5}')
        RECENT_ENTRIES=$(tail -n 10 "$log_file" | wc -l)
        log_result "$service_name Log" 0 "Size: $LOG_SIZE, Recent entries: $RECENT_ENTRIES"
        
        # Check for errors in recent logs
        ERROR_COUNT=$(tail -n 100 "$log_file" | grep -i error | wc -l)
        if [ "$ERROR_COUNT" -gt 5 ]; then
            echo -e "   ${YELLOW}⚠️ Warning: $ERROR_COUNT errors found in recent logs${NC}"
        fi
    else
        log_result "$service_name Log" 1 "Log file not found"
    fi
}

# Find recent log files
RECENT_BACKEND_LOG=$(ls -t backend_*.log 2>/dev/null | head -n1 || echo "backend.log")
RECENT_WORKER_LOG=$(ls -t worker_*.log 2>/dev/null | head -n1 || echo "worker.log")
RECENT_FRONTEND_LOG=$(ls -t frontend_*.log 2>/dev/null | head -n1 || echo "frontend.log")

check_log_file "$RECENT_BACKEND_LOG" "Backend"
check_log_file "$RECENT_WORKER_LOG" "Worker"
check_log_file "$RECENT_FRONTEND_LOG" "Frontend"

# Final summary
echo ""
echo "🏥 HEALTH CHECK SUMMARY:"
echo "========================================"

if [ $OVERALL_HEALTH -eq 0 ]; then
    echo -e "${GREEN}🎉 OVERALL HEALTH: EXCELLENT${NC}"
    echo "✅ All systems operational"
    echo "🚀 System ready for production traffic"
else
    echo -e "${RED}⚠️ OVERALL HEALTH: ISSUES DETECTED${NC}"
    echo "❌ Some systems require attention"
    echo "🔧 Review failed checks above"
fi

echo ""
echo "📊 Quick Stats:"
echo "   Memory Usage: $MEMORY_USAGE"
echo "   Disk Usage: ${DISK_USAGE}%"
echo "   Load Average: $LOAD_AVG"
echo "   Workflows Available: $WORKFLOW_COUNT"
echo ""
echo "🔗 Service URLs:"
echo "   Backend API: http://localhost:8000"
echo "   Frontend: http://localhost:3001"
echo "   API Health: http://localhost:8000/health"
echo "   Temporal UI: http://localhost:8233"

exit $OVERALL_HEALTH

