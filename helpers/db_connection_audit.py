#!/usr/bin/env python3
"""
🔍 DATABASE CONNECTION AUDIT
=============================

Nástroj pro audit databázových konexí a poolů:
- Monitoring aktivních konexí
- Detekce memory leaks
- Pool statistics
- Connection lifecycle tracking
- Rollback/commit analysis
"""

import os
import time
import psutil
import threading
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
from collections import defaultdict, deque

from logger import get_logger

logger = get_logger(__name__)


class ConnectionTracker:
    """Sledování lifecycle databázových konexí"""
    
    def __init__(self):
        self.active_connections = {}
        self.connection_history = deque(maxlen=1000)  # Posledních 1000 konexí
        self.connection_counter = 0
        self.lock = threading.Lock()
        
    def track_connection_open(self, connection_id: str = None, metadata: Dict = None) -> str:
        """Zaregistruje otevření nové konexe"""
        if not connection_id:
            self.connection_counter += 1
            connection_id = f"conn_{self.connection_counter}_{int(time.time())}"
        
        with self.lock:
            connection_info = {
                "connection_id": connection_id,
                "opened_at": time.time(),
                "opened_timestamp": datetime.now().isoformat(),
                "thread_id": threading.get_ident(),
                "process_id": os.getpid(),
                "metadata": metadata or {},
                "status": "OPEN"
            }
            
            self.active_connections[connection_id] = connection_info
            logger.info(f"🔗 CONN_OPEN: {connection_id} (thread: {threading.get_ident()})")
            
        return connection_id
    
    def track_connection_close(self, connection_id: str, error: Exception = None):
        """Zaregistruje uzavření konexe"""
        with self.lock:
            if connection_id not in self.active_connections:
                logger.warning(f"⚠️ CONN_CLOSE_UNKNOWN: {connection_id}")
                return
            
            connection_info = self.active_connections[connection_id]
            close_time = time.time()
            duration = close_time - connection_info["opened_at"]
            
            connection_info.update({
                "closed_at": close_time,
                "closed_timestamp": datetime.now().isoformat(),
                "duration_seconds": duration,
                "status": "ERROR" if error else "CLOSED",
                "error": str(error) if error else None
            })
            
            # Přesun do historie
            self.connection_history.append(connection_info.copy())
            del self.active_connections[connection_id]
            
            status = "❌ CONN_ERROR" if error else "✅ CONN_CLOSE"
            logger.info(f"{status}: {connection_id} (duration: {duration:.3f}s)")
            
            if error:
                logger.error(f"🚫 Connection error: {error}")
    
    def get_active_connections(self) -> Dict[str, Any]:
        """Vrátí statistiky aktivních konexí"""
        with self.lock:
            current_time = time.time()
            connections_by_thread = defaultdict(list)
            long_running = []
            
            for conn_id, conn_info in self.active_connections.items():
                duration = current_time - conn_info["opened_at"]
                conn_info["current_duration"] = duration
                
                connections_by_thread[conn_info["thread_id"]].append(conn_info)
                
                if duration > 300:  # Více než 5 minut
                    long_running.append(conn_info)
            
            return {
                "total_active": len(self.active_connections),
                "by_thread": dict(connections_by_thread),
                "long_running": long_running,
                "avg_duration": sum(
                    current_time - conn["opened_at"] 
                    for conn in self.active_connections.values()
                ) / len(self.active_connections) if self.active_connections else 0
            }
    
    def get_connection_statistics(self) -> Dict[str, Any]:
        """Vrátí celkové statistiky konexí"""
        with self.lock:
            total_connections = len(self.connection_history) + len(self.active_connections)
            closed_connections = list(self.connection_history)
            
            if closed_connections:
                avg_duration = sum(conn["duration_seconds"] for conn in closed_connections) / len(closed_connections)
                error_count = sum(1 for conn in closed_connections if conn["status"] == "ERROR")
            else:
                avg_duration = 0
                error_count = 0
            
            return {
                "total_connections": total_connections,
                "active_connections": len(self.active_connections),
                "closed_connections": len(closed_connections),
                "error_connections": error_count,
                "error_rate": error_count / len(closed_connections) if closed_connections else 0,
                "avg_connection_duration": avg_duration,
                "max_concurrent": max(
                    len([c for c in closed_connections if c["opened_at"] <= t <= c["closed_at"]])
                    for t in [time.time()]
                ) if closed_connections else len(self.active_connections)
            }


# Globální tracker
connection_tracker = ConnectionTracker()


@contextmanager
def tracked_db_connection(metadata: Dict = None):
    """Context manager pro sledované DB konexe"""
    connection_id = connection_tracker.track_connection_open(metadata=metadata)
    try:
        # Pro SQLite
        conn = sqlite3.connect("prisma/dev.db", timeout=30.0)
        yield conn
        connection_tracker.track_connection_close(connection_id)
    except Exception as e:
        connection_tracker.track_connection_close(connection_id, error=e)
        raise


