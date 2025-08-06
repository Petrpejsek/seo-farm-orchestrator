#!/bin/bash

# 🛡️ MASTER TEMPORAL WORKER MANAGER - PRODUCTION VERSION
# =====================================================
# Production-ready verze s kompletní konfigurací pro deploy
# - Environment detection (dev/staging/production)
# - Cross-platform kompatibilita (Linux/macOS)
# - Secure lock file location
# - Production URLs a cesty
# - Enhanced logging and monitoring
# 
# POUŽITÍ: ./master_worker_manager_production.sh [start|stop|restart|status|health]

set -euo pipefail

# 🌍 ENVIRONMENT DETECTION
ENVIRONMENT="${ENVIRONMENT:-development}"
HOSTNAME="${HOSTNAME:-$(hostname)}"

# 🔧 PRODUCTION/ENVIRONMENT KONFIGURACE
case "$ENVIRONMENT" in
    "production")
        WORKER_SCRIPT="${WORKER_SCRIPT:-/opt/seo-farm/production_worker.py}"
        PID_FILE="${PID_FILE:-/var/run/seo-farm/worker.pid}"
        LOCK_FILE="${LOCK_FILE:-/var/lock/seo-farm/temporal_worker.lock}"
        LOG_FILE="${LOG_FILE:-/var/log/seo-farm/worker.log}"
        API_BASE_URL="${API_BASE_URL:-https://api.yourdomain.com}"
        WORKER_USER="${WORKER_USER:-seouser}"
        ;;
    "staging")
        WORKER_SCRIPT="${WORKER_SCRIPT:-/opt/seo-farm-staging/production_worker.py}"
        PID_FILE="${PID_FILE:-/tmp/seo-farm-staging/worker.pid}"
        LOCK_FILE="${LOCK_FILE:-/tmp/seo-farm-staging/temporal_worker.lock}"
        LOG_FILE="${LOG_FILE:-/tmp/seo-farm-staging/worker.log}"
        API_BASE_URL="${API_BASE_URL:-https://staging-api.yourdomain.com}"
        WORKER_USER="${WORKER_USER:-$(whoami)}"
        ;;
    *)  # development
        WORKER_SCRIPT="${WORKER_SCRIPT:-./production_worker.py}"
        PID_FILE="${PID_FILE:-./worker.pid}"
        LOCK_FILE="${LOCK_FILE:-/tmp/temporal_worker_dev.lock}"
        LOG_FILE="${LOG_FILE:-./worker.log}"
        API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
        WORKER_USER="${WORKER_USER:-$(whoami)}"
        ;;
esac

# 🔧 DALŠÍ KONFIGURACE
HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-30}"  # sekund
PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-python3}"
MAX_STARTUP_WAIT="${MAX_STARTUP_WAIT:-60}"  # sekund
GRACEFUL_SHUTDOWN_TIMEOUT="${GRACEFUL_SHUTDOWN_TIMEOUT:-30}"

# 🖥️ PLATFORM DETECTION
PLATFORM="$(uname -s)"
case "$PLATFORM" in
    "Darwin")  # macOS
        PS_COMMAND_FIELD="command"
        ;;
    "Linux")   # Linux
        PS_COMMAND_FIELD="comm"
        ;;
    *)
        echo "⚠️  Neznámá platforma: $PLATFORM, používám Linux defaults"
        PS_COMMAND_FIELD="comm"
        ;;
esac

# 🎨 BARVY PRO VÝSTUP
if [[ -t 1 ]]; then  # Pouze pokud je terminal
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# 📝 LOGGING FUNKCE
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] [$$] [$ENVIRONMENT]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] [$$] [$ENVIRONMENT] ✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] [$$] [$ENVIRONMENT] ⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] [$$] [$ENVIRONMENT] ❌ $1${NC}" | tee -a "$LOG_FILE"
}

