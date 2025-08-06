#!/usr/bin/env python3
"""
🔍 DATABASE DEBUG ASSISTANT
============================

Izolační Temporal aktivita pro kompletní testování databázového připojení:
- Connection testing
- CRUD operace na test tabulkách  
- Pool monitoring
- Transaction testing
- Performance benchmarking
"""

import os
import time
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from temporalio import activity

# Import našeho DB loggeru
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from helpers.db_logger import db_logger, log_db_operation, db_operation_context
from logger import get_logger

logger = get_logger(__name__)


@activity.defn
@log_db_operation("DB_DEBUG_FULL_TEST")
async def db_debug_assistant(test_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    🔍 KOMPLETNÍ DB DEBUG TEST
    
    Provede sérii testů databázového připojení a operací:
    1. Basic connectivity test
    2. CRUD operations test
    3. Transaction test  
    4. Pool monitoring
    5. Performance benchmarks
    6. Assistant table specific tests
    
    Args:
        test_config: Konfigurace testů
        
    Returns:
        Detailní report všech testů
    """
    
    activity_info = activity.info()
    logger.info(f"🔍 DB_DEBUG_START: {activity_info.activity_id}")
    
    test_results = {
        "test_id": f"db_debug_{int(time.time())}",
        "timestamp": datetime.now().isoformat(),
        "activity_id": activity_info.activity_id,
        "config": test_config,
        "tests": {}
    }
    
    try:
        # 1️⃣ BASIC CONNECTIVITY TEST
        logger.info("1️⃣ Testing basic DB connectivity...")
        connectivity_result = await test_db_connectivity()
        test_results["tests"]["connectivity"] = connectivity_result
        
        # 2️⃣ CRUD OPERATIONS TEST
        logger.info("2️⃣ Testing CRUD operations...")
        crud_result = await test_crud_operations()
        test_results["tests"]["crud"] = crud_result
        
        # 3️⃣ TRANSACTION TEST
        logger.info("3️⃣ Testing transactions...")
        transaction_result = await test_transactions()
        test_results["tests"]["transactions"] = transaction_result
        
        # 4️⃣ ASSISTANTS TABLE TEST  
        logger.info("4️⃣ Testing assistants table operations...")
        assistants_result = await test_assistants_table()
        test_results["tests"]["assistants"] = assistants_result
        
        # 5️⃣ PERFORMANCE BENCHMARK
        logger.info("5️⃣ Running performance benchmarks...")
        performance_result = await test_performance()
        test_results["tests"]["performance"] = performance_result
        
        # 6️⃣ CONNECTION POOL MONITORING
        logger.info("6️⃣ Monitoring connection pools...")
        pool_result = await test_connection_pools()
        test_results["tests"]["connection_pools"] = pool_result
        
        # FINAL SUMMARY
        success_count = sum(1 for test in test_results["tests"].values() if test.get("success", False))
        total_count = len(test_results["tests"])
        
        test_results["summary"] = {
            "success_count": success_count,
            "total_count": total_count,
            "success_rate": success_count / total_count if total_count > 0 else 0,
            "overall_success": success_count == total_count
        }
        
        logger.info(f"✅ DB_DEBUG_COMPLETED: {success_count}/{total_count} tests passed")
        return test_results
        
    except Exception as e:
        error_info = {
            "error": str(e),
            "type": type(e).__name__,
            "timestamp": datetime.now().isoformat()
        }
        test_results["fatal_error"] = error_info
        test_results["summary"] = {"overall_success": False}
        
        logger.error(f"❌ DB_DEBUG_FAILED: {e}")
        raise


async def test_db_connectivity() -> Dict[str, Any]:
    """Test základního připojení k databázi"""
    result = {
        "test_name": "connectivity",
        "success": False,
        "start_time": time.time()
    }
    
    try:
        with db_operation_context("CONNECTIVITY_TEST", "SELECT 1 as test"):
            # Import here to avoid circular dependencies
            import sqlite3
            
            # Test SQLite connection (adjust for your DB)
            db_path = "prisma/dev.db"
            if not os.path.exists(db_path):
                raise Exception(f"Database file not found: {db_path}")
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Basic connectivity test
            cursor.execute("SELECT 1 as test")
            test_row = cursor.fetchone()
            
            if test_row and test_row[0] == 1:
                result["success"] = True
                result["message"] = "Database connection successful"
            else:
                result["error"] = "Unexpected result from connectivity test"
                
            conn.close()
            
    except Exception as e:
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
    
    result["duration"] = time.time() - result["start_time"]
    return result


async def test_crud_operations() -> Dict[str, Any]:
    """Test CRUD operací na test tabulce"""
    result = {
        "test_name": "crud_operations", 
        "success": False,
        "start_time": time.time(),
        "operations": {}
    }
    
    try:
        import sqlite3
        conn = sqlite3.connect("prisma/dev.db")
        cursor = conn.cursor()
        
        # CREATE test table
        with db_operation_context("CREATE_TEST_TABLE"):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS debug_test (
                    id INTEGER PRIMARY KEY,
                    test_data TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            result["operations"]["create_table"] = {"success": True}
        
        # INSERT test data
        with db_operation_context("INSERT_TEST_DATA"):
            test_data = f"Test data {int(time.time())}"
            cursor.execute("INSERT INTO debug_test (test_data) VALUES (?)", (test_data,))
            inserted_id = cursor.lastrowid
            result["operations"]["insert"] = {"success": True, "inserted_id": inserted_id}
        
        # SELECT test data
        with db_operation_context("SELECT_TEST_DATA"):
            cursor.execute("SELECT * FROM debug_test WHERE id = ?", (inserted_id,))
            row = cursor.fetchone()
            if row and row[1] == test_data:
                result["operations"]["select"] = {"success": True, "data": row}
            else:
                result["operations"]["select"] = {"success": False, "error": "Data mismatch"}
        
        # UPDATE test data
        with db_operation_context("UPDATE_TEST_DATA"):
            updated_data = f"Updated {test_data}"
            cursor.execute("UPDATE debug_test SET test_data = ? WHERE id = ?", (updated_data, inserted_id))
            result["operations"]["update"] = {"success": True, "rows_affected": cursor.rowcount}
        
        # DELETE test data
        with db_operation_context("DELETE_TEST_DATA"):
            cursor.execute("DELETE FROM debug_test WHERE id = ?", (inserted_id,))
            result["operations"]["delete"] = {"success": True, "rows_affected": cursor.rowcount}
        
        # DROP test table
        with db_operation_context("DROP_TEST_TABLE"):
            cursor.execute("DROP TABLE debug_test")
            result["operations"]["drop_table"] = {"success": True}
        
        conn.commit()
        conn.close()
        
        # Check if all operations succeeded
        all_success = all(op.get("success", False) for op in result["operations"].values())
        result["success"] = all_success
        
    except Exception as e:
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
    
    result["duration"] = time.time() - result["start_time"]
    return result


async def test_transactions() -> Dict[str, Any]:
    """Test transakčního chování"""
    result = {
        "test_name": "transactions",
        "success": False,
        "start_time": time.time(),
        "tests": {}
    }
    
    try:
        import sqlite3
        
        # Test COMMIT transaction
        with db_operation_context("TRANSACTION_COMMIT_TEST"):
            conn = sqlite3.connect("prisma/dev.db")
            cursor = conn.cursor()
            
            cursor.execute("CREATE TABLE IF NOT EXISTS trans_test (id INTEGER, data TEXT)")
            cursor.execute("INSERT INTO trans_test VALUES (1, 'commit_test')")
            conn.commit()
            
            cursor.execute("SELECT COUNT(*) FROM trans_test WHERE id = 1")
            count = cursor.fetchone()[0]
            result["tests"]["commit"] = {"success": count == 1, "count": count}
            
            cursor.execute("DELETE FROM trans_test WHERE id = 1")
            conn.commit()
            conn.close()
        
        # Test ROLLBACK transaction
        with db_operation_context("TRANSACTION_ROLLBACK_TEST"):
            conn = sqlite3.connect("prisma/dev.db")
            cursor = conn.cursor()
            
            cursor.execute("INSERT INTO trans_test VALUES (2, 'rollback_test')")
            # Don't commit - simulate rollback
            conn.rollback()
            
            cursor.execute("SELECT COUNT(*) FROM trans_test WHERE id = 2")
            count = cursor.fetchone()[0]
            result["tests"]["rollback"] = {"success": count == 0, "count": count}
            
            cursor.execute("DROP TABLE trans_test")
            conn.commit()
            conn.close()
        
        # Check overall success
        result["success"] = all(test.get("success", False) for test in result["tests"].values())
        
    except Exception as e:
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
    
    result["duration"] = time.time() - result["start_time"]
    return result


async def test_assistants_table() -> Dict[str, Any]:
    """Test operací specifických pro assistants tabulku"""
    result = {
        "test_name": "assistants_table",
        "success": False,
        "start_time": time.time(),
        "operations": {}
    }
    
    try:
        import sqlite3
        conn = sqlite3.connect("prisma/dev.db")
        cursor = conn.cursor()
        
        # Check table structure
        with db_operation_context("CHECK_ASSISTANTS_SCHEMA"):
            cursor.execute("PRAGMA table_info(assistants)")
            columns = cursor.fetchall()
            result["operations"]["schema"] = {
                "success": len(columns) > 0,
                "column_count": len(columns),
                "columns": [col[1] for col in columns]
            }
        
        # Count existing assistants
        with db_operation_context("COUNT_ASSISTANTS"):
            cursor.execute("SELECT COUNT(*) FROM assistants")
            count = cursor.fetchone()[0]
            result["operations"]["count"] = {"success": True, "count": count}
        
        # Test project-specific query (typical use case)
        with db_operation_context("SELECT_BY_PROJECT"):
            cursor.execute("SELECT * FROM assistants WHERE active = 1 ORDER BY `order`")
            assistants = cursor.fetchall()
            result["operations"]["active_assistants"] = {
                "success": True,
                "count": len(assistants),
                "orders": [a[7] for a in assistants] if assistants else []  # order column
            }
        
        # Test specific assistant lookup
        with db_operation_context("SELECT_SPECIFIC_ASSISTANT"):
            cursor.execute("SELECT * FROM assistants WHERE functionKey = 'image_renderer_assistant'")
            image_assistant = cursor.fetchone()
            result["operations"]["image_renderer"] = {
                "success": image_assistant is not None,
                "found": image_assistant is not None,
                "data": image_assistant if image_assistant else None
            }
        
        conn.close()
        
        # Check overall success
        result["success"] = all(op.get("success", False) for op in result["operations"].values())
        
    except Exception as e:
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
    
    result["duration"] = time.time() - result["start_time"]
    return result


async def test_performance() -> Dict[str, Any]:
    """Performance benchmark testů"""
    result = {
        "test_name": "performance",
        "success": False,
        "start_time": time.time(),
        "benchmarks": {}
    }
    
    try:
        import sqlite3
        
        # Single query performance
        with db_operation_context("PERF_SINGLE_QUERY"):
            start = time.time()
            conn = sqlite3.connect("prisma/dev.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM assistants")
            cursor.fetchone()
            conn.close()
            duration = time.time() - start
            
            result["benchmarks"]["single_query"] = {
                "success": duration < 1.0,  # Should be under 1 second
                "duration": duration,
                "acceptable": duration < 1.0
            }
        
        # Multiple queries performance
        with db_operation_context("PERF_MULTIPLE_QUERIES"):
            start = time.time()
            conn = sqlite3.connect("prisma/dev.db")
            cursor = conn.cursor()
            
            for i in range(10):
                cursor.execute("SELECT * FROM assistants WHERE `order` = ?", (i+1,))
                cursor.fetchall()
            
            conn.close()
            duration = time.time() - start
            
            result["benchmarks"]["multiple_queries"] = {
                "success": duration < 2.0,  # Should be under 2 seconds for 10 queries
                "duration": duration,
                "queries_count": 10,
                "avg_per_query": duration / 10
            }
        
        # Check overall performance
        result["success"] = all(bench.get("success", False) for bench in result["benchmarks"].values())
        
    except Exception as e:
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
    
    result["duration"] = time.time() - result["start_time"]
    return result


async def test_connection_pools() -> Dict[str, Any]:
    """Test connection pool monitoring"""
    result = {
        "test_name": "connection_pools",
        "success": False,
        "start_time": time.time(),
        "stats": {}
    }
    
    try:
        # SQLite doesn't use connection pools like PostgreSQL
        # But we can test concurrent connections
        import sqlite3
        import threading
        
        connections = []
        errors = []
        
        def create_connection(conn_id):
            try:
                conn = sqlite3.connect("prisma/dev.db", timeout=5.0)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                connections.append(conn_id)
                conn.close()
            except Exception as e:
                errors.append({"conn_id": conn_id, "error": str(e)})
        
        # Test concurrent connections
        with db_operation_context("CONCURRENT_CONNECTIONS_TEST"):
            threads = []
            for i in range(5):
                thread = threading.Thread(target=create_connection, args=(i,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join(timeout=10)
        
        result["stats"]["concurrent_connections"] = {
            "success": len(errors) == 0,
            "successful_connections": len(connections),
            "failed_connections": len(errors),
            "errors": errors
        }
        
        result["success"] = len(errors) == 0
        
    except Exception as e:
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
    
    result["duration"] = time.time() - result["start_time"]
    return result


# Utility funkce pro monitoring aktivních operací
async def log_active_db_operations():
    """Zaloguje všechny aktivní DB operace"""
    db_logger.log_active_operations()
    return db_logger.active_operations


if __name__ == "__main__":
    # Standalone test
    print("🔍 Testing DB Debug Assistant...")
    import asyncio
    
    async def test():
        config = {"test_mode": True}
        result = await db_debug_assistant(config)
        print(json.dumps(result, indent=2, default=str))
    
    asyncio.run(test())