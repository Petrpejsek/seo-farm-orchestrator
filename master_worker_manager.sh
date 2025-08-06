#!/bin/bash

# 🛡️ MASTER TEMPORAL WORKER MANAGER
# ===================================
# Spolehlivý spouštěč jednoho jediného Temporal workeru
# - Atomický lock pomocí flock
# - PID file ochrana
# - Health check mechanismus
# - Graceful shutdown
# 
# POUŽITÍ: ./master_worker_manager.sh [start|stop|restart|status|health]

set -euo pipefail

# 🔧 KONFIGURACE
WORKER_SCRIPT="production_worker.py"
PID_FILE="worker.pid"
LOCK_FILE="/tmp/temporal_worker.lock"
LOG_FILE="worker.log"
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
HEALTH_CHECK_INTERVAL=30  # sekund

# 🎨 BARVY PRO VÝSTUP
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 📝 LOGGING FUNKCE
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1${NC}" | tee -a "$LOG_FILE"
}

# 🔐 FUNKCE PRO ATOMICKÝ LOCK (cross-platform)
acquire_lock() {
    log "Získávám atomický lock..."
    
    # Použijeme mkdir pro atomický lock (funguje všude)
    local lock_dir="${LOCK_FILE}.d"
    local max_wait=30
    local waited=0
    
    while ! mkdir "$lock_dir" 2>/dev/null; do
        if [[ $waited -ge $max_wait ]]; then
            log_error "Worker už běží nebo je uzamčen! (lock dir: $lock_dir)"
            log_error "Pokud jste si jisti, že worker neběží, smažte: $lock_dir"
            log_error "Nebo počkejte, až se lock automaticky uvolní"
            exit 1
        fi
        log "Čekám na uvolnění lock... ($waited/$max_wait s)"
        sleep 1
        ((waited++))
    done
    
    # Uložíme PID do lock directory pro debugging
    echo $$ > "$lock_dir/manager_pid"
    echo "$(date)" > "$lock_dir/locked_at"
    
    log_success "Lock získán úspěšně"
}

release_lock() {
    local lock_dir="${LOCK_FILE}.d"
    if [[ -d "$lock_dir" ]]; then
        rm -rf "$lock_dir"
        log "Lock uvolněn"
    fi
}

# 🔍 PID FILE OCHRANA
validate_pid_file() {
    if [[ ! -f "$PID_FILE" ]]; then
        return 1  # PID file neexistuje
    fi
    
    local pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
    if [[ -z "$pid" ]]; then
        log_warning "PID file je prázdný, odstraňuji..."
        rm -f "$PID_FILE"
        return 1
    fi
    
    # Ověř, zda proces stále existuje
    if ! ps -p "$pid" >/dev/null 2>&1; then
        log_warning "Proces s PID $pid už neexistuje, odstraňuji starý PID file..."
        rm -f "$PID_FILE"
        return 1
    fi
    
    # Ověř, zda to je opravdu náš worker
    if ! ps -p "$pid" -o command= | grep -q "$WORKER_SCRIPT"; then
        log_warning "Proces s PID $pid není náš worker, odstraňuji PID file..."
        rm -f "$PID_FILE"
        return 1
    fi
    
    echo "$pid"
    return 0
}

# 🔍 KONTROLA BĚŽÍCÍCH WORKERŮ
check_running_workers() {
    local count=$(ps aux | grep "$WORKER_SCRIPT" | grep -v grep | wc -l | tr -d ' ')
    echo "$count"
}

get_worker_pids() {
    ps aux | grep "$WORKER_SCRIPT" | grep -v grep | awk '{print $2}' | tr '\n' ' '
}

# 🏥 HEALTH CHECK
health_check() {
    log "Provádím health check..."
    
    # 1. Ověř že worker proces běží
    local worker_count=$(check_running_workers)
    if [[ "$worker_count" -eq 0 ]]; then
        log_error "Health check selhal: Žádný worker proces neběží"
        return 1
    fi
    
    if [[ "$worker_count" -gt 1 ]]; then
        log_error "Health check selhal: Běží více workerů ($worker_count) - to je problém!"
        log_error "Běžící procesy: $(get_worker_pids)"
        return 1
    fi
    
    # 2. Ověř PID file
    local pid=$(validate_pid_file)
    if [[ $? -ne 0 ]]; then
        log_error "Health check selhal: Problém s PID file"
        return 1
    fi
    
    # 3. Ověř API endpoint (pokud je dostupný)
    if command -v curl >/dev/null 2>&1; then
        if curl -s --max-time 5 "$API_BASE_URL/health" >/dev/null 2>&1; then
            log_success "API endpoint je dostupný"
        else
            log_warning "API endpoint nedostupný (možná ještě startuje)"
        fi
    fi
    
    log_success "Health check úspěšný - worker běží správně (PID: $pid)"
    return 0
}