# 📁 ADRESÁŘ A PERMISSIONS SETUP
setup_directories() {
    log "Nastavuji adresářovou strukturu..."
    
    # Vytvoř parent adresáře pokud neexistují
    mkdir -p "$(dirname "$PID_FILE")" 2>/dev/null || true
    mkdir -p "$(dirname "$LOCK_FILE")" 2>/dev/null || true
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
    
    # Nastav permissions pokud je to production
    if [[ "$ENVIRONMENT" == "production" ]]; then
        # V produkci musí mít správné permissions
        if [[ "$(whoami)" == "root" ]]; then
            chown -R "$WORKER_USER:$WORKER_USER" "$(dirname "$PID_FILE")" 2>/dev/null || true
            chown -R "$WORKER_USER:$WORKER_USER" "$(dirname "$LOG_FILE")" 2>/dev/null || true
            chmod 755 "$(dirname "$PID_FILE")" 2>/dev/null || true
            chmod 755 "$(dirname "$LOG_FILE")" 2>/dev/null || true
        fi
    fi
}

# 🔐 ATOMICKÝ LOCK (cross-platform, production-safe)
acquire_lock() {
    log "Získávám atomický lock..."
    
    local lock_dir="${LOCK_FILE}.d"
    local max_wait=30
    local waited=0
    
    # Ujisti se, že lock directory parent existuje
    mkdir -p "$(dirname "$lock_dir")" 2>/dev/null || true
    
    while ! mkdir "$lock_dir" 2>/dev/null; do
        if [[ $waited -ge $max_wait ]]; then
            log_error "Worker už běží nebo je uzamčen! (lock dir: $lock_dir)"
            log_error "Pokud jste si jisti, že worker neběží, smažte: $lock_dir"
            
            # V production ukažme dodatečné info pro debugging
            if [[ "$ENVIRONMENT" == "production" ]]; then
                if [[ -d "$lock_dir" ]]; then
                    log_error "Lock info:"
                    ls -la "$lock_dir" 2>/dev/null || true
                    cat "$lock_dir/manager_pid" 2>/dev/null && echo || true
                    cat "$lock_dir/locked_at" 2>/dev/null && echo || true
                fi
            fi
            
            exit 1
        fi
        log "Čekám na uvolnění lock... ($waited/$max_wait s)"
        sleep 1
        ((waited++))
    done
    
    # Uložíme info do lock directory
    echo $$ > "$lock_dir/manager_pid" 2>/dev/null || true
    echo "$(date)" > "$lock_dir/locked_at" 2>/dev/null || true
    echo "$ENVIRONMENT" > "$lock_dir/environment" 2>/dev/null || true
    echo "$HOSTNAME" > "$lock_dir/hostname" 2>/dev/null || true
    
    log_success "Lock získán úspěšně"
}

release_lock() {
    local lock_dir="${LOCK_FILE}.d"
    if [[ -d "$lock_dir" ]]; then
        rm -rf "$lock_dir" 2>/dev/null || true
        log "Lock uvolněn"
    fi
}

# 🔍 PID FILE OCHRANA (cross-platform)
validate_pid_file() {
    if [[ ! -f "$PID_FILE" ]]; then
        return 1  # PID file neexistuje
    fi
    
    local pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
    if [[ -z "$pid" ]]; then
        log_warning "PID file je prázdný, odstraňuji..."
        rm -f "$PID_FILE" 2>/dev/null || true
        return 1
    fi
    
    # Cross-platform check existence procesu
    if ! kill -0 "$pid" 2>/dev/null; then
        log_warning "Proces s PID $pid už neexistuje, odstraňuji starý PID file..."
        rm -f "$PID_FILE" 2>/dev/null || true
        return 1
    fi
    
    # Ověř, zda to je opravdu náš worker (cross-platform)
    local process_command=""
    case "$PLATFORM" in
        "Darwin")  # macOS
            process_command=$(ps -p "$pid" -o command= 2>/dev/null | head -1 || echo "")
            ;;
        "Linux")   # Linux  
            process_command=$(ps -p "$pid" -o comm= 2>/dev/null | head -1 || echo "")
            # Fallback na args pokud comm není dostatečný
            if [[ ! "$process_command" =~ python|worker ]]; then
                process_command=$(ps -p "$pid" -o args= 2>/dev/null | head -1 || echo "")
            fi
            ;;
    esac
    
    if [[ ! "$process_command" =~ production_worker|python.*worker ]]; then
        log_warning "Proces s PID $pid není náš worker, odstraňuji PID file..."
        log_warning "Process command: $process_command"
        rm -f "$PID_FILE" 2>/dev/null || true
        return 1
    fi
    
    echo "$pid"
    return 0
}

