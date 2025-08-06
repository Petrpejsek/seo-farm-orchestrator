#!/usr/bin/env python3
"""
🔍 DATABASE ACTIVITY MONITOR
============================

Monitoring databázových aktivit a detekce problémů:
- Dlouho běžící queries
- Zombie transakce  
- Zablokované queries
- Performance monitoring
- Activity statistics
"""

import os
import time
import threading
import sqlite3
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from dataclasses import dataclass

from logger import get_logger

logger = get_logger(__name__)


@dataclass
class QueryActivity:
    """Reprezentace databázové aktivity"""
    query_id: str
    query_text: str
    start_time: float
    thread_id: int
    process_id: int
    status: str  # RUNNING, COMPLETED, ERROR, TIMEOUT
    duration: Optional[float] = None
    error: Optional[str] = None
    result_rows: Optional[int] = None


class DatabaseActivityMonitor:
    """Monitor databázových aktivit"""
    
    def __init__(self, max_history: int = 1000):
        self.active_queries = {}  # query_id -> QueryActivity
        self.query_history = deque(maxlen=max_history)
        self.query_counter = 0
        self.lock = threading.Lock()
        self.monitoring_enabled = True
        
        # Prahy pro detekci problémů
        self.long_query_threshold = 30.0  # 30 sekund
        self.zombie_threshold = 300.0     # 5 minut
        self.max_concurrent_queries = 20
        
    def start_query_tracking(self, query_text: str, metadata: Dict = None) -> str:
        """Začne sledovat nový query"""
        if not self.monitoring_enabled:
            return None
            
        with self.lock:
            self.query_counter += 1
            query_id = f"query_{self.query_counter}_{int(time.time())}"
            
            activity = QueryActivity(
                query_id=query_id,
                query_text=query_text,
                start_time=time.time(),
                thread_id=threading.get_ident(),
                process_id=os.getpid(),
                status="RUNNING"
            )
            
            self.active_queries[query_id] = activity
            
            # Zkrácený text pro log
            query_preview = query_text[:100] + "..." if len(query_text) > 100 else query_text
            logger.info(f"🔵 QUERY_START: {query_id} - {query_preview}")
            
            return query_id
    
    def finish_query_tracking(self, query_id: str, error: Exception = None, result_rows: int = None):
        """Dokončí sledování query"""
        if not query_id or not self.monitoring_enabled:
            return
            
        with self.lock:
            if query_id not in self.active_queries:
                logger.warning(f"⚠️ QUERY_FINISH_UNKNOWN: {query_id}")
                return
            
            activity = self.active_queries[query_id]
            activity.duration = time.time() - activity.start_time
            activity.result_rows = result_rows
            
            if error:
                activity.status = "ERROR"
                activity.error = str(error)
                logger.error(f"❌ QUERY_ERROR: {query_id} ({activity.duration:.3f}s) - {error}")
            else:
                activity.status = "COMPLETED"
                status_icon = "✅" if activity.duration < self.long_query_threshold else "🐌"
                logger.info(f"{status_icon} QUERY_COMPLETE: {query_id} ({activity.duration:.3f}s)")
            
            # Přesun do historie
            self.query_history.append(activity)
            del self.active_queries[query_id]
    
    def detect_long_running_queries(self) -> List[QueryActivity]:
        """Detekuje dlouho běžící queries"""
        current_time = time.time()
        long_queries = []
        
        with self.lock:
            for activity in self.active_queries.values():
                duration = current_time - activity.start_time
                if duration > self.long_query_threshold:
                    activity_copy = QueryActivity(
                        query_id=activity.query_id,
                        query_text=activity.query_text,
                        start_time=activity.start_time,
                        thread_id=activity.thread_id,
                        process_id=activity.process_id,
                        status=activity.status,
                        duration=duration
                    )
                    long_queries.append(activity_copy)
        
        return long_queries
    
    def detect_zombie_queries(self) -> List[QueryActivity]:
        """Detekuje zombie transakce"""
        current_time = time.time()
        zombies = []
        
        with self.lock:
            for activity in self.active_queries.values():
                duration = current_time - activity.start_time
                if duration > self.zombie_threshold:
                    activity_copy = QueryActivity(
                        query_id=activity.query_id,
                        query_text=activity.query_text,
                        start_time=activity.start_time,
                        thread_id=activity.thread_id,
                        process_id=activity.process_id,
                        status="ZOMBIE",
                        duration=duration
                    )
                    zombies.append(activity_copy)
        
        return zombies
    
    def get_activity_statistics(self) -> Dict[str, Any]:
        """Vrátí statistiky databázových aktivit"""
        current_time = time.time()
        
        with self.lock:
            # Aktivní queries
            active_count = len(self.active_queries)
            avg_active_duration = sum(
                current_time - activity.start_time 
                for activity in self.active_queries.values()
            ) / active_count if active_count > 0 else 0
            
            # Historie queries
            completed_queries = [q for q in self.query_history if q.status == "COMPLETED"]
            error_queries = [q for q in self.query_history if q.status == "ERROR"]
            
            avg_completion_time = sum(
                q.duration for q in completed_queries if q.duration
            ) / len(completed_queries) if completed_queries else 0
            
            # Detekce problémů
            long_queries = self.detect_long_running_queries()
            zombies = self.detect_zombie_queries()
            
            # Statistiky podle threadů
            threads_activity = defaultdict(int)
            for activity in self.active_queries.values():
                threads_activity[activity.thread_id] += 1
            
            return {
                "timestamp": datetime.now().isoformat(),
                "active_queries": {
                    "count": active_count,
                    "avg_duration": avg_active_duration,
                    "by_thread": dict(threads_activity)
                },
                "completed_queries": {
                    "count": len(completed_queries),
                    "avg_duration": avg_completion_time,
                    "error_count": len(error_queries),
                    "error_rate": len(error_queries) / len(self.query_history) if self.query_history else 0
                },
                "issues": {
                    "long_running_count": len(long_queries),
                    "zombie_count": len(zombies),
                    "concurrent_limit_exceeded": active_count > self.max_concurrent_queries
                },
                "performance": {
                    "total_queries": len(self.query_history) + active_count,
                    "queries_per_minute": len([
                        q for q in self.query_history 
                        if current_time - q.start_time < 60
                    ]),
                    "avg_query_time": avg_completion_time
                }
            }
    
    def log_activity_summary(self):
        """Zaloguje přehled aktivit"""
        stats = self.get_activity_statistics()
        
        logger.info("📊 DB_ACTIVITY_SUMMARY:")
        logger.info(f"  🔄 Active queries: {stats['active_queries']['count']}")
        logger.info(f"  ✅ Completed queries: {stats['completed_queries']['count']}")
        logger.info(f"  ❌ Error rate: {stats['completed_queries']['error_rate']:.2%}")
        logger.info(f"  ⏱️ Avg query time: {stats['performance']['avg_query_time']:.3f}s")
        logger.info(f"  🏃 Queries/min: {stats['performance']['queries_per_minute']}")
        
        # Upozornění na problémy
        if stats['issues']['long_running_count'] > 0:
            logger.warning(f"  ⚠️ Long running queries: {stats['issues']['long_running_count']}")
        
        if stats['issues']['zombie_count'] > 0:
            logger.error(f"  🧟 Zombie queries: {stats['issues']['zombie_count']}")
        
        if stats['issues']['concurrent_limit_exceeded']:
            logger.warning(f"  🚫 Too many concurrent queries: {stats['active_queries']['count']}")


