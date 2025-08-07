"""
🏗️ PRODUKČNÍ KONFIGURACE PRO TEMPORAL WORKER
Centralizované nastavení pro stabilní běh v produkčním prostředí.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class TemporalConfig:
    """Konfigurace pro Temporal server a workery."""
    host: str = "localhost:7233"
    namespace: str = "default"
    task_queue: str = "default"
    max_workers: int = 12  # ⚡ BATCH PROCESSING: Zvýšeno pro paralelní zpracování stovek témat
    graceful_shutdown_timeout: int = 30

@dataclass
class ActivityConfig:
    """Konfigurace pro aktivity a timeouty."""
    default_timeout: int = 600  # 10 minut
    heartbeat_timeout: int = 180  # 3 minuty
    retry_attempts: int = 3
    retry_backoff: float = 2.0

@dataclass
class LLMConfig:
    """Konfigurace pro LLM providery."""
    default_temperature: float = 0.7
    default_max_tokens: Optional[int] = None  # Neomezeno
    request_timeout: int = 120  # 2 minuty
    api_base_url: str = "http://localhost:8000"

@dataclass
class LoggingConfig:
    """Konfigurace pro logování."""
    level: str = "INFO"
    format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    file: str = "worker_production.log"
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

class Config:
    """Hlavní konfigurační třída pro celý systém."""
    
    def __init__(self):
        self.temporal = TemporalConfig()
        self.activity = ActivityConfig()
        self.llm = LLMConfig()
        self.logging = LoggingConfig()
        
        # Načtení z environment variables
        self._load_from_env()
    
    def _load_from_env(self):
        """Načte konfiguraci z environment variables."""
        # Temporal
        self.temporal.host = os.getenv("TEMPORAL_HOST", self.temporal.host)
        self.temporal.namespace = os.getenv("TEMPORAL_NAMESPACE", self.temporal.namespace)
        
        # LLM
        self.llm.api_base_url = os.getenv("API_BASE_URL", self.llm.api_base_url)
        
        # Logging
        log_level = os.getenv("LOG_LEVEL", self.logging.level)
        if log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            self.logging.level = log_level
    
    def get_activity_options(self) -> Dict[str, Any]:
        """Vrátí standardní options pro Temporal aktivity."""
        from datetime import timedelta
        
        return {
            "start_to_close_timeout": timedelta(seconds=self.activity.default_timeout),
            "heartbeat_timeout": timedelta(seconds=self.activity.heartbeat_timeout),
            "retry_policy": {
                "maximum_attempts": self.activity.retry_attempts,
                "backoff_coefficient": self.activity.retry_backoff,
            }
        }

# Globální instance konfigurace
config = Config()

# Convenience funkce pro rychlý přístup
def get_temporal_config() -> TemporalConfig:
    return config.temporal

def get_activity_config() -> ActivityConfig:
    return config.activity

def get_llm_config() -> LLMConfig:
    return config.llm

def get_logging_config() -> LoggingConfig:
    return config.logging