# 🔍 KONTROLA BĚŽÍCÍCH WORKERŮ (cross-platform)
check_running_workers() {
    local count=0
    case "$PLATFORM" in
        "Darwin")  # macOS
            count=$(ps aux | grep -E "(production_worker\.py|python.*production_worker)" | grep -v grep | wc -l | tr -d ' ')
            ;;
        "Linux")   # Linux
            count=$(pgrep -f "production_worker" | wc -l | tr -d ' ')
            ;;
    esac
    echo "$count"
}

get_worker_pids() {
    case "$PLATFORM" in
        "Darwin")  # macOS
            ps aux | grep -E "(production_worker\.py|python.*production_worker)" | grep -v grep | awk '{print $2}' | tr '\n' ' '
            ;;
        "Linux")   # Linux
            pgrep -f "production_worker" | tr '\n' ' '
            ;;
    esac
}

# 🏥 ENHANCED HEALTH CHECK
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
    
    # 3. Ověř API endpoint (jen pokud je curl dostupný)
    if command -v curl >/dev/null 2>&1; then
        local health_url="$API_BASE_URL/health"
        if curl -s --max-time 5 "$health_url" >/dev/null 2>&1; then
            log_success "API endpoint je dostupný ($health_url)"
        else
            log_warning "API endpoint nedostupný: $health_url"
            # V produkci to může být problém
            if [[ "$ENVIRONMENT" == "production" ]]; then
                log_error "V produkci musí být API dostupné!"
                return 1
            fi
        fi
    else
        log_warning "curl není k dispozici, přeskakuji API health check"
    fi
    
    # 4. Ověř log file (pokud existuje)
    if [[ -f "$LOG_FILE" ]]; then
        local log_size=$(du -h "$LOG_FILE" 2>/dev/null | cut -f1 || echo "0")
        log "Log file size: $log_size"
        
        # Zkontroluj poslední aktivitu
        local last_log_line=$(tail -1 "$LOG_FILE" 2>/dev/null || echo "")
        if [[ -n "$last_log_line" ]]; then
            log "Poslední log: $(echo "$last_log_line" | head -c 100)..."
        fi
    fi
    
    log_success "Health check úspěšný - worker běží správně (PID: $pid)"
    return 0
}

# 🚀 ENHANCED WORKER START
start_worker() {
    log "=== SPOUŠTÍM TEMPORAL WORKER ==="
    log "Environment: $ENVIRONMENT"
    log "Platform: $PLATFORM"
    log "Hostname: $HOSTNAME"
    
    # Setup adresářů
    setup_directories
    
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
    
    # V produkci ověř permissions
    if [[ "$ENVIRONMENT" == "production" ]]; then
        if [[ ! -x "$WORKER_SCRIPT" ]]; then
            log_error "Worker script není spustitelný!"
            release_lock
            exit 1
        fi
    fi
    
    log "API_BASE_URL: $API_BASE_URL"
    log "Worker script: $WORKER_SCRIPT"
    log "Python executable: $PYTHON_EXECUTABLE"
    
    # Spuštění workera na pozadí
    log "Spouštím worker proces..."
    
    # V produkci můžeme chtít změnit uživatele
    local start_command=""
    if [[ "$ENVIRONMENT" == "production" && "$(whoami)" == "root" && "$WORKER_USER" != "root" ]]; then
        start_command="su - $WORKER_USER -c 'cd $(dirname "$WORKER_SCRIPT") && API_BASE_URL=\"$API_BASE_URL\" nohup $PYTHON_EXECUTABLE \"$WORKER_SCRIPT\" >> \"$LOG_FILE\" 2>&1 &'"
        eval "$start_command"
        sleep 2
        # Získej PID jinak při su
        local worker_pid=$(get_worker_pids | awk '{print $1}')
    else
        cd "$(dirname "$WORKER_SCRIPT")"
        API_BASE_URL="$API_BASE_URL" nohup "$PYTHON_EXECUTABLE" "$WORKER_SCRIPT" >> "$LOG_FILE" 2>&1 &
        local worker_pid=$!
    fi
    
    if [[ -z "$worker_pid" ]]; then
        log_error "Nepodařilo se získat PID worker procesu!"
        release_lock
        exit 1
    fi
    
    # Ulož PID
    echo "$worker_pid" > "$PID_FILE"
    log "PID $worker_pid uložen do $PID_FILE"
    
    # Počkej na startup a ověř
    log "Čekám na worker startup (max ${MAX_STARTUP_WAIT}s)..."
    local waited=0
    while [[ $waited -lt $MAX_STARTUP_WAIT ]]; do
        if kill -0 "$worker_pid" 2>/dev/null; then
            break
        fi
        sleep 1
        ((waited++))
    done
    
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
        log_success "Environment: $ENVIRONMENT"
        log_success "Log file: $LOG_FILE"
        log_success "Pro monitoring: tail -f $LOG_FILE"
    else
        log_error "Worker se spustil, ale health check selhal"
        stop_worker
        release_lock
        exit 1
    fi
    
    log_success "=== WORKER ÚSPĚŠNĚ SPUŠTĚN ==="
}

