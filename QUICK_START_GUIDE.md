# ⚡ QUICK START GUIDE

## 🚀 **1-MINUTE SETUP**

### Lokální Development (teď):
```bash
source local_env_setup.sh && start_worker
```

### Production Server:
```bash
source production_env_setup.sh && start_production_worker
```

## 📋 **DOSTUPNÉ PŘÍKAZY:**

### Development Aliasy:
- `start_worker` → Spustí worker
- `stop_worker` → Zastaví worker  
- `restart_worker` → Restartuje worker
- `status_worker` → Status workera
- `health_worker` → Health check

### Production Aliasy:
- `start_production_worker` → Spustí production worker
- `stop_production_worker` → Zastaví production worker
- `restart_production_worker` → Restartuje production worker  
- `status_production_worker` → Status production workera
- `health_production_worker` → Health check production workera

## 🔄 **PŘEPÍNÁNÍ PROSTŘEDÍ:**

```bash
# Development
source local_env_setup.sh

# Production  
source production_env_setup.sh

# Check current environment
echo "Current: $ENVIRONMENT"
```

## 📊 **MONITORING:**

```bash
# Status
status_worker

# Health check
health_worker

# Real-time logs
tail -f ./worker.log

# Environment info
./master_worker_manager_production.sh env
```

## 🚨 **TROUBLESHOOTING:**

```bash
# Worker neběží?
restart_worker

# Duplicitní procesy?
stop_worker && start_worker

# Chyba v konfiguraci?
./master_worker_manager_production.sh env
```

**🎯 To je vše! Worker je připraven k použití.**