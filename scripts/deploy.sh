#!/bin/bash
# 🚀 MASTER DEPLOYMENT SCRIPT
# Usage: ./scripts/deploy.sh [production|staging]

set -e  # Exit on any error

ENVIRONMENT=${1:-production}
TARGET_SERVER="root@91.99.210.104"
PROJECT_DIR="/root/seo-farm-orchestrator"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🚀 STARTING DEPLOYMENT TO: $ENVIRONMENT"
echo "📅 Timestamp: $TIMESTAMP"
echo "🎯 Target: $TARGET_SERVER:$PROJECT_DIR"

# Step 1: Pre-deployment validation
echo ""
echo "1️⃣ PRE-DEPLOYMENT CHECKS..."
if [ -f "scripts/pre_deploy_checks.sh" ]; then
    ./scripts/pre_deploy_checks.sh || {
        echo "❌ Pre-deployment checks failed!"
        exit 1
    }
else
    echo "⚠️ Pre-deployment checks skipped (script not found)"
fi

# Step 2: Code synchronization
echo ""
echo "2️⃣ SYNCHRONIZING CODE..."
echo "🔄 Uploading files to server..."

# Create backup on server first
ssh $TARGET_SERVER "
if [ -d '$PROJECT_DIR' ]; then
    echo '📦 Creating backup...'
    cp -r '$PROJECT_DIR' '/root/backup_${TIMESTAMP}'
fi
"

# Sync files (excluding unnecessary directories)
rsync -avz --delete \
    --exclude='venv/' \
    --exclude='node_modules/' \
    --exclude='.git/' \
    --exclude='*.log' \
    --exclude='outputs/' \
    --exclude='__pycache__/' \
    --exclude='.next/' \
    . $TARGET_SERVER:$PROJECT_DIR/

echo "✅ Code synchronized successfully"

# Step 3: Remote deployment execution
echo ""
echo "3️⃣ REMOTE DEPLOYMENT EXECUTION..."
ssh $TARGET_SERVER "cd $PROJECT_DIR && chmod +x scripts/*.sh && ./scripts/remote_deploy.sh $ENVIRONMENT" || {
    echo "❌ Remote deployment failed!"
    echo "🔄 Attempting rollback..."
    ssh $TARGET_SERVER "
    if [ -d '/root/backup_${TIMESTAMP}' ]; then
        rm -rf '$PROJECT_DIR'
        mv '/root/backup_${TIMESTAMP}' '$PROJECT_DIR'
        echo '✅ Rollback completed'
    fi
    "
    exit 1
}

# Step 4: Health validation
echo ""
echo "4️⃣ POST-DEPLOYMENT HEALTH CHECK..."
sleep 15  # Give services time to start

ssh $TARGET_SERVER "cd $PROJECT_DIR && ./scripts/health_check.sh" || {
    echo "❌ Health check failed!"
    echo "🔄 Attempting rollback..."
    ssh $TARGET_SERVER "
    if [ -d '/root/backup_${TIMESTAMP}' ]; then
        rm -rf '$PROJECT_DIR'
        mv '/root/backup_${TIMESTAMP}' '$PROJECT_DIR'
        cd '$PROJECT_DIR'
        ./scripts/remote_deploy.sh $ENVIRONMENT
        echo '✅ Rollback completed'
    fi
    "
    exit 1
}

# Step 5: Cleanup
echo ""
echo "5️⃣ CLEANUP..."
ssh $TARGET_SERVER "
# Keep only last 3 backups
ls -dt /root/backup_* 2>/dev/null | tail -n +4 | xargs rm -rf 2>/dev/null || true
echo '✅ Old backups cleaned up'
"

echo ""
echo "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "📊 Summary:"
echo "   Environment: $ENVIRONMENT"
echo "   Timestamp: $TIMESTAMP"
echo "   Server: $TARGET_SERVER"
echo "   Backup: /root/backup_${TIMESTAMP}"
echo ""
echo "🔗 Access URLs:"
echo "   Backend API: http://91.99.210.104:8000"
echo "   Frontend: http://91.99.210.104:3001"
echo "   Health Check: curl http://91.99.210.104:8000/health"

