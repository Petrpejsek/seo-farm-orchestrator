"""
LLM Client Factory pro multi-provider podporu.
Vytváří správný client podle provideru a spravuje API klíče.
"""

import logging
from typing import Dict, Any, List, Optional, Union
import os

from .base import BaseLLMClient
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # Přidá backend/ do PATH
from openai_client import OpenAIClient
from .claude_client import ClaudeClient
from .gemini_client import GeminiClient

logger = logging.getLogger(__name__)

class LLMClientFactory:
    """
    Factory pro vytváření LLM clientů podle provideru.
    Spravuje API klíče a poskytuje unified interface.
    """
    
    SUPPORTED_PROVIDERS = {
        "openai": OpenAIClient,
        "claude": ClaudeClient,
        "gemini": GeminiClient
    }
    
    @staticmethod
    def create_client(provider: str, api_key: Optional[str] = None) -> BaseLLMClient:
        """
        Vytvoří LLM client pro daný provider.
        
        Args:
            provider: Provider name (openai, claude, gemini)
            api_key: Optional API key (pokud není poskytnut, hledá se v prostředí)
            
        Returns:
            BaseLLMClient instance
            
        Raises:
            ValueError: Nepodporovaný provider
            Exception: Chybí API klíč
        """
        provider = provider.lower()
        
        if provider not in LLMClientFactory.SUPPORTED_PROVIDERS:
            supported = list(LLMClientFactory.SUPPORTED_PROVIDERS.keys())
            raise ValueError(f"Nepodporovaný provider '{provider}'. Podporované: {supported}")
        
        # Získání API klíče
        if not api_key:
            api_key = LLMClientFactory._get_api_key(provider)
        
        if not api_key or api_key == "Not found":
            raise Exception(f"API klíč pro {provider} nebyl nalezen")
        
        # Vytvoření clienta
        client_class = LLMClientFactory.SUPPORTED_PROVIDERS[provider]
        client = client_class(api_key)
        
        logger.info(f"✅ LLM Client vytvořen pro provider: {provider}")
        return client
    
    @staticmethod
    def _get_api_key(provider: str) -> Optional[str]:
        """
        🚫 STRICT API KEY LOADING - žádné fallbacky
        Načte API klíč POUZE z backend API.
        
        Args:
            provider: Název provideru
            
        Returns:
            API klíč nebo None
            
        Raises:
            Exception: Pokud backend API není dostupný
        """
        if not provider:
            raise Exception("Provider name pro API klíč není specifikován")
        
        try:
            # POUZE backend API - žádné fallbacky
            import requests
            api_base_url = os.getenv('API_BASE_URL')
            if not api_base_url:
                raise Exception("API_BASE_URL environment variable není nastavena - LLM Factory nelze použít")
                
            response = requests.get(f"{api_base_url}/api-keys/{provider}", timeout=5)
            
            if response.ok:
                data = response.json()
                api_key = data.get("api_key")
                if api_key and api_key != "Not found":
                    logger.info(f"🔑 API klíč pro {provider} načten z backend API")
                    return api_key
            
            # Žádný fallback - pokud backend API nevrátí klíč, selhání
            logger.error(f"❌ Backend API nevrátilo platný API klíč pro {provider} (status: {response.status_code})")
            return None
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Nelze připojit k backend API pro získání API klíče {provider}: {e}")
        except Exception as e:
            raise Exception(f"Kritická chyba při načítání API klíče {provider} z backend API: {e}")
    
    @staticmethod
    def get_supported_providers() -> List[str]:
        """Vrátí seznam podporovaných providerů."""
        return list(LLMClientFactory.SUPPORTED_PROVIDERS.keys())
    
    @staticmethod
    def get_all_models() -> Dict[str, Dict[str, List[str]]]:
        """
        Vrátí všechny podporované modely pro všechny providery.
        
        Returns:
            Dict ve formátu:
            {
                "openai": {"text": ["gpt-4o", ...], "image": ["dall-e-3", ...]},
                "claude": {"text": ["claude-3.5-sonnet", ...], "image": []},
                ...
            }
        """
        all_models = {}
        
        for provider_name, client_class in LLMClientFactory.SUPPORTED_PROVIDERS.items():
            try:
                # Vytvořím temporary instance s dummy API key pro získání modelů
                temp_client = client_class("dummy-key")
                all_models[provider_name] = temp_client.get_supported_models()
            except Exception as e:
                # 🚫 ŽÁDNÝ FALLBACK - pokud nelze načíst modely, LLM Factory nesmí fungovat
                logger.error(f"❌ Nepodařilo se načíst modely pro {provider_name}: {e}")
                raise Exception(f"LLM Factory není správně nakonfigurován - nelze načíst modely pro {provider_name}: {e}")
        
        return all_models
    
    @staticmethod
    def get_provider_parameters(provider: str) -> List[str]:
        """
        Vrátí podporované parametry pro daný provider.
        
        Args:
            provider: Provider name
            
        Returns:
            List parametrů
        """
        provider = provider.lower()
        
        if provider not in LLMClientFactory.SUPPORTED_PROVIDERS:
            supported = list(LLMClientFactory.SUPPORTED_PROVIDERS.keys())
            raise ValueError(f"Nepodporovaný provider '{provider}' pro získání parametrů. Podporované: {supported}")
        
        try:
            client_class = LLMClientFactory.SUPPORTED_PROVIDERS[provider]
            temp_client = client_class("dummy-key")
            return temp_client.get_supported_parameters()
        except Exception as e:
            # 🚫 ŽÁDNÝ FALLBACK - pokud nelze načíst parametry, LLM Factory nesmí fungovat
            logger.error(f"❌ Nepodařilo se načíst parametry pro {provider}: {e}")
            raise Exception(f"LLM Factory není správně nakonfigurován - nelze načíst parametry pro {provider}: {e}")
    
    @staticmethod
    def validate_model_for_provider(provider: str, model: str) -> bool:
        """
        Ověří, zda je model podporován daným providerem.
        
        Args:
            provider: Provider name
            model: Model name
            
        Returns:
            True pokud je model podporován
        """
        provider = provider.lower()
        
        if provider not in LLMClientFactory.SUPPORTED_PROVIDERS:
            supported = list(LLMClientFactory.SUPPORTED_PROVIDERS.keys())
            raise ValueError(f"Nepodporovaný provider '{provider}' pro validaci modelu. Podporované: {supported}")
        
        try:
            client_class = LLMClientFactory.SUPPORTED_PROVIDERS[provider]
            temp_client = client_class("dummy-key")
            return temp_client.validate_model(model)
        except Exception as e:
            # 🚫 ŽÁDNÝ FALLBACK - pokud validace selže, LLM Factory nesmí říct "false" ale vyhodit chybu
            logger.error(f"❌ Nepodařilo se ověřit model {model} pro {provider}: {e}")
            raise Exception(f"LLM Factory není správně nakonfigurován - nelze ověřit model {model} pro {provider}: {e}")