# Globální monitor
activity_monitor = DatabaseActivityMonitor()


class MonitoredSQLiteConnection:
    """SQLite konexe s monitoringem"""
    
    def __init__(self, database_path: str, **kwargs):
        self.database_path = database_path
        self.connection = sqlite3.connect(database_path, **kwargs)
        self.active_queries = {}
        
    def execute(self, query: str, parameters=None):
        """Monitorovaný execute"""
        query_id = activity_monitor.start_query_tracking(query)
        try:
            cursor = self.connection.cursor()
            if parameters:
                result = cursor.execute(query, parameters)
            else:
                result = cursor.execute(query)
            
            # Počet řádků (pokud je to možné zjistit)
            row_count = cursor.rowcount if hasattr(cursor, 'rowcount') else None
            activity_monitor.finish_query_tracking(query_id, result_rows=row_count)
            
            return result
        except Exception as e:
            activity_monitor.finish_query_tracking(query_id, error=e)
            raise
    
    def __getattr__(self, name):
        """Proxy pro ostatní metody connection"""
        return getattr(self.connection, name)
    
    def close(self):
        """Uzavře konexe"""
        return self.connection.close()


def create_monitored_connection(database_path: str = "prisma/dev.db", **kwargs) -> MonitoredSQLiteConnection:
    """Vytvoří monitorovanou SQLite konexe"""
    return MonitoredSQLiteConnection(database_path, **kwargs)