# 🛑 ENHANCED WORKER STOP
stop_worker() {
    log "=== ZASTAVUJI TEMPORAL WORKER ==="
    
    # Najdi všechny worker procesy
    local worker_pids=$(get_worker_pids)
    
    if [[ -z "$worker_pids" ]]; then
        log_warning "Žádné worker procesy nenalezeny"
    else
        log "Ukončuji procesy: $worker_pids"
        
        # Graceful shutdown (SIGTERM)
        for pid in $worker_pids; do
            if kill -0 "$pid" 2>/dev/null; then
                log "Posílám SIGTERM procesu $pid"
                kill -TERM "$pid" 2>/dev/null || true
            fi
        done
        
        # Počkej na graceful shutdown
        local waited=0
        while [[ $waited -lt $GRACEFUL_SHUTDOWN_TIMEOUT ]]; do
            local remaining=$(check_running_workers)
            if [[ "$remaining" -eq 0 ]]; then
                break
            fi
            sleep 1
            ((waited++))
        done
        
        # Ověř, že jsou ukončeny
        local remaining=$(check_running_workers)
        if [[ "$remaining" -gt 0 ]]; then
            log_warning "Některé procesy stále běží po ${GRACEFUL_SHUTDOWN_TIMEOUT}s, používám SIGKILL..."
            for pid in $worker_pids; do
                if kill -0 "$pid" 2>/dev/null; then
                    log "Posílám SIGKILL procesu $pid"
                    kill -9 "$pid" 2>/dev/null || true
                fi
            done
            sleep 2
        fi
        
        # Finální ověření
        local final_count=$(check_running_workers)
        if [[ "$final_count" -gt 0 ]]; then
            log_error "KRITICKÉ: Někteří workeri stále běží!"
            case "$PLATFORM" in
                "Darwin")
                    ps aux | grep -E "(production_worker\.py|python.*production_worker)" | grep -v grep
                    ;;
                "Linux")
                    ps aux | grep production_worker | grep -v grep
                    ;;
            esac
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