# 🚀 SPUŠTĚNÍ WORKERA
start_worker() {
    log "=== SPOUŠTÍM TEMPORAL WORKER ==="
    
    # Získej atomický lock
    acquire_lock
    
    # Ověř, že žádný worker neběží
    local worker_count=$(check_running_workers)
    if [[ "$worker_count" -gt 0 ]]; then
        log_error "Worker už běží! Nalezeno $worker_count procesů:"
        log_error "$(get_worker_pids)"
        log_error "Použijte 'restart' místo 'start' nebo nejdříve zastavte worker"
        release_lock
        exit 1
    fi
    
    # Ověř PID file
    if validate_pid_file >/dev/null 2>&1; then
        log_error "PID file existuje, ale worker neběží - pravděpodobně dirty shutdown"
        rm -f "$PID_FILE"
    fi
    
    # Ověř prostředí
    if [[ -z "$API_BASE_URL" ]]; then
        log_error "API_BASE_URL není nastavena!"
        release_lock
        exit 1
    fi
    
    if [[ ! -f "$WORKER_SCRIPT" ]]; then
        log_error "Worker script '$WORKER_SCRIPT' neexistuje!"
        release_lock
        exit 1
    fi
    
    log "API_BASE_URL: $API_BASE_URL"
    log "Worker script: $WORKER_SCRIPT"
    
    # Spuštění workera na pozadí
    log "Spouštím worker proces..."
    API_BASE_URL="$API_BASE_URL" nohup python3 "$WORKER_SCRIPT" >> "$LOG_FILE" 2>&1 &
    local worker_pid=$!
    
    # Ulož PID
    echo "$worker_pid" > "$PID_FILE"
    log "PID $worker_pid uložen do $PID_FILE"
    
    # Krátká pauza a ověření
    sleep 3
    if ! kill -0 "$worker_pid" 2>/dev/null; then
        log_error "Worker se nepodařilo spustit!"
        rm -f "$PID_FILE"
        release_lock
        exit 1
    fi
    
    # Health check
    sleep 2
    if health_check; then
        log_success "Worker spuštěn úspěšně!"
        log_success "PID: $worker_pid"
        log_success "Log file: $LOG_FILE"
        log_success "Pro monitoring: tail -f $LOG_FILE"
    else
        log_error "Worker se spustil, ale health check selhal"
        stop_worker
        release_lock
        exit 1
    fi
    
    # Lock zůstává aktivní dokud worker běží
    log_success "=== WORKER ÚSPĚŠNĚ SPUŠTĚN ==="
}

# 🛑 ZASTAVENÍ WORKERA
stop_worker() {
    log "=== ZASTAVUJI TEMPORAL WORKER ==="
    
    # Najdi všechny worker procesy
    local worker_pids=$(get_worker_pids)
    
    if [[ -z "$worker_pids" ]]; then
        log_warning "Žádné worker procesy nenalezeny"
    else
        log "Ukončuji procesy: $worker_pids"
        
        # Graceful shutdown (SIGTERM)
        echo "$worker_pids" | xargs -r kill -TERM 2>/dev/null || true
        
        # Počkej na graceful shutdown
        sleep 5
        
        # Ověř, že jsou ukončeny
        local remaining=$(check_running_workers)
        if [[ "$remaining" -gt 0 ]]; then
            log_warning "Některé procesy stále běží, používám SIGKILL..."
            echo "$worker_pids" | xargs -r kill -9 2>/dev/null || true
            sleep 2
        fi
        
        # Finální ověření
        local final_count=$(check_running_workers)
        if [[ "$final_count" -gt 0 ]]; then
            log_error "KRITICKÉ: Někteří workeri stále běží!"
            ps aux | grep "$WORKER_SCRIPT" | grep -v grep
            exit 1
        fi
        
        log_success "Všechny worker procesy ukončeny"
    fi
    
    # Vyčisti PID file
    if [[ -f "$PID_FILE" ]]; then
        rm -f "$PID_FILE"
        log "PID file smazán"
    fi
    
    # Uvolni lock
    release_lock
    
    log_success "=== WORKER ÚSPĚŠNĚ ZASTAVEN ==="
}

