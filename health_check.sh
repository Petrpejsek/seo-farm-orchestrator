#!/bin/bash
# Health check script pro SEO Farm systém

echo "🏥 SEO FARM HEALTH CHECK"
echo "========================"

# Temporal Server
echo -n "Temporal Server: "
if curl -s http://localhost:8233 >/dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ NEDOSTUPNÝ"
    exit 1
fi

# Backend API
echo -n "Backend API: "
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ NEDOSTUPNÝ" 
    exit 1
fi

# Worker Process
echo -n "Worker Process: "
if pgrep -f "production_worker.py" >/dev/null 2>&1; then
    echo "✅ BĚŽÍ"
else
    echo "❌ NEBĚŽÍ"
    exit 1
fi

# Recent Activity (last 5 minutes)
echo -n "Recent Activity: "
if find outputs/ -name "*.json" -mmin -5 2>/dev/null | head -1 >/dev/null; then
    echo "✅ AKTIVNÍ"
else
    echo "⚠️ ŽÁDNÁ AKTIVITA (5 min)"
fi

# Disk Space
echo -n "Disk Space: "
disk_usage=$(df -h . | awk 'NR==2{print $5}' | sed 's/%//')
if [ "$disk_usage" -lt 90 ]; then
    echo "✅ OK (${disk_usage}%)"
else
    echo "⚠️ VYSOKÉ VYUŽITÍ (${disk_usage}%)"
fi

echo "========================"
echo "✅ VŠECHNY KONTROLY DOKONČENY"