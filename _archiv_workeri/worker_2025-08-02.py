#!/usr/bin/env python3
"""
🏭 SEO ORCHESTRATOR - PRODUKČNÍ WORKER
Stabilní, crash-proof worker pro Temporal.io orchestraci LLM článků.

Spuštění:
    export API_BASE_URL=http://localhost:8000
    python worker.py

Monitoring:
    tail -f worker_production.log

Dokumentace:
    Viz PRODUCTION_README.md
"""

import sys
import os
import asyncio
import signal
from pathlib import Path

# Přidání project root do Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import produkčního workera
from production_worker import main as production_main

def check_environment():
    """Kontrola základních požadavků před spuštěním."""
    print("🔍 === PŘEDSTARTOVNÍ KONTROLA ===")
    
    # Kontrola API_BASE_URL
    api_url = os.getenv("API_BASE_URL")
    if not api_url:
        print("❌ CHYBA: Environment variable API_BASE_URL není nastavena")
        print("   Řešení: export API_BASE_URL=http://localhost:8000")
        return False
    
    print(f"✅ API_BASE_URL: {api_url}")
    
    # Kontrola Python verze
    if sys.version_info < (3, 8):
        print(f"❌ CHYBA: Python {sys.version_info.major}.{sys.version_info.minor} není podporován")
        print("   Minimální verze: Python 3.8+")
        return False
    
    print(f"✅ Python verze: {sys.version_info.major}.{sys.version_info.minor}")
    
    # Kontrola důležitých modulů
    required_modules = [
        ("temporalio", "Temporal.io client"),
        ("prisma", "Database ORM"),
        ("httpx", "HTTP client")
    ]
    
    for module, description in required_modules:
        try:
            __import__(module)
            print(f"✅ {description}: OK")
        except ImportError:
            print(f"❌ CHYBA: {description} není nainstalován")
            print(f"   Řešení: pip install {module}")
            return False
    
    print("🎉 Předstartovní kontrola úspěšná!")
    print()
    return True

def setup_signal_handlers():
    """Nastaví signal handlers pro graceful shutdown."""
    def signal_handler(signum, frame):
        print(f"\n📡 Přijat signal {signum} - ukončuji worker...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # systemd stop

if __name__ == "__main__":
    print("🏭 === SEO ORCHESTRATOR WORKER ===")
    print("📋 Produkční worker pro stabilní LLM orchestraci")
    print()
    
    # Předstartovní kontrola
    if not check_environment():
        print("💥 Worker se nespustí kvůli chybám v konfiguraci")
        sys.exit(1)
    
    # Signal handlers
    setup_signal_handlers()
    
    try:
        print("🚀 Spouštím produkční worker...")
        print("   📊 Monitoring: tail -f worker_production.log")
        print("   ⏹️ Stop: Ctrl+C nebo kill -TERM")
        print()
        
        # Spuštění hlavního workera
        asyncio.run(production_main())
        
    except KeyboardInterrupt:
        print("\n⚡ Worker přerušen uživatelem")
    except Exception as e:
        print(f"\n💀 Kritická chyba: {e}")
        sys.exit(1)
    finally:
        print("👋 Worker ukončen")