# 🔄 RESTART
restart_worker() {
    log "=== RESTART WORKERA ==="
    stop_worker
    sleep 2
    start_worker
}

# 📊 STATUS
show_status() {
    echo ""
    log "=== STATUS TEMPORAL WORKERA ==="
    echo ""
    
    local worker_count=$(check_running_workers)
    local lock_status="🔓 UNLOCKED"
    local pid_status="📁 Žádný PID file"
    
    # Kontrola lock file
    if [[ -f "$LOCK_FILE" ]]; then
        lock_status="🔒 LOCKED"
    fi
    
    # Kontrola PID file
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE" 2>/dev/null || echo "neplatný")
        if validate_pid_file >/dev/null 2>&1; then
            pid_status="📁 PID: $pid (aktivní)"
        else
            pid_status="📁 PID: $pid (mrtvý)"
        fi
    fi
    
    echo "🔧 Worker script: $WORKER_SCRIPT"
    echo "🔐 Lock status: $lock_status"
    echo "$pid_status"
    echo "📊 Běžící procesy: $worker_count"
    echo ""
    
    if [[ "$worker_count" -eq 0 ]]; then
        log_success "Žádné worker procesy - systém je čistý"
    elif [[ "$worker_count" -eq 1 ]]; then
        log_success "Správně - běží POUZE JEDEN worker:"
        ps aux | grep "$WORKER_SCRIPT" | grep -v grep
        echo ""
        health_check
    else
        log_error "PROBLÉM - běží více workerů ($worker_count):"
        ps aux | grep "$WORKER_SCRIPT" | grep -v grep
        echo ""
        log_error "DOPORUČENÍ: Spusť '$0 restart'"
    fi
    
    echo ""
}

# 🔁 KONTINUÁLNÍ HEALTH CHECK (pro daemon mode)
continuous_health_check() {
    log "Spouštím kontinuální health check (interval: ${HEALTH_CHECK_INTERVAL}s)"
    log "Pro ukončení stiskněte Ctrl+C"
    
    while true; do
        if ! health_check; then
            log_error "Health check selhal - ukončuji monitoring"
            exit 1
        fi
        sleep "$HEALTH_CHECK_INTERVAL"
    done
}

# 🚨 CLEANUP funkce při ukončení
cleanup() {
    log "Provádím cleanup při ukončení..."
    release_lock
}

# Nastavení trap pro cleanup
trap cleanup EXIT INT TERM

# 🎯 MAIN LOGIC
case "${1:-status}" in
    "start")
        start_worker
        ;;
    "stop")
        stop_worker
        ;;
    "restart")
        restart_worker
        ;;
    "status")
        show_status
        ;;
    "health")
        health_check
        ;;
    "monitor")
        continuous_health_check
        ;;
    *)
        echo ""
        echo "🛡️ MASTER TEMPORAL WORKER MANAGER"
        echo "=================================="
        echo ""
        echo "Použití: $0 [start|stop|restart|status|health|monitor]"
        echo ""
        echo "start    - Spustí POUZE JEDEN worker (selže pokud už běží)"
        echo "stop     - Gracefully zastaví všechny worker procesy"  
        echo "restart  - Zastaví všechny a spustí JEDEN worker (BEZPEČNÉ)"
        echo "status   - Zobrazí detailní stav worker procesů"
        echo "health   - Provede health check"
        echo "monitor  - Kontinuální health check monitoring"
        echo ""
        echo "🔒 Používá mkdir pro atomický lock (cross-platform)"
        echo "📁 PID file: $PID_FILE"
        echo "🔐 Lock dir: ${LOCK_FILE}.d"  
        echo "📋 Log file: $LOG_FILE"
        echo ""
        echo "🚨 VŽDY používej tento script místo manuálního spouštění!"
        echo ""
        ;;
esac