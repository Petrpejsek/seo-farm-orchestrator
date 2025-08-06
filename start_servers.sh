#!/bin/bash

# 🚀 SEO Farm Orchestrator - Start Script
# ⚠️  WARNING: Worker se spouští výhradně přes master_worker_manager.sh
# ⚠️  TENTO SKRIPT NESPOUŠTÍ TEMPORAL WORKER!
# ⚠️  Pro worker použij: ./master_worker_manager.sh start

echo "🔥 Spouštím SEO Farm Orchestrator..."

# Zastavení starých procesů
echo "🧹 Zastavuji staré procesy..."
pkill -f uvicorn 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
sleep 2

# Aktivace virtual environment
echo "🐍 Aktivuji Python venv..."
source venv/bin/activate

# Spuštění backend serveru
echo "⚙️ Spouštím Backend (FastAPI) na portu 8000..."
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "✅ Backend PID: $BACKEND_PID"
cd ..

# Čekání na backend
echo "⏳ Čekám na backend startup..."
sleep 8

# Test backend
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend je AKTIVNÍ na http://localhost:8000"
else
    echo "❌ Backend selhal!"
    exit 1
fi

# Spuštění frontend serveru
echo "🎨 Spouštím Frontend (Next.js) na portu 3001..."
cd web-frontend
npm run dev -- -p 3001 &
FRONTEND_PID=$!
echo "✅ Frontend PID: $FRONTEND_PID"
cd ..

# Čekání na frontend
echo "⏳ Čekám na frontend startup..."
sleep 10

# Test frontend
if curl -s http://localhost:3001 > /dev/null; then
    echo "✅ Frontend je AKTIVNÍ na http://localhost:3001"
else
    echo "❌ Frontend selhal!"
    exit 1
fi

echo ""
echo "🎉 VŠECHNO JE SPUŠTĚNO!"
echo "📱 Frontend: http://localhost:3001"
echo "🔧 Backend:  http://localhost:8000"
echo "📋 API Docs: http://localhost:8000/docs"
echo ""
echo "💾 PIDs: Backend=$BACKEND_PID, Frontend=$FRONTEND_PID"
echo "🛑 Pro zastavení: pkill -f uvicorn && pkill -f 'next dev'"
echo ""
echo "✨ Enjoy coding!"

# Keep script running
wait