class DatabaseActivityWatchdog:
    """Watchdog pro automatické sledování a řešení problémů"""
    
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        
    def start(self):
        """Spustí watchdog"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.thread.start()
        logger.info("🐕 DB_WATCHDOG_STARTED")
    
    def stop(self):
        """Zastaví watchdog"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🐕 DB_WATCHDOG_STOPPED")
    
    def _watchdog_loop(self):
        """Hlavní smyčka watchdogu"""
        while self.running:
            try:
                self._check_database_health()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"❌ WATCHDOG_ERROR: {e}")
                time.sleep(self.check_interval)
    
    def _check_database_health(self):
        """Zkontroluje zdraví databáze"""
        stats = activity_monitor.get_activity_statistics()
        
        # Detekce problémů
        issues_found = []
        
        if stats['issues']['zombie_count'] > 0:
            issues_found.append(f"Zombie queries detected: {stats['issues']['zombie_count']}")
            logger.error(f"🧟 ZOMBIE_QUERIES_DETECTED: {stats['issues']['zombie_count']}")
        
        if stats['issues']['long_running_count'] > 3:
            issues_found.append(f"Too many long running queries: {stats['issues']['long_running_count']}")
            logger.warning(f"🐌 LONG_QUERIES_DETECTED: {stats['issues']['long_running_count']}")
        
        if stats['completed_queries']['error_rate'] > 0.2:
            issues_found.append(f"High error rate: {stats['completed_queries']['error_rate']:.2%}")
            logger.error(f"❌ HIGH_ERROR_RATE: {stats['completed_queries']['error_rate']:.2%}")
        
        if stats['issues']['concurrent_limit_exceeded']:
            issues_found.append("Too many concurrent queries")
            logger.warning(f"🚫 CONCURRENT_LIMIT_EXCEEDED: {stats['active_queries']['count']}")
        
        # Logování výsledků
        if issues_found:
            logger.warning(f"🚨 DB_HEALTH_ISSUES: {len(issues_found)} issues found")
            for issue in issues_found:
                logger.warning(f"  - {issue}")
        else:
            logger.debug("✅ DB_HEALTH_OK: No issues detected")
        
        # Pravidelné logování statistik
        if time.time() % (self.check_interval * 5) < self.check_interval:  # Každých 5 cyklů
            activity_monitor.log_activity_summary()


# Globální watchdog
db_watchdog = DatabaseActivityWatchdog()


def start_database_monitoring():
    """Spustí monitoring databáze"""
    activity_monitor.monitoring_enabled = True
    db_watchdog.start()
    logger.info("🔍 DB_MONITORING_STARTED")


def stop_database_monitoring():
    """Zastaví monitoring databáze"""
    activity_monitor.monitoring_enabled = False
    db_watchdog.stop()
    logger.info("🔍 DB_MONITORING_STOPPED")


def get_database_health_report() -> Dict[str, Any]:
    """Vrátí kompletní zdravotní report databáze"""
    stats = activity_monitor.get_activity_statistics()
    long_queries = activity_monitor.detect_long_running_queries()
    zombies = activity_monitor.detect_zombie_queries()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "overall_health": "HEALTHY" if not (long_queries or zombies or stats['issues']['concurrent_limit_exceeded']) else "WARNING",
        "statistics": stats,
        "long_running_queries": [
            {
                "query_id": q.query_id,
                "duration": q.duration,
                "query_preview": q.query_text[:100] + "..." if len(q.query_text) > 100 else q.query_text,
                "thread_id": q.thread_id
            }
            for q in long_queries
        ],
        "zombie_queries": [
            {
                "query_id": q.query_id,
                "duration": q.duration,
                "query_preview": q.query_text[:100] + "..." if len(q.query_text) > 100 else q.query_text,
                "thread_id": q.thread_id
            }
            for q in zombies
        ]
    }


if __name__ == "__main__":
    # Test monitoring
    print("🔍 Testing Database Activity Monitor...")
    
    # Start monitoring
    start_database_monitoring()
    
    # Simulace databázových operací
    import asyncio
    
    async def test_queries():
        conn = create_monitored_connection()
        
        # Test rychlý query
        conn.execute("SELECT COUNT(*) FROM assistants")
        
        # Test pomalejší query (simulace)
        time.sleep(0.1)
        conn.execute("SELECT * FROM assistants")
        
        conn.close()
    
    asyncio.run(test_queries())
    
    # Výpis statistik
    time.sleep(1)
    report = get_database_health_report()
    print(f"Health: {report['overall_health']}")
    print(f"Active queries: {report['statistics']['active_queries']['count']}")
    print(f"Completed queries: {report['statistics']['completed_queries']['count']}")
    
    stop_database_monitoring()
    print("✅ Test completed")