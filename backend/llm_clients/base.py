"""
Abstract base class pro všechny LLM clients.
Zajišťuje konzistentní interface napříč providery.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class BaseLLMClient(ABC):
    """
    Abstract base class pro všechny LLM providery.
    Každý provider musí implementovat tyto metody.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.provider_name = self.__class__.__name__.replace('Client', '').lower()
        logger.info(f"🤖 Inicializuji {self.provider_name} LLM client")
    
    @abstractmethod
    async def chat_completion(
        self, 
        system_prompt: str, 
        user_message: str, 
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,  # -1 nebo None = neomezeno
        **kwargs
    ) -> Dict[str, Any]:
        """
        Hlavní metoda pro chat completion.
        Musí vracet standardizovaný formát výsledku.
        """
        pass
    
    @abstractmethod
    async def image_generation(
        self, 
        prompt: str, 
        model: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generování obrázků (pokud provider podporuje).
        """
        pass
    
    @abstractmethod
    def get_supported_models(self) -> Dict[str, List[str]]:
        """
        Vrátí seznam podporovaných modelů pro daný provider.
        Format: {"text": ["model1", "model2"], "image": ["dalle-3"]}
        """
        pass
    
    @abstractmethod
    def get_supported_parameters(self) -> List[str]:
        """
        Vrátí seznam parametrů podporovaných tímto providerem.
        Např. ["temperature", "max_tokens", "top_p"]
        """
        pass
    
    @abstractmethod
    def validate_model(self, model: str) -> bool:
        """
        Ověří, zda je model podporován tímto providerem.
        """
        pass
    
    def _standardize_response(
        self, 
        content: str, 
        model: str, 
        usage: Dict[str, int] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Standardizuje response format napříč všemi providery.
        """
        return {
            "content": content,
            "model": model,
            "provider": self.provider_name,
            "usage": usage or {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            },
            "metadata": metadata or {},
            "timestamp": __import__('time').time()
        }
    
    def _log_request(self, model: str, system_prompt: str, user_message: str):
        """Loguje request pro audit."""
        logger.info(f"📝 [{self.provider_name.upper()}] Model: {model}")
        logger.info(f"📝 [{self.provider_name.upper()}] System prompt: {len(system_prompt)} znaků")
        logger.info(f"📝 [{self.provider_name.upper()}] User message: {len(user_message)} znaků")
    
    def _log_response(self, response: Dict[str, Any]):
        """Loguje response pro audit."""
        usage = response.get("usage", {})
        tokens = usage.get("total_tokens", 0)
        logger.info(f"✅ [{self.provider_name.upper()}] Response: {len(response.get('content', ''))} znaků")
        logger.info(f"✅ [{self.provider_name.upper()}] Tokens: {tokens}")