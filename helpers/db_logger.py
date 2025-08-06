#!/usr/bin/env python3
"""
🔍 DATABASE DEBUGGING LOGGER
=============================

Konzistentní logging pro všechny databázové operace s detailním sledováním:
- Query text a parametry
- Duration měření
- Výsledky operací
- Error handling
- Connection pool monitoring
"""

import time
import json
import traceback
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from contextlib import contextmanager
from datetime import datetime

from logger import get_logger

logger = get_logger(__name__)


class DBOperationLogger:
    """Centrální logger pro všechny DB operace"""
    
    def __init__(self):
        self.operation_counter = 0
        self.active_operations = {}
        
    def start_operation(self, operation_type: str, query: str = None, params: Dict = None) -> str:
        """Zahájí novou DB operaci a vrátí operation_id"""
        self.operation_counter += 1
        operation_id = f"db_op_{self.operation_counter}_{int(time.time())}"
        
        operation_data = {
            "operation_id": operation_id,
            "operation_type": operation_type,
            "query": query,
            "params": params,
            "start_time": time.time(),
            "start_timestamp": datetime.now().isoformat(),
            "status": "STARTED"
        }
        
        self.active_operations[operation_id] = operation_data
        
        logger.info(f"🔵 DB_OP_START: {operation_id}")
        logger.info(f"📊 Type: {operation_type}")
        if query:
            # Safely truncate long queries
            query_preview = query[:200] + "..." if len(query) > 200 else query
            logger.info(f"🔍 Query: {query_preview}")
        if params:
            logger.info(f"⚙️ Params: {json.dumps(params, default=str, ensure_ascii=False)[:500]}")
            
        return operation_id
    
    def finish_operation(self, operation_id: str, result: Any = None, error: Exception = None):
        """Dokončí DB operaci s výsledkem nebo chybou"""
        if operation_id not in self.active_operations:
            logger.error(f"❌ DB_OP_ERROR: Unknown operation_id {operation_id}")
            return
            
        operation_data = self.active_operations[operation_id]
        end_time = time.time()
        duration = end_time - operation_data["start_time"]
        
        operation_data.update({
            "end_time": end_time,
            "end_timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "status": "ERROR" if error else "COMPLETED"
        })
        
        if error:
            operation_data["error"] = str(error)
            operation_data["error_type"] = type(error).__name__
            operation_data["traceback"] = traceback.format_exc()
            
            logger.error(f"❌ DB_OP_ERROR: {operation_id}")
            logger.error(f"⏱️ Duration: {duration:.3f}s")
            logger.error(f"🚫 Error: {error}")
            logger.error(f"📍 Traceback: {traceback.format_exc()[:1000]}")
        else:
            # Bezpečné logování výsledku
            if result is not None:
                if hasattr(result, '__len__') and not isinstance(result, str):
                    result_info = f"{type(result).__name__} with {len(result)} items"
                else:
                    result_info = f"{type(result).__name__}: {str(result)[:200]}"
                operation_data["result_type"] = type(result).__name__
                operation_data["result_preview"] = str(result)[:500]
            else:
                result_info = "None"
                
            logger.info(f"✅ DB_OP_SUCCESS: {operation_id}")
            logger.info(f"⏱️ Duration: {duration:.3f}s")
            logger.info(f"📦 Result: {result_info}")
        
        # Odstranit z aktivních operací
        del self.active_operations[operation_id]
        
    def log_active_operations(self):
        """Zaloguje všechny aktivní operace (pro debugging zacyklení)"""
        if not self.active_operations:
            logger.info("📊 DB_ACTIVE_OPS: Žádné aktivní operace")
            return
            
        logger.warning(f"⚠️ DB_ACTIVE_OPS: {len(self.active_operations)} aktivních operací")
        for op_id, op_data in self.active_operations.items():
            duration = time.time() - op_data["start_time"]
            logger.warning(f"  🔄 {op_id}: {op_data['operation_type']} ({duration:.1f}s)")


# Globální instance
db_logger = DBOperationLogger()


def log_db_operation(operation_type: str):
    """Decorator pro automatické logování DB operací"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extrakce query a params z argumentů
            query = kwargs.get('query') or (args[0] if args else None)
            params = kwargs.get('params') or kwargs.get('args') or (args[1] if len(args) > 1 else None)
            
            operation_id = db_logger.start_operation(
                operation_type=operation_type,
                query=str(query) if query else None,
                params=params
            )
            
            try:
                result = await func(*args, **kwargs)
                db_logger.finish_operation(operation_id, result=result)
                return result
            except Exception as e:
                db_logger.finish_operation(operation_id, error=e)
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Extrakce query a params z argumentů
            query = kwargs.get('query') or (args[0] if args else None)
            params = kwargs.get('params') or kwargs.get('args') or (args[1] if len(args) > 1 else None)
            
            operation_id = db_logger.start_operation(
                operation_type=operation_type,
                query=str(query) if query else None,
                params=params
            )
            
            try:
                result = func(*args, **kwargs)
                db_logger.finish_operation(operation_id, result=result)
                return result
            except Exception as e:
                db_logger.finish_operation(operation_id, error=e)
                raise
        
        # Rozhodnutí mezi sync/async wrapper
        if hasattr(func, '__code__') and 'async' in str(func.__code__.co_flags):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


@contextmanager
def db_operation_context(operation_type: str, query: str = None, params: Dict = None):
    """Context manager pro manuální logování DB operací"""
    operation_id = db_logger.start_operation(operation_type, query, params)
    try:
        yield operation_id
        db_logger.finish_operation(operation_id)
    except Exception as e:
        db_logger.finish_operation(operation_id, error=e)
        raise


# Utility funkce pro monitoring
def get_active_db_operations() -> Dict:
    """Vrátí info o aktivních DB operacích"""
    return {
        "count": len(db_logger.active_operations),
        "operations": list(db_logger.active_operations.values())
    }


def log_db_pool_stats():
    """Loguje statistiky connection pool (implementace závislá na ORM)"""
    try:
        # Placeholder - bude rozšířeno podle použitého ORM
        logger.info("📊 DB_POOL_STATS: Connection pool monitoring...")
        
        # TODO: Implementovat podle konkrétního ORM (SQLAlchemy, etc.)
        
    except Exception as e:
        logger.error(f"❌ DB_POOL_STATS_ERROR: {e}")


# Cleanup funkce
def cleanup_stale_operations(max_age_seconds: int = 300):
    """Vyčistí staré operace (pro případ že finish_operation nebyl zavolán)"""
    current_time = time.time()
    stale_ops = []
    
    for op_id, op_data in db_logger.active_operations.items():
        if current_time - op_data["start_time"] > max_age_seconds:
            stale_ops.append(op_id)
    
    for op_id in stale_ops:
        logger.warning(f"🧹 CLEANUP_STALE_OP: {op_id} (age > {max_age_seconds}s)")
        del db_logger.active_operations[op_id]


if __name__ == "__main__":
    # Test logging
    print("🔍 Testing DB Logger...")
    
    with db_operation_context("TEST", "SELECT * FROM test", {"limit": 10}):
        time.sleep(0.1)
    
    print("✅ DB Logger test completed")