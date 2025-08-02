# 🏭 PRODUKČNÍ TEMPORAL WORKER - DEPLOYMENT GUIDE

Kompletní návod pro nasazení stabilního SEO orchestrátoru v produkčním prostředí.

## 📋 ARCHITEKTURA SYSTÉMU

### Komponenty

```
🏭 PRODUCTION STACK
├── 🔧 config.py              # Centralizovaná konfigurace
├── 📝 logger.py              # Jednotné logování s rotací
├── 🛡️ activity_wrappers.py   # Bezpečné wrappery pro aktivity  
├── 🚀 production_worker.py   # Hlavní produkční worker
└── 📁 activities/
    └── 🛡️ safe_assistant_activities.py  # Bezpečné aktivity
```

### Flow procesu

```
1. 📥 WORKFLOW REQUEST (AssistantPipelineWorkflow)
   ↓
2. 🔄 LOAD_ASSISTANTS (load_assistants_from_database)
   ↓
3. 🔁 FOR EACH ASSISTANT:
   ├── 🛡️ Safe wrapper aktivace
   ├── ⚡ Heartbeat před LLM voláním
   ├── 🤖 LLM API call (OpenAI/Claude/Gemini)
   ├── 📊 Output standardization
   └── 📝 Structured logging
   ↓
4. ✅ WORKFLOW COMPLETION
```

## 🚀 RYCHLÉ SPUŠTĚNÍ

### 1. Prerekvizity
```bash
# Python 3.8+, aktivní venv
source venv/bin/activate

# Temporal server běží
temporal server start-dev &

# Backend API běží 
cd backend && uvicorn main:app --port 8000 &
```

### 2. Spuštění produkčního workera
```bash
# Z root adresáře projektu
export API_BASE_URL=http://localhost:8000
python production_worker.py
```

### 3. Test pipeline
```bash
# Přes Temporal UI: http://localhost:8233
# Workflow: AssistantPipelineWorkflow
# Args: ["test topic", "project_id", "csv_data", "2025-01-31"]
```

## ⚙️ KONFIGURACE

### Environment Variables
```bash
# Temporal
TEMPORAL_HOST=localhost:7233          # Default: localhost:7233
TEMPORAL_NAMESPACE=default            # Default: default

# Backend API
API_BASE_URL=http://localhost:8000    # POVINNÉ

# Logging
LOG_LEVEL=INFO                        # DEBUG|INFO|WARNING|ERROR
```

### config.py nastavení
```python
# Timeouty
default_timeout = 600s         # 10 minut na aktivitu
heartbeat_timeout = 180s       # 3 minuty heartbeat

# LLM
default_temperature = 0.7
default_max_tokens = None      # Neomezeno

# Retry
retry_attempts = 3
retry_backoff = 2.0           # Exponential
```

## 📝 LOGOVÁNÍ

### Struktura logů
```
worker_production.log          # Hlavní log (rotace 10MB, 5 backupů)
├── 🚀 ACTIVITY START: activity_name
├── 🤖 LLM REQUEST: provider/model  
├── 📨 LLM RESPONSE: provider (chars in Xs)
├── ✅ ACTIVITY SUCCESS: activity_name
└── ❌ ACTIVITY ERROR: activity_name (s traceback)
```

### Log level guide
- `DEBUG`: Detailní LLM inputs/outputs
- `INFO`: Průběh aktivit a workflow (default)
- `WARNING`: Neočekávané situace, ale systém pokračuje
- `ERROR`: Chyby, které jsou zachycené a vyřešené
- `CRITICAL`: Systémové selhání

## 🛡️ BEZPEČNOSTNÍ FUNKCE

### Error Handling
```python
✅ Každá aktivita má @safe_activity wrapper
✅ LLM volání mají retry logiku (3x s exponential backoff)
✅ Standardizované error response formáty
✅ Graceful shutdown při SIGINT/SIGTERM
✅ Input validace pro všechny aktivity
```

### Monitoring
```python
✅ Heartbeat každých 30s během LLM volání
✅ Timeout protection (10 min default)
✅ Structured logging pro alerting
✅ Health check endpoint
```

## 🔧 TROUBLESHOOTING

### Worker se nespustí
```bash
# 1. Zkontroluj Temporal server
curl http://localhost:8233

# 2. Zkontroluj backend API
curl http://localhost:8000/health

# 3. Zkontroluj environment variables
echo $API_BASE_URL

# 4. Zkontroluj logs
tail -f worker_production.log
```

### Pipeline selhává
```bash
# 1. Zkontroluj konkrétní aktivitu v logu
grep "ACTIVITY ERROR" worker_production.log

# 2. Zkontroluj LLM API klíče
curl http://localhost:8000/api-keys/openai

# 3. Temporal UI debugging
# http://localhost:8233 → Workflows → [workflow_id] → Event History
```

### Běžné chyby
```
❌ "API_BASE_URL není nastavena"
   → export API_BASE_URL=http://localhost:8000

❌ "Temporal server connection failed"  
   → temporal server start-dev &

❌ "Asistent nemá název - databáze poškozená"
   → Oprav NULL názvy v DB: UPDATE Assistant SET name='...' WHERE name IS NULL

❌ "LLM selhalo po 3 pokusech"
   → Zkontroluj API klíče, rate limits, model availability
```

## 🚀 PRODUKČNÍ DEPLOYMENT

### Systemd Service
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
ExecStart=/opt/seo-orchestrator/venv/bin/python production_worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Docker (alternativa)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "production_worker.py"]
```

### Health Check Script
```bash
#!/bin/bash
# health_check.sh
python -c "
import asyncio
from production_worker import health_check
result = asyncio.run(health_check())
exit(0 if result else 1)
"
```

## 📊 MONITORING & ALERTING

### Metriky k monitorování
```
✅ Worker uptime
✅ Workflow success/failure rate  
✅ Average activity duration
✅ LLM API response times
✅ Error rate po providerech
✅ Queue depth
```

### Alerting pravidla
```
🚨 Worker down > 1 min
🚨 Error rate > 10% za 5 min  
🚨 LLM timeout > 50% za 10 min
⚠️ Workflow duration > 20 min
⚠️ Queue depth > 10 items
```

## 🔄 UPDATES & MAINTENANCE

### Bezpečný update
```bash
# 1. Graceful shutdown (SIGTERM)
kill -TERM $(pgrep -f production_worker.py)

# 2. Update kódu
git pull origin main

# 3. Restart
python production_worker.py
```

### Monitoring při update
```bash
# Watch logy během restartu
tail -f worker_production.log | grep -E "(ERROR|CRITICAL|START|SHUTDOWN)"
```

---

## 📞 SUPPORT

Při problémech zkontrolujte:
1. `worker_production.log` pro detailní error info
2. Temporal UI (http://localhost:8233) pro workflow debugging  
3. Backend API health (http://localhost:8000/health)
4. Database connectivity (Prisma)

**🏆 SYSTÉM JE PŘIPRAVEN PRO PRODUKČNÍ NASAZENÍ!**