#!/bin/bash

echo "🚀 Spouštím SEO Farm Orchestrator: frontend + backend..."

# Spuštění backendu (FastAPI)
(cd backend && uvicorn main:app --port 8000 --reload) &

# Spuštění frontend (Next.js)
(cd web-frontend && NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev -- --port 3001) &

# Čekání na všechny procesy
wait 