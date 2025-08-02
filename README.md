# 🏭 SEO ORCHESTRATOR - Produkční LLM Workflow System

Stabilní orchestrátor pro automatizovanou tvorbu SEO článků postavený na **Temporal.io** s podporou multiple LLM providerů (OpenAI, Claude, Gemini).

## 🚀 RYCHLÉ SPUŠTĚNÍ

### Prerekvizity
```bash
# Python 3.8+
python --version

# Aktivace virtuálního prostředí
source venv/bin/activate

# Instalace závislostí
pip install -r requirements.txt
```

### Spuštění systému
```bash
# 1. Spuštění Temporal serveru
temporal server start-dev &

# 2. Spuštění backend API
cd backend && uvicorn main:app --port 8000 &

# 3. Spuštění produkčního workera
export API_BASE_URL=http://localhost:8000
python worker.py
```

### Monitoring
```bash
# Sledování logů workera
tail -f worker_production.log

# Temporal UI
open http://localhost:8233

# Backend API
curl http://localhost:8000/health
```

## 🏗️ ARCHITEKTURA SYSTÉMU

### 📁 Struktura projektu
```
🏭 PRODUKČNÍ ARCHITEKTURA:
├── 🚀 worker.py                     # Hlavní entrypoint workera
├── 🏭 production_worker.py          # Produkční worker logika
├── 🔧 config.py                     # Centralizovaná konfigurace
├── 📝 logger.py                     # Strukturované logování
├── 🛡️ activity_wrappers.py          # Bezpečné wrappery pro aktivity
├── 📋 requirements.txt              # Python závislosti
├── 📚 PRODUCTION_README.md          # Detailní deployment guide
├── 🧪 test_production_worker.py     # Test suite
├── 📁 activities/
│   ├── 🛡️ safe_assistant_activities.py  # Bezpečné LLM aktivity
│   └── 📄 [originální aktivity...]
├── 📁 workflows/
│   ├── 🔄 assistant_pipeline_workflow.py
│   └── 📄 [ostatní workflows...]
├── 📁 backend/
│   ├── 🌐 main.py                   # FastAPI aplikace
│   ├── 🔗 temporal_client.py        # Temporal klient
│   ├── 📁 llm_clients/              # LLM provideri
│   └── 📁 api/                      # REST API endpoints
└── 📁 web-frontend/                 # React.js frontend
```

### 🔄 Workflow Pipeline
```
1. 📥 AssistantPipelineWorkflow REQUEST
   ↓
2. 🔄 load_assistants_from_database
   ↓
3. 🔁 FOR EACH ASSISTANT:
   ├── 🛡️ Safe wrapper aktivace (@safe_activity)
   ├── ⚡ Heartbeat před LLM voláním
   ├── 🤖 LLM API call (OpenAI/Claude/Gemini)
   ├── 🔄 Retry logic (3x exponential backoff)
   ├── 📊 Output standardization & validation
   └── 📝 Structured logging
   ↓
4. ✅ WORKFLOW COMPLETION
```

## 🛡️ BEZPEČNOSTNÍ FUNKCE

### ✅ Implementované bezpečnostní funkce:
- **🛡️ Crash Protection** - Každá aktivita má `@safe_activity` wrapper
- **📊 Structured Logging** - Všechny chyby s traceback do `worker_production.log`
- **⚡ Graceful Shutdown** - SIGINT/SIGTERM handling s cleanup
- **🔄 Retry Logic** - LLM volání s exponential backoff (3x)
- **⚙️ Centralized Config** - Vše v `config.py` a environment variables
- **⚡ Heartbeat Protection** - Prevence timeouts během LLM volání
- **🧪 Input Validation** - Validace všech vstupních parametrů

### 📊 Monitoring features:
```python
✅ Health check endpoints
✅ Structured logs pro alerting  
✅ Error rate tracking
✅ Duration monitoring
✅ LLM API response tracking
✅ Activity success/failure metrics
```

## ⚙️ KONFIGURACE

### Environment Variables
```bash
# Povinné
export API_BASE_URL=http://localhost:8000

# Volitelné
export TEMPORAL_HOST=localhost:7233
export TEMPORAL_NAMESPACE=default
export LOG_LEVEL=INFO
```

### config.py nastavení
```python
# Timeouty
default_timeout = 600s         # 10 minut na aktivitu
heartbeat_timeout = 180s       # 3 minuty heartbeat

# LLM konfigurace
default_temperature = 0.7
default_max_tokens = None      # Neomezeno

# Retry policy
retry_attempts = 3
retry_backoff = 2.0           # Exponential backoff
```

