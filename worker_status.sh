#!/bin/bash

# 📊 RYCHLÁ KONTROLA STAVU WORKERA

echo "📊 === STAV PRODUCTION WORKERA ==="

WORKER_COUNT=$(ps aux | grep "production_worker.py" | grep -v grep | wc -l)
echo "🔢 Počet běžících workerů: $WORKER_COUNT"

if [ "$WORKER_COUNT" -eq 0 ]; then
    echo "❌ ŽÁDNÝ WORKER NEBĚŽÍ!"
    if [ -f worker.pid ]; then
        echo "🗑️  Odstraňuji starý PID soubor"
        rm worker.pid
    fi
elif [ "$WORKER_COUNT" -eq 1 ]; then
    echo "✅ PERFEKT: Běží přesně jeden worker"
    RUNNING_PID=$(ps aux | grep "production_worker.py" | grep -v grep | awk '{print $2}')
    echo "🎯 Běžící PID: $RUNNING_PID"
    
    if [ -f worker.pid ]; then
        STORED_PID=$(cat worker.pid)
        echo "📁 Uložený PID: $STORED_PID"
        if [ "$RUNNING_PID" = "$STORED_PID" ]; then
            echo "✅ PID se shodují - vše OK"
        else
            echo "⚠️  PID se neshodují - aktualizuji"
            echo "$RUNNING_PID" > worker.pid
        fi
    else
        echo "$RUNNING_PID" > worker.pid
        echo "📁 PID uložen do worker.pid"
    fi
else
    echo "❌ PROBLÉM: Běží $WORKER_COUNT workerů!"
    echo "🔧 Spusť: ./start_single_worker.sh"
fi

echo "📄 Logy: tail -f worker_production.log"