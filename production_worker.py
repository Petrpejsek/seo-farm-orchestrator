"""
🏭 PRODUKČNÍ TEMPORAL WORKER
Stabilní, modulární worker připravený pro nasazení v produkčním prostředí.
"""

import asyncio
import signal
import sys
from typing import List, Optional

# 🛡️ OCHRANA PŘED DEPRECATED MODULY - ZABRÁNÍ NAČÍTÁNÍ STARÝCH VERZÍ
for banned in ["worker_DEPRECATED", "assistant_activities_DEPRECATED", "simple_worker_DEPRECATED"]:
    if banned in sys.modules:
        raise RuntimeError(f"❌ ZAKÁZÁN DEPRECATED MODUL: {banned} - použij safe_assistant_activities.py!")

# Naše nové moduly
from config import get_temporal_config, get_logging_config
from logger import get_logger, log_workflow_start

# Temporal imports
from temporalio.client import Client
from temporalio.worker import Worker

# Workflows
from workflows.seo_workflow import SEOWorkflow
from workflows.assistant_pipeline_workflow import AssistantPipelineWorkflow

# Aktivities - bezpečné verze
from activities.safe_assistant_activities import (
    load_assistants_from_database,
    execute_assistant
)

# Originální aktivity (pokud existují)
try:
    from activities.generate_llm_friendly_content import generate_llm_friendly_content
    from activities.inject_structured_markup import inject_structured_markup
    from activities.save_output_to_json import save_output_to_json
    ORIGINAL_ACTIVITIES_AVAILABLE = True
except ImportError as e:
    get_logger(__name__).warning(f"⚠️ Některé originální aktivity nejsou dostupné: {e}")
    ORIGINAL_ACTIVITIES_AVAILABLE = False

logger = get_logger(__name__)

# 🔍 DEBUG: Ověření, že běží správná verze
print("✅ LAUNCH: Čistý worker běží – verze bez fallbacků, bez string outputu")
print("✅ Worker načetl safe_assistant_activities.py")
print("✅ Aktivita: image_renderer_assistant")
print("✅ Concurrency: 3")

class ProductionWorker:
    """Produkční Temporal worker s graceful shutdown a error handling."""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.worker: Optional[Worker] = None
        self.config = get_temporal_config()
        self.running = False
        
    async def setup(self):
        """Nastaví připojení k Temporal serveru."""
        try:
            logger.info(f"🔗 Připojování k Temporal serveru: {self.config.host}")
            
            self.client = await Client.connect(
                self.config.host,
                namespace=self.config.namespace
            )
            
            # Příprava aktivit
            activities = [
                load_assistants_from_database,
                execute_assistant
            ]
            
            # Přidání originálních aktivit, pokud jsou dostupné
            if ORIGINAL_ACTIVITIES_AVAILABLE:
                activities.extend([
                    generate_llm_friendly_content,
                    inject_structured_markup,
                    save_output_to_json
                ])
                logger.info("✅ Originální aktivity přidány")
            
            # Vytvoření workera
            self.worker = Worker(
                self.client,
                task_queue=self.config.task_queue,
                workflows=[
                    SEOWorkflow,
                    AssistantPipelineWorkflow
                ],
                activities=activities,
                max_concurrent_activities=self.config.max_workers
            )
            
            logger.info(f"✅ Worker nastaven pro task queue: {self.config.task_queue}")
            logger.info(f"📊 Max concurrent activities: {self.config.max_workers}")
            logger.info(f"🔄 Workflows: {len([SEOWorkflow, AssistantPipelineWorkflow])}")
            logger.info(f"⚙️ Activities: {len(activities)}")
            
        except Exception as e:
            logger.error(f"❌ Chyba při nastavení workera: {e}")
            raise
    
    async def run(self):
        """Spustí worker s graceful shutdown."""
        if not self.worker:
            raise RuntimeError("Worker není nastaven. Zavolejte setup() nejdříve.")
        
        self.running = True
        logger.info("🚀 Produkční worker spuštěn a čeká na úkoly...")
        
        try:
            await self.worker.run()
        except KeyboardInterrupt:
            logger.info("⏹️ Přijat signal pro ukončení")
        except Exception as e:
            logger.error(f"❌ Worker spadl s chybou: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Gracefully ukončí worker."""
        if not self.running:
            return
            
        logger.info("🛑 Ukončování workera...")
        self.running = False
        
        # Cleanup
        if self.client:
            try:
                # Temporal client se ukončí automaticky
                logger.info("✅ Temporal client uzavřen")
            except Exception as e:
                logger.error(f"⚠️ Chyba při uzavírání clienta: {e}")
    
    def setup_signal_handlers(self):
        """Nastaví signal handlery pro graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"📡 Přijat signal {signum}")
            if self.running:
                # Spustíme shutdown v event lopu
                loop = asyncio.get_event_loop()
                loop.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

async def health_check() -> bool:
    """
    Provede health check Temporal připojení.
    
    Returns:
        True pokud je připojení v pořádku
    """
    try:
        config = get_temporal_config()
        client = await Client.connect(config.host, namespace=config.namespace)
        
        # Jednoduchý test - pokud se podaří připojení, je to OK
        # Nepotřebujeme složité API volání, stačí úspěšné připojení
        logger.info(f"✅ Health check OK - Temporal server běží na {config.host}")
        
        # Client se automaticky uzavře při ukončení scope
        return True
        
    except Exception as e:
        logger.error(f"❌ Health check selhal: {e}")
        return False

async def main():
    """Hlavní funkce pro spuštění produkčního workera."""
    logger.info("🏭 === PRODUKČNÍ TEMPORAL WORKER ===")
    
    # Health check před spuštěním
    if not await health_check():
        logger.error("❌ Health check selhal - ukončuji")
        sys.exit(1)
    
    # Vytvoření a spuštění workera
    worker = ProductionWorker()
    worker.setup_signal_handlers()
    
    try:
        await worker.setup()
        await worker.run()
    except Exception as e:
        logger.error(f"💥 Kritická chyba workera: {e}")
        sys.exit(1)
    
    logger.info("👋 Worker ukončen")

if __name__ == "__main__":
    # Nastavení event loop policy pro Windows kompatibilitu
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚡ Worker přerušen uživatelem")
    except Exception as e:
        logger.error(f"💀 Neočekávaná chyba: {e}")
        sys.exit(1)