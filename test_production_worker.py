"""
🧪 TEST SCRIPT PRO PRODUKČNÍ WORKER
Rychlý test všech nových modulů bez circular imports.
"""

import asyncio
import sys

async def test_modules():
    """Test všech nových modulů."""
    print("🧪 === TEST PRODUKČNÍCH MODULŮ ===")
    print()
    
    # Test 1: Config
    try:
        from config import config, get_temporal_config, get_llm_config
        print("✅ Config modul: OK")
        print(f"   - Temporal host: {get_temporal_config().host}")
        print(f"   - Activity timeout: {config.activity.default_timeout}s")
        print(f"   - LLM API URL: {get_llm_config().api_base_url}")
    except Exception as e:
        print(f"❌ Config modul: {e}")
        return False
    
    # Test 2: Logger
    try:
        from logger import get_logger, log_activity_start
        logger = get_logger('test')
        logger.info("Logger test úspěšný")
        print("✅ Logger modul: OK")
    except Exception as e:
        print(f"❌ Logger modul: {e}")
        return False
    
    # Test 3: Activity Wrappers
    try:
        from activity_wrappers import safe_activity, validate_activity_input
        
        # Test validace
        validate_activity_input({'test': 'value'}, ['test'])
        
        # Test error handling
        try:
            validate_activity_input({}, ['required'])
            print("❌ Validace by měla selhat")
            return False
        except ValueError:
            pass  # Expected
            
        print("✅ Activity wrappers: OK")
    except Exception as e:
        print(f"❌ Activity wrappers: {e}")
        return False
    
    # Test 4: Production Worker (import only)
    try:
        # Pouze test importu, ne spuštění
        import production_worker
        print("✅ Production worker: Import OK")
    except Exception as e:
        print(f"❌ Production worker: {e}")
        return False
    
    print()
    print("🎉 === VŠECHNY MODULY TESTOVÁNY ÚSPĚŠNĚ ===")
    print()
    print("📋 SUMMARY:")
    print("✅ config.py - Centralizovaná konfigurace")
    print("✅ logger.py - Strukturované logování")  
    print("✅ activity_wrappers.py - Bezpečné wrappery")
    print("✅ production_worker.py - Hlavní worker")
    print()
    print("🚀 SYSTÉM PŘIPRAVEN PRO DEPLOYMENT!")
    
    return True

async def test_temporal_connection():
    """Test připojení k Temporal serveru."""
    try:
        from temporalio.client import Client
        
        print("🔗 Test Temporal připojení...")
        client = await Client.connect("localhost:7233", namespace="default")
        print("✅ Temporal připojení: OK")
        
        return True
    except Exception as e:
        print(f"⚠️ Temporal připojení: {e}")
        print("   (To je OK pokud Temporal server neběží)")
        return False

if __name__ == "__main__":
    asyncio.run(test_modules())
    print()
    asyncio.run(test_temporal_connection())