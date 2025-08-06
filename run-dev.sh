#!/bin/bash

# ⚠️  WARNING: Worker se spouští výhradně přes master_worker_manager.sh
# ⚠️  TENTO SKRIPT NESPOUŠTÍ TEMPORAL WORKER!
# ⚠️  Pro worker použij: ./master_worker_manager.sh start

echo "🚀 Spouštím SEO Farm Orchestrator: frontend + backend..."

# Spuštění backendu (FastAPI)
(cd backend && uvicorn main:app --port 8000 --reload) &

# Spuštění frontend (Next.js)
(cd web-frontend && NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev -- --port 3001) &

# Čekání na všechny procesy
wait 