# 📊 ENHANCED STATUS
show_status() {
    echo ""
    log "=== STATUS TEMPORAL WORKERA ==="
    echo ""
    
    local worker_count=$(check_running_workers)
    local lock_status="🔓 UNLOCKED"
    local pid_status="📁 Žádný PID file"
    
    # Konfigurace info
    echo "🌍 Environment: $ENVIRONMENT"
    echo "🖥️  Platform: $PLATFORM"
    echo "🏠 Hostname: $HOSTNAME"
    echo "👤 Worker user: $WORKER_USER"
    echo ""
    
    # Cesty
    echo "🔧 Worker script: $WORKER_SCRIPT"
    echo "📁 PID file: $PID_FILE"
    echo "📋 Log file: $LOG_FILE"
    echo "🌐 API URL: $API_BASE_URL"
    echo ""
    
    # Kontrola lock file
    local lock_dir="${LOCK_FILE}.d"
    if [[ -d "$lock_dir" ]]; then
        lock_status="🔒 LOCKED"
        if [[ -f "$lock_dir/manager_pid" ]]; then
            local lock_pid=$(cat "$lock_dir/manager_pid" 2>/dev/null || echo "N/A")
            lock_status="$lock_status (PID: $lock_pid)"
        fi
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
    
    echo "🔐 Lock status: $lock_status"
    echo "$pid_status"
    echo "📊 Běžící procesy: $worker_count"
    echo ""
    
    if [[ "$worker_count" -eq 0 ]]; then
        log_success "Žádné worker procesy - systém je čistý"
    elif [[ "$worker_count" -eq 1 ]]; then
        log_success "Správně - běží POUZE JEDEN worker:"
        case "$PLATFORM" in
            "Darwin")
                ps aux | grep -E "(production_worker\.py|python.*production_worker)" | grep -v grep
                ;;
            "Linux")
                ps aux | grep production_worker | grep -v grep || pgrep -fl production_worker
                ;;
        esac
        echo ""
        health_check
    else
        log_error "PROBLÉM - běží více workerů ($worker_count):"
        case "$PLATFORM" in
            "Darwin")
                ps aux | grep -E "(production_worker\.py|python.*production_worker)" | grep -v grep
                ;;
            "Linux")
                ps aux | grep production_worker | grep -v grep || pgrep -fl production_worker
                ;;
        esac
        echo ""
        log_error "DOPORUČENÍ: Spusť '$0 restart'"
    fi
    
    echo ""
}

# 🔁 KONTINUÁLNÍ HEALTH CHECK
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

# 📋 SHOW ENVIRONMENT INFO
show_environment_info() {
    echo ""
    echo "🌍 ENVIRONMENT CONFIGURATION"
    echo "============================"
    echo "Environment: $ENVIRONMENT"
    echo "Platform: $PLATFORM"
    echo "Hostname: $HOSTNAME"
    echo "Current user: $(whoami)"
    echo "Worker user: $WORKER_USER"
    echo ""
    echo "📁 PATHS:"
    echo "Worker script: $WORKER_SCRIPT"
    echo "PID file: $PID_FILE"
    echo "Lock file: $LOCK_FILE"
    echo "Log file: $LOG_FILE"
    echo ""
    echo "🌐 NETWORK:"
    echo "API Base URL: $API_BASE_URL"
    echo ""
    echo "🔧 CONFIGURATION:"
    echo "Python: $PYTHON_EXECUTABLE"
    echo "Health check interval: ${HEALTH_CHECK_INTERVAL}s"
    echo "Max startup wait: ${MAX_STARTUP_WAIT}s"
    echo "Graceful shutdown timeout: ${GRACEFUL_SHUTDOWN_TIMEOUT}s"
    echo ""
}

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
    "env"|"environment")
        show_environment_info
        ;;
    *)
        echo ""
        echo "🛡️ MASTER TEMPORAL WORKER MANAGER - PRODUCTION READY"
        echo "===================================================="
        echo ""
        echo "Použití: $0 [start|stop|restart|status|health|monitor|env]"
        echo ""
        echo "start      - Spustí POUZE JEDEN worker (selže pokud už běží)"
        echo "stop       - Gracefully zastaví všechny worker procesy"  
        echo "restart    - Zastaví všechny a spustí JEDEN worker (BEZPEČNÉ)"
        echo "status     - Zobrazí detailní stav worker procesů"
        echo "health     - Provede health check"
        echo "monitor    - Kontinuální health check monitoring"
        echo "env        - Zobrazí environment konfiguraci"
        echo ""
        echo "🌍 ENVIRONMENT VARIABLES:"
        echo "ENVIRONMENT=development|staging|production"
        echo "API_BASE_URL=<api_url>"
        echo "WORKER_SCRIPT=<path_to_script>"
        echo "PYTHON_EXECUTABLE=<python_path>"
        echo ""
        echo "🔒 Cross-platform atomický lock (Linux/macOS)"
        echo "📁 Production-safe file locations"
        echo "🏥 Enhanced health checking"
        echo ""
        echo "🚨 VŽDY používej tento script místo manuálního spouštění!"
        echo ""
        ;;
esac