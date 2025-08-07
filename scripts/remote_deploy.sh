#!/bin/bash
# 🔄 REMOTE DEPLOYMENT EXECUTION SCRIPT
# Runs on the production server

set -e

ENVIRONMENT=${1:-production}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🔄 REMOTE DEPLOYMENT STARTED"
echo "📅 Timestamp: $TIMESTAMP"
echo "🌍 Environment: $ENVIRONMENT"

# Step 1: Service graceful shutdown
echo ""
echo "⏹️ STOPPING SERVICES GRACEFULLY..."

# Function to stop process gracefully
stop_process() {
    local process_name=$1
    local process_pattern=$2
    
    echo "🛑 Stopping $process_name..."
    
    # Find PIDs
    PIDS=$(ps aux | grep "$process_pattern" | grep -v grep | awk '{print $2}' || true)
    
    if [ ! -z "$PIDS" ]; then
        echo "Found PIDs: $PIDS"
        
        # Send TERM signal first
        for pid in $PIDS; do
            kill -TERM $pid 2>/dev/null || true
        done
        
        # Wait 10 seconds
        sleep 10
        
        # Force kill if still running
        for pid in $PIDS; do
            if kill -0 $pid 2>/dev/null; then
                echo "Force killing $pid..."
                kill -KILL $pid 2>/dev/null || true
            fi
        done
        
        echo "✅ $process_name stopped"
    else
        echo "ℹ️ $process_name not running"
    fi
}

# Stop all services
stop_process "Backend" "uvicorn"
stop_process "Worker" "production_worker"
stop_process "Frontend" "npm.*start\|next-server"

# Additional cleanup
sleep 5

# Step 2: Fix import issues automatically
echo ""
echo "🔧 FIXING IMPORT ISSUES..."
find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*" -exec sed -i 's/from api\./from backend.api./g' {} \;
echo "✅ Import issues fixed"

# Step 3: Update dependencies
echo ""
echo "📦 UPDATING DEPENDENCIES..."

# Python dependencies
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
fi

echo "🐍 Installing Python packages..."
pip install -r requirements.txt --upgrade --quiet
echo "✅ Python dependencies updated"

# Node.js dependencies
if [ -d "web-frontend" ] && command -v npm &> /dev/null; then
    echo "📦 Installing Node.js packages..."
    cd web-frontend
    npm install --silent
    echo "🔨 Building frontend..."
    npm run build
    cd ..
    echo "✅ Frontend dependencies updated and built"
else
    echo "⚠️ Frontend directory not found or npm not available"
fi

# Step 4: Database migrations
echo ""
echo "🗄️ RUNNING DATABASE MIGRATIONS..."
if [ -d "backend" ] && command -v npx &> /dev/null; then
    cd backend
    if [ -f "prisma/schema.prisma" ]; then
        echo "🔧 Generating Prisma client..."
        npx prisma generate --quiet
        
        echo "🗄️ Running database migrations..."
        npx prisma migrate deploy || {
            echo "❌ Database migration failed!"
            exit 1
        }
        echo "✅ Database migrations completed"
    else
        echo "⚠️ Prisma schema not found, skipping migrations"
    fi
    cd ..
else
    echo "⚠️ Backend directory not found or npx not available, skipping migrations"
fi

# Step 5: Environment setup
echo ""
echo "⚙️ SETTING UP ENVIRONMENT..."
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
    echo "✅ Environment variables loaded from .env"
else
    echo "⚠️ .env file not found"
fi

# Step 6: Start services in correct order
echo ""
echo "🚀 STARTING SERVICES..."

# Start backend first
echo "🌐 Starting backend..."
nohup python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend_${TIMESTAMP}.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -f -s http://localhost:8000/health >/dev/null 2>&1; then
        echo "✅ Backend is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start within 30 seconds"
        exit 1
    fi
    sleep 2
done

# Start worker second
echo "⚙️ Starting worker..."
nohup python production_worker.py > worker_${TIMESTAMP}.log 2>&1 &
WORKER_PID=$!
echo "✅ Worker started (PID: $WORKER_PID)"

# Start frontend last
if [ -d "web-frontend" ] && command -v npm &> /dev/null; then
    echo "🎨 Starting frontend..."
    cd web-frontend
    nohup npm run start -- -p 3001 > ../frontend_${TIMESTAMP}.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
    echo "✅ Frontend started (PID: $FRONTEND_PID)"
else
    echo "⚠️ Frontend not started (directory not found or npm not available)"
fi

# Step 7: Wait for all services to stabilize
echo ""
echo "⏳ WAITING FOR SERVICES TO STABILIZE..."
sleep 15

# Step 8: Create service status file
echo ""
echo "📋 CREATING SERVICE STATUS..."
cat > service_status.txt << EOF
Deployment completed: $(date)
Environment: $ENVIRONMENT
Backend PID: $BACKEND_PID
Worker PID: $WORKER_PID
Frontend PID: ${FRONTEND_PID:-N/A}
Log files:
- Backend: backend_${TIMESTAMP}.log
- Worker: worker_${TIMESTAMP}.log
- Frontend: frontend_${TIMESTAMP}.log
EOF

echo "✅ REMOTE DEPLOYMENT COMPLETE!"
echo ""
echo "📊 Service Summary:"
echo "   Backend: http://localhost:8000 (PID: $BACKEND_PID)"
echo "   Worker: PID $WORKER_PID"
echo "   Frontend: http://localhost:3001 (PID: ${FRONTEND_PID:-N/A})"
echo ""
echo "📝 Log files created with timestamp: $TIMESTAMP"

