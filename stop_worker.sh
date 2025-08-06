#!/bin/bash

# 🛑 BEZPEČNÉ UKONČENÍ WORKERA

echo "🛑 === UKONČOVÁNÍ PRODUCTION WORKERA ==="

if [ -f worker.pid ]; then
    PID=$(cat worker.pid)
    echo "📁 Našel jsem PID: $PID"
    
    if ps -p $PID > /dev/null; then
        echo "⏳ Ukončuji worker s PID $PID..."
        kill $PID
        sleep 2
        
        if ps -p $PID > /dev/null; then
            echo "⚠️  Worker neodpovídá, používám SIGKILL..."
            kill -9 $PID
            sleep 1
        fi
        
        if ps -p $PID > /dev/null; then
            echo "❌ CHYBA: Worker stále běží!"
        else
            echo "✅ Worker úspěšně ukončen"
        fi
    else
        echo "⚠️  Worker s PID $PID už neběží"
    fi
    
    rm worker.pid
    echo "🗑️  PID soubor odstraněn"
else
    echo "⚠️  Soubor worker.pid nenalezen"
fi

# Kontrola všech workerů
REMAINING=$(ps aux | grep "production_worker.py" | grep -v grep | wc -l)
if [ "$REMAINING" -gt 0 ]; then
    echo "❌ Stále běží $REMAINING workerů, ukončuji všechne..."
    ps aux | grep "production_worker.py" | grep -v grep | awk '{print $2}' | xargs kill -9
    sleep 1
fi

FINAL_COUNT=$(ps aux | grep "production_worker.py" | grep -v grep | wc -l)
echo "📊 Finální stav: $FINAL_COUNT workerů běží"

if [ "$FINAL_COUNT" -eq 0 ]; then
    echo "🎉 VŠICHNI WORKERI ÚSPĚŠNĚ UKONČENI"
else
    echo "❌ CHYBA: Stále běží workeri!"
fi