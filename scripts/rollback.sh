#!/bin/bash
# 🔄 INTELLIGENT ROLLBACK SYSTEM

set -e

BACKUP_DIR_PATTERN="/root/backup_*"
TARGET_BACKUP=$1

echo "🔄 INTELLIGENT ROLLBACK SYSTEM"
echo "📅 Timestamp: $(date)"

# Function to list available backups
list_backups() {
    echo "📦 Available backups:"
    ls -dt $BACKUP_DIR_PATTERN 2>/dev/null | head -n 10 | while read backup; do
        BACKUP_DATE=$(basename "$backup" | sed 's/backup_//' | sed 's/_/ /')
        BACKUP_SIZE=$(du -sh "$backup" 2>/dev/null | cut -f1)
        echo "   - $backup ($BACKUP_SIZE, created: $BACKUP_DATE)"
    done
}

# If no specific backup provided, show options
if [ -z "$TARGET_BACKUP" ]; then
    echo "❓ No specific backup provided"
    list_backups
    
    LATEST_BACKUP=$(ls -dt $BACKUP_DIR_PATTERN 2>/dev/null | head -n1)
    if [ -z "$LATEST_BACKUP" ]; then
        echo "❌ No backups found for rollback!"
        echo "💡 Backup pattern: $BACKUP_DIR_PATTERN"
        exit 1
    fi
    
    echo ""
    echo "🤖 Auto-selecting latest backup: $LATEST_BACKUP"
    TARGET_BACKUP=$LATEST_BACKUP
else
    # Validate provided backup
    if [ ! -d "$TARGET_BACKUP" ]; then
        echo "❌ Backup directory not found: $TARGET_BACKUP"
        echo ""
        list_backups
        exit 1
    fi
fi

echo ""
echo "🎯 Selected backup: $TARGET_BACKUP"
BACKUP_DATE=$(basename "$TARGET_BACKUP" | sed 's/backup_//' | sed 's/_/ /')
echo "📅 Backup date: $BACKUP_DATE"

# Confirmation (skip in emergency mode)
if [ "$2" != "--force" ]; then
    echo ""
    echo "⚠️  WARNING: This will:"
    echo "   1. Stop all current services"
    echo "   2. Replace current deployment"
    echo "   3. Restart services with backup version"
    echo ""
    read -p "🔄 Continue with rollback? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Rollback cancelled"
        exit 1
    fi
fi

echo ""
echo "🚀 STARTING ROLLBACK PROCESS..."

# Step 1: Create emergency backup of current state
CURRENT_DIR="/root/seo-farm-orchestrator"
EMERGENCY_BACKUP="/root/emergency_backup_$(date +%Y%m%d_%H%M%S)"

if [ -d "$CURRENT_DIR" ]; then
    echo "📦 Creating emergency backup of current state..."
    cp -r "$CURRENT_DIR" "$EMERGENCY_BACKUP"
    echo "✅ Emergency backup created: $EMERGENCY_BACKUP"
else
    echo "⚠️ Current deployment directory not found: $CURRENT_DIR"
fi

# Step 2: Stop current services gracefully
echo ""
echo "⏹️ STOPPING CURRENT SERVICES..."

stop_service() {
    local service_name=$1
    local process_pattern=$2
    
    echo "🛑 Stopping $service_name..."
    PIDS=$(ps aux | grep "$process_pattern" | grep -v grep | awk '{print $2}' || true)
    
    if [ ! -z "$PIDS" ]; then
        # Graceful shutdown first
        for pid in $PIDS; do
            kill -TERM $pid 2>/dev/null || true
        done
        
        # Wait up to 15 seconds
        sleep 15
        
        # Force kill if needed
        for pid in $PIDS; do
            if kill -0 $pid 2>/dev/null; then
                echo "Force killing $pid..."
                kill -KILL $pid 2>/dev/null || true
            fi
        done
        echo "✅ $service_name stopped"
    else
        echo "ℹ️ $service_name was not running"
    fi
}

stop_service "Backend" "uvicorn"
stop_service "Worker" "production_worker"
stop_service "Frontend" "npm.*start\|next-server"

# Additional cleanup
sleep 5

# Step 3: Restore from backup
echo ""
echo "📂 RESTORING FROM BACKUP..."

if [ -d "$CURRENT_DIR" ]; then
    echo "🗑️ Removing current deployment..."
    rm -rf "$CURRENT_DIR"
fi

echo "📥 Restoring from backup: $TARGET_BACKUP"
cp -r "$TARGET_BACKUP" "$CURRENT_DIR"
echo "✅ Files restored successfully"

# Step 4: Fix permissions
echo ""
echo "🔐 FIXING PERMISSIONS..."
cd "$CURRENT_DIR"
chmod +x scripts/*.sh 2>/dev/null || true
chmod +x *.sh 2>/dev/null || true
echo "✅ Permissions fixed"

# Step 5: Start services with restored version
echo ""
echo "🚀 STARTING RESTORED SERVICES..."

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️ Virtual environment not found in backup"
fi

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
    echo "✅ Environment variables loaded"
else
    echo "⚠️ .env file not found in backup"
fi

# Start backend
echo "🌐 Starting backend..."
nohup python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend_rollback.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"

# Wait for backend to be ready
echo "⏳ Waiting for backend..."
for i in {1..30}; do
    if curl -f -s http://localhost:8000/health >/dev/null 2>&1; then
        echo "✅ Backend is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start after rollback"
        echo "🆘 EMERGENCY: Check backend_rollback.log"
        exit 1
    fi
    sleep 2
done

# Start worker
echo "⚙️ Starting worker..."
nohup python production_worker.py > worker_rollback.log 2>&1 &
WORKER_PID=$!
echo "✅ Worker started (PID: $WORKER_PID)"

# Start frontend if available
if [ -d "web-frontend" ] && command -v npm &> /dev/null; then
    echo "🎨 Starting frontend..."
    cd web-frontend
    nohup npm run start -- -p 3001 > ../frontend_rollback.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
    echo "✅ Frontend started (PID: $FRONTEND_PID)"
else
    echo "ℹ️ Frontend not available in backup"
    FRONTEND_PID="N/A"
fi

# Step 6: Health check
echo ""
echo "🏥 POST-ROLLBACK HEALTH CHECK..."
sleep 10

# Basic health checks
HEALTH_OK=true

# Check backend
if ! curl -f -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "❌ Backend health check failed after rollback"
    HEALTH_OK=false
fi

# Check processes
if ! ps aux | grep -q "uvicorn" || ps aux | grep "uvicorn" | grep -q grep; then
    echo "❌ Backend process not running after rollback"
    HEALTH_OK=false
fi

if ! ps aux | grep -q "production_worker" || ps aux | grep "production_worker" | grep -q grep; then
    echo "❌ Worker process not running after rollback"
    HEALTH_OK=false
fi

# Step 7: Create rollback report
echo ""
echo "📋 CREATING ROLLBACK REPORT..."

cat > rollback_report.txt << EOF
ROLLBACK COMPLETED
==================
Date: $(date)
Target Backup: $TARGET_BACKUP
Backup Date: $BACKUP_DATE
Emergency Backup: $EMERGENCY_BACKUP

Service Status:
- Backend PID: $BACKEND_PID
- Worker PID: $WORKER_PID  
- Frontend PID: $FRONTEND_PID

Health Check: $([ "$HEALTH_OK" = true ] && echo "PASSED" || echo "FAILED")

Log Files:
- Backend: backend_rollback.log
- Worker: worker_rollback.log
- Frontend: frontend_rollback.log

Recovery Actions:
1. Review log files for any issues
2. Run health check: ./scripts/health_check.sh
3. Monitor services for stability
4. If issues persist, check emergency backup: $EMERGENCY_BACKUP
EOF

echo "✅ Rollback report created: rollback_report.txt"

# Final status
echo ""
echo "🎯 ROLLBACK SUMMARY:"
echo "========================================"

if [ "$HEALTH_OK" = true ]; then
    echo "🎉 ROLLBACK SUCCESSFUL!"
    echo "✅ All services restored and running"
    echo "📊 System Status:"
    echo "   Backend: http://localhost:8000 (PID: $BACKEND_PID)"
    echo "   Worker: PID $WORKER_PID"
    echo "   Frontend: http://localhost:3001 (PID: $FRONTEND_PID)"
    echo ""
    echo "🔍 Next Steps:"
    echo "   1. Run: ./scripts/health_check.sh"
    echo "   2. Monitor logs for stability"
    echo "   3. Test critical functionality"
else
    echo "⚠️ ROLLBACK COMPLETED WITH ISSUES"
    echo "❌ Some services may not be functioning correctly"
    echo "🆘 EMERGENCY ACTIONS REQUIRED:"
    echo "   1. Check log files: backend_rollback.log, worker_rollback.log"
    echo "   2. Run: ./scripts/health_check.sh"
    echo "   3. Consider manual service restart"
    echo "   4. Emergency backup available: $EMERGENCY_BACKUP"
fi

echo ""
echo "📞 Emergency contacts and procedures:"
echo "   - Check all logs in current directory"
echo "   - Emergency backup: $EMERGENCY_BACKUP"
echo "   - Original backup: $TARGET_BACKUP"

exit $([ "$HEALTH_OK" = true ] && echo 0 || echo 1)

