# SEO Farm Orchestrator Backend

🚀 **FastAPI backend s Temporal.io integrací pro SEO content generation**

## 📋 Přehled

Backend poskytuje REST API endpoint pro spouštění SEO pipeline workflow přes Temporal.io orchestrator.

## ⚙️ Instalace

### 1. Python prostředí
```bash
# Vytvořte virtuální prostředí v root adresáři
cd seo-farm-orchestrator
python3.11 -m venv .venv
source .venv/bin/activate

# Instalace závislostí
cd backend
pip install -e .
```

### 2. Environment konfigurace
Vytvořte `.env` soubor v root adresáři (`seo-farm-orchestrator/.env`):
```ini
# Temporal konfigurace
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=default

# OpenAI konfigurace (pro workflow aktivity)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
OPENAI_ASSISTANT_ID=asst_xxxxxxxxxxxxxxxxxxxxx
```

## 🚀 Spuštění

### Development server
```bash
cd backend
./run_dev.sh
```

Nebo manuálně:
```bash
cd backend
uvicorn main:app --port 8000 --reload
```

### Dostupné endpointy
- **API server**: http://localhost:8000
- **API dokumentace**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

## 📡 API Endpoints

### POST /api/pipeline-run
Spustí SEO pipeline workflow.

**Request:**
```json
{
  "topic": "AI nástroje pro marketing",
  "csv": {
    "name": "topics.csv",
    "content": "QUkgbsOhc3Ryb2plClNFTyBzdHJhdGVnaWU="
  }
}
```

**Response:**
```json
{
  "status": "started",
  "workflow_id": "seo_pipeline_ai_nastroje_1234567890",
  "run_id": "abc123-def456-ghi789"
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "seo-farm-backend"
}
```

## 🔧 Závislosti

- **FastAPI** - REST API framework
- **Uvicorn** - ASGI server
- **Temporalio** - Temporal.io Python SDK
- **Python-dotenv** - Environment variables

## 🐛 Troubleshooting

### Temporal connection error
```bash
# Ujistěte se, že Temporal server běží
docker-compose up -d

# Kontrola Temporal UI
open http://localhost:8081
```

### Import errors
```bash
# Ujistěte se, že jste v backend/ adresáři
cd backend

# A že máte aktivní virtuální prostředí
source ../.venv/bin/activate
``` 