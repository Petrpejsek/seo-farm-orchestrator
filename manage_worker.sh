#!/bin/bash
# Bezpečný script pro správu Temporal Workeru

# Název worker procesu
WORKER_NAME="production_worker.py"
PID_FILE="worker.pid"
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"

# Funkce pro kontrolu běžících workerů
check_workers() {
    echo "🔍 Kontroluji běžící workery..."
    RUNNING_WORKERS=$(ps aux | grep "$WORKER_NAME" | grep -v grep | wc -l | tr -d ' ')
    echo "📊 Nalezeno workerů: $RUNNING_WORKERS"
    echo "$RUNNING_WORKERS"
}

# Funkce pro zastavení VŠECH workerů
stop_all_workers() {
    echo "🛑 Zastavuji VŠECHNY worker procesy..."
    PIDS=$(ps aux | grep "$WORKER_NAME" | grep -v grep | awk '{print $2}')
    if [ -z "$PIDS" ]; then
        echo "✅ Žádné workery k zastavení."
    else
        echo "💀 Ukončuji procesy: $PIDS"
        echo "$PIDS" | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
    
    # Ověř že jsou všichni ukončeni
    REMAINING_WORKERS=$(check_workers | tail -1)
    if [ "$REMAINING_WORKERS" -gt 0 ]; then
        echo "❌ CHYBA: Někteří workery stále běží!"
        ps aux | grep "$WORKER_NAME" | grep -v grep
        exit 1
    fi
    
    # Vymaž PID file
    rm -f "$PID_FILE"
    echo "✅ Všichni workery ukončeni"
}

# Funkce pro spuštění POUZE JEDNOHO workera
start_single_worker() {
    echo "🚀 Spouštím JEDEN worker..."
    
    # Ověř že žádný worker neběží
    EXISTING_WORKERS=$(check_workers | tail -1)
    if [ "$EXISTING_WORKERS" -gt 0 ]; then
        echo "❌ CHYBA: Už nějaký worker běží! Použij 'restart' místo 'start'"
        exit 1
    fi
    
    # Ověř prostředí
    if [ -z "$API_BASE_URL" ]; then
        echo "❌ CHYBA: API_BASE_URL není nastavena!"
        exit 1
    fi
    
    echo "🔗 API_BASE_URL: $API_BASE_URL"
    
    # Aktivace venv a spuštění
    source venv/bin/activate
    env API_BASE_URL="$API_BASE_URL" python "$WORKER_NAME" &
    WORKER_PID=$!
    echo "$WORKER_PID" > "$PID_FILE"
    echo "✅ Worker spuštěn s PID: $WORKER_PID"
    sleep 5 # Dej mu čas na start
    
    # Ověř že běží pouze JEDEN proces
    RUNNING_COUNT=$(check_workers | tail -1)
    if [ "$RUNNING_COUNT" -ne 1 ]; then
        echo "❌ CHYBA: Worker se nespustil správně nebo je jich více než jeden!"
        ps aux | grep "$WORKER_NAME" | grep -v grep
        exit 1
    fi
    echo "✅ Worker spuštěn úspěšně (PID: $WORKER_PID)"
    echo "📋 Pro kontrolu: ps aux | grep production_worker | grep -v grep"
}

# Funkce pro restart workera
restart_worker() {
    echo "🔄 RESTART: Zastavuji všechny a spouštím jeden worker..."
    stop_all_workers
    start_single_worker
    echo "✅ Worker restartován."
}

# Funkce pro zobrazení stavu
status_worker() {
    echo "📊 STAV WORKER PROCESŮ:"
    echo "======================"
    
    WORKER_COUNT=$(check_workers | tail -1)
    
    if [ $WORKER_COUNT -eq 0 ]; then
        echo "✅ Žádné worker procesy"
    elif [ $WORKER_COUNT -eq 1 ]; then
        echo "✅ Správně - POUZE JEDEN worker:"
        ps aux | grep "$WORKER_NAME" | grep -v grep
        if [ -f "$PID_FILE" ]; then
            echo "📁 PID file: $(cat $PID_FILE)"
        fi
    else
        echo "❌ CHYBA: Běží více než jeden worker! ($WORKER_COUNT)"
        ps aux | grep "$WORKER_NAME" | grep -v grep
    fi
}

# Hlavní logika scriptu
case "$1" in
    start)
        start_single_worker
        ;;
    stop)
        stop_all_workers
        ;;
    restart)
        restart_worker
        ;;
    status)
        status_worker
        ;;
    *)
        echo "Použití: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac