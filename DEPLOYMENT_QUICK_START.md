# 🚀 DEPLOYMENT QUICK START GUIDE

## 1. First Time Setup
```bash
./setup_deployment.sh
source deployment_aliases.sh
```

## 2. Deploy to Production
```bash
deploy-prod
# or
./scripts/deploy.sh production
```

## 3. Monitor System Health
```bash
deploy-health
# or
./scripts/health_check.sh
```

## 4. Emergency Rollback
```bash
deploy-rollback
# or
./scripts/rollback.sh
```

## 5. Enable Monitoring
```bash
# Add to crontab
(crontab -l 2>/dev/null; echo "*/5 * * * * $(pwd)/scripts/monitor.sh") | crontab -
```

## 6. Daily Operations
- **Check health**: `deploy-health`
- **View logs**: `tail -f backend_*.log worker_*.log`
- **Monitor**: `deploy-monitor`
- **Deploy**: `deploy-prod`

## Emergency Contacts
- Health Check: `./scripts/health_check.sh`
- Rollback: `./scripts/rollback.sh --force`
- Logs: `/var/log/seo-farm/` or `logs/`
