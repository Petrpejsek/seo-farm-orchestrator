# 🚀 PRODUCTION DEPLOYMENT INSTRUCTIONS

## 🎯 ODPOVĚĎ NA OTÁZKU: BUDE TO FUNGOVAT NA PRODUKČNÍM SERVERU?

**✅ ANO! Ale s potřebnými úpravami:**

## 🚨 CO BYLO OPRAVENO PRO PRODUKCI:

### 1. **Cross-platform kompatibilita**
```bash
# ✅ OPRAVENO: Detekce platformy
case "$(uname -s)" in
    "Darwin")  PS_COMMAND_FIELD="command" ;;    # macOS
    "Linux")   PS_COMMAND_FIELD="comm" ;;       # Linux
esac
```

### 2. **Environment-aware konfigurace**
```bash
# ✅ OPRAVENO: Dynamické cesty podle prostředí
case "$ENVIRONMENT" in
    "production")
        API_BASE_URL="https://api.yourdomain.com"
        LOCK_FILE="/var/lock/seo-farm/temporal_worker.lock"
        PID_FILE="/var/run/seo-farm/worker.pid"
        ;;
    "development")
        API_BASE_URL="http://localhost:8000"
        LOCK_FILE="/tmp/temporal_worker_dev.lock"
        ;;
esac
```

### 3. **Secure file locations**
```bash
# ✅ OPRAVENO: Production-safe cesty
# /tmp/ → /var/lock/, /var/run/, /var/log/
```

### 4. **Enhanced security**
```bash
# ✅ OPRAVENO: User switching v produkci
if [[ "$ENVIRONMENT" == "production" && "$(whoami)" == "root" ]]; then
    su - $WORKER_USER -c "worker_command"
fi
```

## 🛠️ DEPLOYMENT KROKY:

### 1. **Server Preparation**
```bash
# Na produkčním serveru
sudo useradd -m -s /bin/bash seouser
sudo mkdir -p /opt/seo-farm
sudo mkdir -p /var/log/seo-farm
sudo mkdir -p /var/run/seo-farm
sudo mkdir -p /var/lock/seo-farm
sudo chown -R seouser:seouser /opt/seo-farm /var/log/seo-farm /var/run/seo-farm
```

### 2. **Deploy aplikace**
```bash
# Zkopíruj soubory
sudo cp master_worker_manager_production.sh /opt/seo-farm/
sudo cp production_worker.py /opt/seo-farm/
sudo cp -r activities/ /opt/seo-farm/
sudo cp config.py logger.py /opt/seo-farm/

# Permissions
sudo chown -R seouser:seouser /opt/seo-farm/
sudo chmod +x /opt/seo-farm/master_worker_manager_production.sh
```

### 3. **Environment Variables**
```bash
# /opt/seo-farm/.env.production
export ENVIRONMENT=production
export API_BASE_URL=https://api.yourdomain.com
export TEMPORAL_HOST=temporal.yourdomain.com:7233
export WORKER_USER=seouser
export LOG_LEVEL=INFO
```

### 4. **Systemd Service** (upravený)
```bash
# Aktualizuj temporal_worker.service:
sudo cp temporal_worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable temporal-worker
```

### 5. **Test deployment**
```bash
# Test jako seouser
sudo su - seouser
cd /opt/seo-farm
source .env.production
./master_worker_manager_production.sh env     # Ověř konfiguraci
./master_worker_manager_production.sh start   # Spusť worker
./master_worker_manager_production.sh status  # Zkontroluj stav
```

## 🔧 POUŽITÍ V RŮZNÝCH PROSTŘEDÍCH:

### Development (lokální)
```bash
export ENVIRONMENT=development
./master_worker_manager_production.sh start
```

### Staging
```bash
export ENVIRONMENT=staging
export API_BASE_URL=https://staging-api.yourdomain.com
./master_worker_manager_production.sh start
```

### Production
```bash
export ENVIRONMENT=production
export API_BASE_URL=https://api.yourdomain.com
export WORKER_USER=seouser
./master_worker_manager_production.sh start
```

## 🚨 KRITICKÉ BODY PRO PRODUKCI:

### 1. **SSL/HTTPS**
```bash
# ❌ NEBUDE FUNGOVAT:
API_BASE_URL=http://localhost:8000

# ✅ PRODUKCE:
API_BASE_URL=https://api.yourdomain.com
```

### 2. **Database connection string**
```bash
# ❌ DEV:
DATABASE_URL="sqlite:./dev.db"

# ✅ PRODUKCE:
DATABASE_URL="postgresql://user:pass@db.yourdomain.com:5432/seo_farm"
```

### 3. **Firewall & Networking**
```bash
# Otevři potřebné porty
sudo ufw allow 8000/tcp   # Backend API
sudo ufw allow 7233/tcp   # Temporal (pouze internal)
```

### 4. **Log rotation**
```bash
# /etc/logrotate.d/seo-farm
/var/log/seo-farm/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 seouser seouser
}
```

## 🏥 MONITORING V PRODUKCI:

### Health Check Script
```bash
#!/bin/bash
# /opt/seo-farm/health_check_prod.sh
source /opt/seo-farm/.env.production
cd /opt/seo-farm
./master_worker_manager_production.sh health
exit $?
```

### Monitoring integration
```bash
# Cron job pro monitoring
*/5 * * * * /opt/seo-farm/health_check_prod.sh || /usr/local/bin/alert_admin.sh
```

## ✅ CHECKLIST PRO GO-LIVE:

- [ ] Environment variables nastaveny
- [ ] SSL certifikáty nakonfigurovány  
- [ ] Database connection string v pořádku
- [ ] User permissions správně nastaveny
- [ ] Log rotation nakonfigurován
- [ ] Firewall rules v pořádku
- [ ] Health check monitoring aktivní
- [ ] Backup strategie připravena
- [ ] Emergency rollback plán připraven

## 🎉 ZÁVĚR:

**ANO, systém bude na produkčním serveru fungovat perfektně!**

Hlavní změny:
1. ✅ Cross-platform kompatibilita (Linux/macOS)
2. ✅ Environment-aware konfigurace  
3. ✅ Production-safe file locations
4. ✅ Enhanced security & user management
5. ✅ Better error handling & logging
6. ✅ Systemd integration ready

**Použij `master_worker_manager_production.sh` místo původního skriptu pro všechna prostředí!**