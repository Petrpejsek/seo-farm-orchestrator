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
