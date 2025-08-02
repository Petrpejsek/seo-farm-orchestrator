"""
🔧 CENTRALIZOVANÉ LOGOVÁNÍ PRO PRODUKČNÍ PROSTŘEDÍ
Jednotné logování pro všechny komponenty systému s rotací a strukturovaným formátem.
"""

import logging
import logging.handlers
import sys
import traceback
from typing import Optional, Dict, Any
from config import get_logging_config

class ProductionLogger:
    """Centralizovaný logger pro produkční prostředí."""
    
    _instances: Dict[str, logging.Logger] = {}
    _initialized = False
    
    @classmethod
    def setup_logging(cls):
        """Nastaví globální logování pro celý systém."""
        if cls._initialized:
            return
            
        config = get_logging_config()
        
        # Základní konfigurace
        logging.basicConfig(
            level=getattr(logging, config.level),
            format=config.format,
            handlers=[
                # Rotující file handler
                logging.handlers.RotatingFileHandler(
                    config.file,
                    maxBytes=config.max_bytes,
                    backupCount=config.backup_count
                ),
                # Console handler pro development
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Ztlumení verbose logů z externích knihoven
        logging.getLogger("temporalio").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Získá logger pro konkrétní modul."""
        if not cls._initialized:
            cls.setup_logging()
            
        if name not in cls._instances:
            cls._instances[name] = logging.getLogger(name)
            
        return cls._instances[name]

def get_logger(name: str) -> logging.Logger:
    """Convenience funkce pro získání loggeru."""
    return ProductionLogger.get_logger(name)

def log_exception(logger: logging.Logger, message: str, exc: Optional[Exception] = None):
    """
    Loguje výjimku s kompletním traceback.
    
    Args:
        logger: Logger instance
        message: Popisná zpráva
        exc: Výjimka (pokud není poskytnutá, použije se aktuální)
    """
    if exc:
        logger.error(f"{message}: {str(exc)}", exc_info=True)
    else:
        logger.error(f"{message}: {traceback.format_exc()}")

def log_activity_start(logger: logging.Logger, activity_name: str, inputs: Dict[str, Any]):
    """Loguje začátek aktivity."""
    logger.info(f"🚀 ACTIVITY START: {activity_name}")
    logger.debug(f"   📥 Inputs: {inputs}")

def log_activity_success(logger: logging.Logger, activity_name: str, output_preview: str):
    """Loguje úspěšné dokončení aktivity."""
    logger.info(f"✅ ACTIVITY SUCCESS: {activity_name}")
    logger.debug(f"   📤 Output preview: {output_preview[:200]}...")

def log_activity_error(logger: logging.Logger, activity_name: str, error: Exception, inputs: Dict[str, Any]):
    """Loguje chybu v aktivitě."""
    logger.error(f"❌ ACTIVITY ERROR: {activity_name}")
    logger.error(f"   📥 Inputs: {inputs}")
    log_exception(logger, f"   💥 Exception in {activity_name}", error)

def log_llm_request(logger: logging.Logger, provider: str, model: str, tokens: Optional[int]):
    """Loguje LLM request."""
    logger.info(f"🤖 LLM REQUEST: {provider}/{model} (tokens: {tokens or 'unlimited'})")

def log_llm_response(logger: logging.Logger, provider: str, response_length: int, duration: float):
    """Loguje LLM response."""
    logger.info(f"📨 LLM RESPONSE: {provider} ({response_length} chars in {duration:.2f}s)")

def log_workflow_start(logger: logging.Logger, workflow_id: str, inputs: Dict[str, Any]):
    """Loguje začátek workflow."""
    logger.info(f"🏃 WORKFLOW START: {workflow_id}")
    logger.debug(f"   📥 Inputs: {inputs}")

def log_workflow_complete(logger: logging.Logger, workflow_id: str, duration: float):
    """Loguje dokončení workflow."""
    logger.info(f"🏁 WORKFLOW COMPLETE: {workflow_id} (duration: {duration:.2f}s)")

# Inicializace při importu
ProductionLogger.setup_logging()