## 🧪 TESTOVÁNÍ

### Unit testy
```bash
# Test všech modulů
python test_production_worker.py

# Pytest (pokud je nainstalován)
pytest tests/ -v
```

### Funkční test pipeline
```bash
# 1. Spusť worker
python worker.py

# 2. Spusť workflow přes Temporal UI
# http://localhost:8233
# Workflow: AssistantPipelineWorkflow
# Args: ["test topic", "project_id", "", "2025-01-31"]
```

## 🚀 PRODUKČNÍ DEPLOYMENT

### Option 1: Systemd Service
```ini
# /etc/systemd/system/seo-worker.service
[Unit]
Description=SEO Orchestrator Worker
After=network.target

[Service]
Type=simple
User=seo-user
WorkingDirectory=/opt/seo-orchestrator
Environment=API_BASE_URL=https://api.yourdomain.com
Environment=TEMPORAL_HOST=temporal.yourdomain.com:7233
Environment=LOG_LEVEL=INFO
ExecStart=/opt/seo-orchestrator/venv/bin/python worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Aktivace
sudo systemctl enable seo-worker
sudo systemctl start seo-worker
sudo systemctl status seo-worker
```

### Option 2: Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV API_BASE_URL=http://backend:8000
ENV TEMPORAL_HOST=temporal:7233

CMD ["python", "worker.py"]
```

```bash
# Build & Run
docker build -t seo-orchestrator .
docker run -e API_BASE_URL=http://backend:8000 seo-orchestrator
```

### Option 3: PM2 (Pro development)
```bash
# Instalace PM2
npm install -g pm2

# Spuštění
pm2 start worker.py --name seo-worker --interpreter python

# Monitoring
pm2 status
pm2 logs seo-worker
```

## 📊 MONITORING & ALERTING

### Log monitoring
```bash
# Sledování chyb
tail -f worker_production.log | grep "ERROR\|CRITICAL"

# Metriky
grep "ACTIVITY SUCCESS\|ACTIVITY ERROR" worker_production.log | wc -l
```

### Doporučené alerting pravidla
```
🚨 Worker down > 1 min
🚨 Error rate > 10% za 5 min
🚨 LLM timeout > 50% za 10 min  
⚠️ Workflow duration > 20 min
⚠️ Queue depth > 10 items
```

## 🔧 TROUBLESHOOTING

### Běžné problémy

#### Worker se nespustí
```bash
# Zkontroluj prerekvizity
python worker.py  # Má vestavěnou diagnostiku

# Ruční kontrola
curl http://localhost:8233          # Temporal server
curl http://localhost:8000/health   # Backend API
echo $API_BASE_URL                  # Environment
```

#### Pipeline selhává
```bash
# Logy s detaily
grep "ACTIVITY ERROR" worker_production.log

# Temporal UI debugging
open http://localhost:8233

# LLM API klíče
curl http://localhost:8000/api-keys/openai
```

#### Performance problémy
```bash
# Analýza duration
grep "Duration:" worker_production.log | sort -n

# LLM response times
grep "LLM RESPONSE:" worker_production.log
```

## 🤝 DEVELOPMENT

### Přidání nové aktivity
```python
# activities/my_new_activity.py
from activity_wrappers import safe_activity

@safe_activity(name="my_new_activity", timeout_seconds=300)
async def my_new_activity(input_data: dict) -> dict:
    # Tvoje logika zde
    return {"status": "completed", "output": "result"}
```

### Přidání nového LLM providera
```python
# backend/llm_clients/my_provider_client.py
from .base import BaseLLMClient

class MyProviderClient(BaseLLMClient):
    async def chat_completion(self, **kwargs):
        # Implementation
        pass
```

## 📚 DOKUMENTACE

- **📋 PRODUCTION_README.md** - Detailní deployment guide
- **📄 REFACTOR_COMPLETE.md** - Historie refaktoringu
- **🧪 test_production_worker.py** - Příklady testování

## 📞 SUPPORT

**Issues & Chyby:**
1. Zkontroluj `worker_production.log` pro detaily
2. Temporal UI (http://localhost:8233) pro workflow debugging
3. Backend health (http://localhost:8000/health)

**🏆 SYSTÉM JE PLNĚ PŘIPRAVEN PRO PRODUKČNÍ NASAZENÍ!**