class DatabaseAuditor:
    """Hlavní třída pro audit databáze"""
    
    def __init__(self):
        self.audit_history = deque(maxlen=100)
        
    def perform_full_audit(self) -> Dict[str, Any]:
        """Provede kompletní audit databáze"""
        audit_start = time.time()
        audit_id = f"audit_{int(audit_start)}"
        
        logger.info(f"🔍 STARTING_DB_AUDIT: {audit_id}")
        
        audit_result = {
            "audit_id": audit_id,
            "timestamp": datetime.now().isoformat(),
            "start_time": audit_start,
            "tests": {}
        }
        
        try:
            # 1. Connection tracking audit
            audit_result["tests"]["connection_tracking"] = self._audit_connection_tracking()
            
            # 2. Memory usage audit
            audit_result["tests"]["memory_usage"] = self._audit_memory_usage()
            
            # 3. Database lock audit
            audit_result["tests"]["database_locks"] = self._audit_database_locks()
            
            # 4. Transaction audit
            audit_result["tests"]["transaction_audit"] = self._audit_transactions()
            
            # 5. Performance audit
            audit_result["tests"]["performance"] = self._audit_performance()
            
            # Summary
            audit_result["duration"] = time.time() - audit_start
            audit_result["success"] = all(
                test.get("success", False) for test in audit_result["tests"].values()
            )
            
            # Uložit do historie
            self.audit_history.append(audit_result)
            
            logger.info(f"✅ COMPLETED_DB_AUDIT: {audit_id} ({audit_result['duration']:.2f}s)")
            return audit_result
            
        except Exception as e:
            audit_result["error"] = str(e)
            audit_result["success"] = False
            audit_result["duration"] = time.time() - audit_start
            
            logger.error(f"❌ FAILED_DB_AUDIT: {audit_id} - {e}")
            return audit_result
    
    def _audit_connection_tracking(self) -> Dict[str, Any]:
        """Audit sledování konexí"""
        try:
            stats = connection_tracker.get_connection_statistics()
            active = connection_tracker.get_active_connections()
            
            # Detekce problémů
            issues = []
            if active["total_active"] > 10:
                issues.append(f"High number of active connections: {active['total_active']}")
            
            if active["long_running"]:
                issues.append(f"Long running connections detected: {len(active['long_running'])}")
            
            if stats["error_rate"] > 0.1:
                issues.append(f"High error rate: {stats['error_rate']:.2%}")
            
            return {
                "success": len(issues) == 0,
                "statistics": stats,
                "active_connections": active,
                "issues": issues
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _audit_memory_usage(self) -> Dict[str, Any]:
        """Audit využití paměti"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # Měření před a po DB operaci
            memory_before = memory_info.rss
            
            # Testovací DB operace
            with tracked_db_connection({"test": "memory_audit"}):
                conn = sqlite3.connect("prisma/dev.db")
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM assistants")
                cursor.fetchone()
                conn.close()
            
            memory_after = process.memory_info().rss
            memory_diff = memory_after - memory_before
            
            return {
                "success": memory_diff < 10 * 1024 * 1024,  # Méně než 10MB
                "memory_before_mb": memory_before / 1024 / 1024,
                "memory_after_mb": memory_after / 1024 / 1024,
                "memory_diff_mb": memory_diff / 1024 / 1024,
                "acceptable": memory_diff < 10 * 1024 * 1024
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _audit_database_locks(self) -> Dict[str, Any]:
        """Audit databázových zámků"""
        try:
            # Pro SQLite - test concurrent access
            import threading
            import queue
            
            results = queue.Queue()
            errors = queue.Queue()
            
            def db_operation(op_id):
                try:
                    with tracked_db_connection({"test": f"lock_test_{op_id}"}):
                        conn = sqlite3.connect("prisma/dev.db", timeout=5.0)
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM assistants")
                        count = cursor.fetchone()[0]
                        conn.close()
                        results.put({"op_id": op_id, "count": count, "success": True})
                except Exception as e:
                    errors.put({"op_id": op_id, "error": str(e)})
            
            # Spustit 3 současné operace
            threads = []
            for i in range(3):
                thread = threading.Thread(target=db_operation, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Počkat na dokončení
            for thread in threads:
                thread.join(timeout=10)
            
            # Vyhodnotit výsledky
            successful_ops = []
            failed_ops = []
            
            while not results.empty():
                successful_ops.append(results.get())
            
            while not errors.empty():
                failed_ops.append(errors.get())
            
            return {
                "success": len(failed_ops) == 0,
                "successful_operations": len(successful_ops),
                "failed_operations": len(failed_ops),
                "concurrent_access_ok": len(successful_ops) >= 2,
                "errors": failed_ops
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _audit_transactions(self) -> Dict[str, Any]:
        """Audit transakcí"""
        try:
            # Test commit/rollback behavior
            test_results = {}
            
            # Test COMMIT
            with tracked_db_connection({"test": "transaction_commit"}):
                conn = sqlite3.connect("prisma/dev.db")
                cursor = conn.cursor()
                
                # Create test table
                cursor.execute("CREATE TABLE IF NOT EXISTS trans_audit (id INTEGER)")
                cursor.execute("INSERT INTO trans_audit VALUES (999)")
                conn.commit()
                
                # Verify commit
                cursor.execute("SELECT COUNT(*) FROM trans_audit WHERE id = 999")
                count = cursor.fetchone()[0]
                test_results["commit"] = {"success": count == 1, "count": count}
                
                # Cleanup
                cursor.execute("DELETE FROM trans_audit WHERE id = 999")
                conn.commit()
                conn.close()
            
            # Test ROLLBACK
            with tracked_db_connection({"test": "transaction_rollback"}):
                conn = sqlite3.connect("prisma/dev.db")
                cursor = conn.cursor()
                
                cursor.execute("INSERT INTO trans_audit VALUES (998)")
                conn.rollback()  # Explicit rollback
                
                cursor.execute("SELECT COUNT(*) FROM trans_audit WHERE id = 998")
                count = cursor.fetchone()[0]
                test_results["rollback"] = {"success": count == 0, "count": count}
                
                # Cleanup table
                cursor.execute("DROP TABLE IF EXISTS trans_audit")
                conn.commit()
                conn.close()
            
            overall_success = all(test["success"] for test in test_results.values())
            
            return {
                "success": overall_success,
                "tests": test_results
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _audit_performance(self) -> Dict[str, Any]:
        """Audit výkonu"""
        try:
            performance_tests = {}
            
            # Test rychlosti jednotlivých query
            start = time.time()
            with tracked_db_connection({"test": "performance_single"}):
                conn = sqlite3.connect("prisma/dev.db")
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM assistants")
                cursor.fetchone()
                conn.close()
            single_query_time = time.time() - start
            
            performance_tests["single_query"] = {
                "duration": single_query_time,
                "success": single_query_time < 1.0,
                "acceptable": single_query_time < 1.0
            }
            
            # Test vícenásobných query
            start = time.time()
            with tracked_db_connection({"test": "performance_multiple"}):
                conn = sqlite3.connect("prisma/dev.db")
                cursor = conn.cursor()
                for i in range(10):
                    cursor.execute("SELECT * FROM assistants WHERE `order` = ?", (i+1,))
                    cursor.fetchall()
                conn.close()
            multiple_query_time = time.time() - start
            
            performance_tests["multiple_queries"] = {
                "duration": multiple_query_time,
                "query_count": 10,
                "avg_per_query": multiple_query_time / 10,
                "success": multiple_query_time < 2.0,
                "acceptable": multiple_query_time < 2.0
            }
            
            overall_success = all(test["success"] for test in performance_tests.values())
            
            return {
                "success": overall_success,
                "tests": performance_tests
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# Globální auditor
db_auditor = DatabaseAuditor()


def run_connection_audit() -> Dict[str, Any]:
    """Spustí kompletní audit databázových konexí"""
    return db_auditor.perform_full_audit()


def get_connection_stats() -> Dict[str, Any]:
    """Vrátí aktuální statistiky konexí"""
    return {
        "tracker_stats": connection_tracker.get_connection_statistics(),
        "active_connections": connection_tracker.get_active_connections(),
        "timestamp": datetime.now().isoformat()
    }


def log_connection_summary():
    """Zaloguje přehled stavu konexí"""
    stats = get_connection_stats()
    
    logger.info("📊 DB_CONNECTION_SUMMARY:")
    logger.info(f"  ✅ Total connections: {stats['tracker_stats']['total_connections']}")
    logger.info(f"  🔗 Active connections: {stats['tracker_stats']['active_connections']}")
    logger.info(f"  ❌ Error rate: {stats['tracker_stats']['error_rate']:.2%}")
    logger.info(f"  ⏱️ Avg duration: {stats['tracker_stats']['avg_connection_duration']:.2f}s")
    
    if stats['active_connections']['long_running']:
        logger.warning(f"  ⚠️ Long running connections: {len(stats['active_connections']['long_running'])}")


if __name__ == "__main__":
    # Test audit
    print("🔍 Running DB Connection Audit...")
    result = run_connection_audit()
    print(f"✅ Audit completed: {result['success']}")
    
    if not result['success']:
        print("❌ Issues found:")
        for test_name, test_result in result['tests'].items():
            if not test_result.get('success', True):
                print(f"  - {test_name}: {test_result.get('error', 'Failed')}")