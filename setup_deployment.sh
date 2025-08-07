#!/bin/bash
# 🚀 DEPLOYMENT INFRASTRUCTURE SETUP

echo "🚀 SETTING UP 100% DEPLOYMENT INFRASTRUCTURE"
echo "=============================================="

# Step 1: Validate environment
echo ""
echo "1️⃣ VALIDATING ENVIRONMENT..."

if [ ! -f ".env" ]; then
    echo "❌ .env file missing! Creating from template..."
    echo "DATABASE_URL=\"postgresql://user:password@localhost:5432/seo_farm\"" > .env
    echo "OPENAI_API_KEY=\"your-openai-api-key\"" >> .env
    echo "API_BASE_URL=\"http://localhost:8000\"" >> .env
    echo "⚠️ Please edit .env with your actual values"
fi

if [ ! -f "backend/.env" ]; then
    echo "❌ backend/.env file missing! Creating from template..."
    cp .env backend/.env
fi

echo "✅ Environment files checked"

# Step 2: Setup scripts permissions
echo ""
echo "2️⃣ SETTING UP SCRIPT PERMISSIONS..."
chmod +x scripts/*.sh
chmod +x setup_deployment.sh
echo "✅ All scripts are now executable"

# Step 3: Setup monitoring directories
echo ""
echo "3️⃣ SETTING UP MONITORING INFRASTRUCTURE..."
sudo mkdir -p /var/log/seo-farm || {
    echo "⚠️ Cannot create /var/log/seo-farm (running without sudo)"
    mkdir -p logs
    echo "📁 Using local logs/ directory instead"
}
echo "✅ Monitoring directories ready"

# Step 4: Setup pre-commit hooks
echo ""
echo "4️⃣ SETTING UP PRE-COMMIT HOOKS..."
if [ -d ".git" ]; then
    cp scripts/pre_deploy_checks.sh .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
    echo "✅ Pre-commit hooks installed"
else
    echo "⚠️ Not a git repository, skipping pre-commit hooks"
fi

# Step 5: Test deployment infrastructure
echo ""
echo "5️⃣ TESTING DEPLOYMENT INFRASTRUCTURE..."
echo "🧪 Running pre-deployment checks..."
if ./scripts/pre_deploy_checks.sh; then
    echo "✅ Pre-deployment checks passed"
else
    echo "⚠️ Some pre-deployment checks failed - review output above"
fi

# Step 6: Setup cron job for monitoring (optional)
echo ""
echo "6️⃣ MONITORING SETUP..."
CURRENT_DIR=$(pwd)
CRON_JOB="*/5 * * * * $CURRENT_DIR/scripts/monitor.sh"

echo "📊 To enable automatic monitoring, add this cron job:"
echo "   crontab -e"
echo "   Then add: $CRON_JOB"
echo ""
echo "Or run this command to add it automatically:"
echo "   (crontab -l 2>/dev/null; echo \"$CRON_JOB\") | crontab -"

# Step 7: Create deployment aliases
echo ""
echo "7️⃣ CREATING DEPLOYMENT ALIASES..."
cat > deployment_aliases.sh << 'EOF'
#!/bin/bash
# Deployment aliases for easy access

alias deploy-prod="./scripts/deploy.sh production"
alias deploy-check="./scripts/pre_deploy_checks.sh"
alias deploy-health="./scripts/health_check.sh"
alias deploy-rollback="./scripts/rollback.sh"
alias deploy-monitor="./scripts/monitor.sh"

echo "🚀 Deployment aliases loaded:"
echo "   deploy-prod     - Deploy to production"
echo "   deploy-check    - Run pre-deployment checks"
echo "   deploy-health   - Run health check"
echo "   deploy-rollback - Rollback to previous version"
echo "   deploy-monitor  - Run monitoring check"
EOF

chmod +x deployment_aliases.sh
echo "✅ Deployment aliases created in deployment_aliases.sh"
echo "   Run: source deployment_aliases.sh"

# Step 8: Create quick start guide
echo ""
echo "8️⃣ CREATING QUICK START GUIDE..."
cat > DEPLOYMENT_QUICK_START.md << 'EOF'
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
EOF

echo "✅ Quick start guide created: DEPLOYMENT_QUICK_START.md"

# Summary
echo ""
echo "🎉 DEPLOYMENT INFRASTRUCTURE SETUP COMPLETE!"
echo "=============================================="
echo ""
echo "📋 What's been set up:"
echo "   ✅ Deployment scripts with proper permissions"
echo "   ✅ Pre-deployment validation"
echo "   ✅ Health check system"
echo "   ✅ Intelligent rollback system"
echo "   ✅ Monitoring infrastructure"
echo "   ✅ Environment file templates"
echo "   ✅ Pre-commit hooks (if git repo)"
echo "   ✅ Quick start documentation"
echo ""
echo "🚀 Ready to deploy with:"
echo "   ./scripts/deploy.sh production"
echo ""
echo "📖 For detailed instructions, see:"
echo "   - ULTIMATE_DEPLOYMENT_STRATEGY.md"
echo "   - DEPLOYMENT_QUICK_START.md"
echo ""
echo "🔧 Next steps:"
echo "   1. Edit .env files with your actual values"
echo "   2. Run: source deployment_aliases.sh"
echo "   3. Test: deploy-check"
echo "   4. Deploy: deploy-prod"

