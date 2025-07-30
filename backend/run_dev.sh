#!/bin/bash

# SEO Farm Orchestrator Backend - Development Server
echo "🚀 Spouštím SEO Farm Backend server..."

# Kontrola virtuálního prostředí
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtuální prostředí není aktivní. Aktivujte ho pomocí:"
    echo "   source .venv/bin/activate"
    echo ""
fi

# Načtení .env souboru pokud existuje
if [ -f .env ]; then
    echo "📄 Načítám .env soubor..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Kontrola TEMPORAL_HOST
if [[ -z "$TEMPORAL_HOST" ]]; then
    echo "⚠️  TEMPORAL_HOST není nastaveno, používám default: localhost:7233"
    export TEMPORAL_HOST="localhost:7233"
fi

# Spuštění FastAPI serveru
echo "🌐 FastAPI server běží na: http://localhost:8000"
echo "📚 API dokumentace: http://localhost:8000/docs"
echo "🔍 Health check: http://localhost:8000/health"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload 