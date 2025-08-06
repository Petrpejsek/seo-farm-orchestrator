"""
Centralizovaný OpenAI client s auditovanými parametry pro SEO Farm Orchestrator.

Tento modul poskytuje všechny OpenAI API volání s přesně definovanými parametry
podle finální specifikace. Žádné defaultní hodnoty nejsou ponechány!
"""

import json
import logging
import os
from typing import Optional, Dict, Any, List
from openai import OpenAI
import asyncio
# Import BaseLLMClient bez circular dependency
try:
    from backend.llm_clients.base import BaseLLMClient
except ImportError:
    import sys
    sys.path.append(os.path.dirname(__file__))
    from llm_clients.base import BaseLLMClient

logger = logging.getLogger(__name__)

# 🎛️ FINÁLNÍ AUDITOVANÉ OPENAI PARAMETRY - ZCELA BEZ DEFAULTŮ!
OPENAI_CONFIG = {
    "model": "gpt-4o",  # JEDINÝ MODEL - žádné fallbacky
    "temperature": 0.7,  # Kreativita vs konzistence
    "max_tokens": None,  # Bez omezení - necháváme na OpenAI API
    "top_p": 1.0,  # Nepoužívat současně s temperature
    "frequency_penalty": 0.0,  # Žádné penalty - explicitně 0.0
    "presence_penalty": 0.0,  # Žádné penalty - explicitně 0.0
    "timeout": 120,  # 2 minuty timeout pro API volání
    "request_timeout": 60  # Timeout pro jednotlivé request
}

# 🎨 DALL·E 3 PARAMETRY PRO IMAGE GENERATION
DALLE_CONFIG = {
    "model": "dall-e-3",  # Pouze nejnovější model
    "size": "1024x1024",  # Standardní velikost
    "quality": "standard",  # standard nebo hd
    "style": "natural",  # natural nebo vivid  
    "n": 1,  # Počet obrázků (DALL·E 3 podporuje pouze n=1)
    "timeout": 180  # 3 minuty pro image generation
}

def get_api_key(service: str = "openai") -> str:
    """
    Načte API klíč pro OpenAI z backend API nebo environment variables.
    
    Args:
        service: Název služby (defaultně "openai")
        
    Returns:
        API klíč pro OpenAI
        
    Raises:
        Exception: Pokud API klíč není nalezen
    """
    try:
        # Pokus o načtení z backend API
        import requests
        backend_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        response = requests.get(f"{backend_url}/api-keys/{service}", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            api_key = data.get("api_key")
            if api_key and api_key != "Not found":
                logger.info(f"✅ OpenAI API klíč načten z backend API")
                return api_key
        
        logger.error(f"❌ Backend API nevrátilo platný klíč")
        raise Exception("❌ OpenAI API klíč nenalezen v backend API")
    except Exception as e:
        logger.error(f"❌ Chyba při načítání API klíče z backend: {e}")
        raise Exception(f"❌ OpenAI API klíč není dostupný: {e}")

class OpenAIClient(BaseLLMClient):
    """
    Centralizovaný OpenAI client s auditovanými parametry.
    Všechny API volání procházejí přes tuto třídu s přesnými parametry.
    """
    
    def __init__(self, api_key: str):
        """Inicializace OpenAI clienta s API klíčem."""
        super().__init__(api_key)
        self.api_key = api_key
        self.client = OpenAI(
            api_key=self.api_key,
            timeout=OPENAI_CONFIG["timeout"]
        )
        logger.info(f"🤖 OpenAI client inicializován s auditem parametrů")
        self._log_config()
    
    def get_supported_models(self) -> Dict[str, List[str]]:
        """Vrátí seznam podporovaných OpenAI modelů."""
        return {
            "text": ["gpt-4o", "gpt-4", "gpt-3.5-turbo"],
            "image": ["dall-e-3", "dall-e-2"]
        }
    
    def get_supported_parameters(self) -> List[str]:
        """Vrátí seznam podporovaných parametrů."""
        return ["temperature", "max_tokens", "top_p", "system_prompt"]
    
    def validate_model(self, model: str) -> bool:
        """Ověří zda je model podporován."""
        all_models = []
        for models in self.get_supported_models().values():
            all_models.extend(models)
        return model in all_models
    
    def _log_config(self):
        """Loguje aktuální konfiguraci pro audit."""
        logger.info(f"📊 OPENAI CONFIG AUDIT:")
        logger.info(f"   Model: {OPENAI_CONFIG['model']} (STRICT MODE - žádné fallbacky)")
        logger.info(f"   Temperature: {OPENAI_CONFIG['temperature']}")
        logger.info(f"   Max tokens: {OPENAI_CONFIG['max_tokens']}")
        logger.info(f"   Top_p: {OPENAI_CONFIG['top_p']}")
        logger.info(f"   Frequency penalty: {OPENAI_CONFIG['frequency_penalty']}")
        logger.info(f"   Presence penalty: {OPENAI_CONFIG['presence_penalty']}")
        logger.info(f"   Timeout: {OPENAI_CONFIG['timeout']}s")
    
    async def chat_completion(
        self, 
        system_prompt: str, 
        user_message: str, 
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Centralizované volání OpenAI Chat Completion API s auditovanými parametry.
        
        Args:
            system_prompt: System prompt pro asistenta
            user_message: Uživatelská zpráva
            model: Override pro model (optional)
            **kwargs: Dodatečné parametry (budou logovány ale ne použity!)
            
        Returns:
            Dict s výsledkem a metadata
        """
        # Model selection s fallback
        model_to_use = model or OPENAI_CONFIG["model"]
        
        # Varování před dodatečnými parametry
        if kwargs:
            logger.warning(f"⚠️ Ignoruji nepodporované parametry: {list(kwargs.keys())}")
        
        logger.info(f"🤖 CHAT_COMPLETION: model={model_to_use}")
        logger.info(f"📝 PROMPT_LENGTH: system={len(system_prompt)}, user={len(user_message)}")
        
        try:
            # Připravíme parametry
            api_params = {
                "model": model_to_use,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": OPENAI_CONFIG["temperature"],
                "top_p": OPENAI_CONFIG["top_p"],
                "frequency_penalty": OPENAI_CONFIG["frequency_penalty"],
                "presence_penalty": OPENAI_CONFIG["presence_penalty"]
            }
            
            # Přidáme max_tokens pouze pokud je specifikováno
            if OPENAI_CONFIG["max_tokens"] is not None:
                api_params["max_tokens"] = OPENAI_CONFIG["max_tokens"]
            
            response = self.client.chat.completions.create(**api_params)
            
            result = {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                "config_used": OPENAI_CONFIG.copy(),
                "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else None
            }
            
            logger.info(f"✅ CHAT_COMPLETION úspěšný: {result['usage']['total_tokens']} tokenů")
            return result
            
        except Exception as e:
            # STRICT MODE - žádné fallbacky
            logger.error(f"❌ Chat completion selhalo s modelem {model_to_use}: {str(e)}")
            raise
    
    async def image_generation(
        self, 
        prompt: str, 
        size: Optional[str] = None,
        quality: Optional[str] = None,
        style: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Centralizované volání DALL·E API pro generování obrázků.
        
        Args:
            prompt: Prompt pro generování obrázku
            size: Velikost obrázku (default z DALLE_CONFIG)
            quality: Kvalita obrázku (default z DALLE_CONFIG)
            style: Styl obrázku (default z DALLE_CONFIG)
            **kwargs: Dodatečné parametry (budou logovány ale ne použity!)
            
        Returns:
            Dict s výsledkem a metadata
        """
        # Použití auditovaných parametrů nebo defaultů
        size_to_use = size or DALLE_CONFIG["size"]
        quality_to_use = quality or DALLE_CONFIG["quality"]
        style_to_use = style or DALLE_CONFIG["style"]
        
        # Varování před dodatečnými parametry
        if kwargs:
            logger.warning(f"⚠️ Ignoruji nepodporované parametry: {list(kwargs.keys())}")
        
        # Limitace délky promptu pro DALL·E (max 1000 chars)
        if len(prompt) > 1000:
            prompt = prompt[:997] + "..."
            logger.warning(f"⚠️ Prompt zkrácen na 1000 znaků")
        
        logger.info(f"🎨 IMAGE_GENERATION: size={size_to_use}, quality={quality_to_use}, style={style_to_use}")
        logger.info(f"📝 PROMPT_LENGTH: {len(prompt)} chars")
        
        try:
            response = self.client.images.generate(
                model=DALLE_CONFIG["model"],
                prompt=prompt,
                n=DALLE_CONFIG["n"],
                size=size_to_use,
                quality=quality_to_use,
                style=style_to_use
            )
            
            # Vytvoří content string pro workflow kompatibilitu  
            images_data = [
                {
                    "url": img.url,
                    "revised_prompt": img.revised_prompt
                } for img in response.data
            ]
            
            # Content pro workflow - JSON string s obrázky
            content = f"Vygenerováno {len(images_data)} obrázků:\n"
            for i, img in enumerate(images_data, 1):
                content += f"{i}. {img['url']}\n   Prompt: {img['revised_prompt']}\n"
            
            result = {
                "content": content,  # 🚨 REQUIRED klíč pro workflow
                "images": images_data,
                "model": DALLE_CONFIG["model"],
                "config_used": {
                    "size": size_to_use,
                    "quality": quality_to_use,
                    "style": style_to_use,
                    "n": DALLE_CONFIG["n"]
                },
                "original_prompt": prompt,
                "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else None
            }
            
            logger.info(f"✅ IMAGE_GENERATION úspěšný: {len(result['images'])} obrázků")
            return result
            
        except Exception as e:
            logger.error(f"❌ Image generation selhalo: {str(e)}")
            raise

# Global instance pro jednoduché použití
_openai_client = None

def get_openai_client() -> OpenAIClient:
    """Vrátí globální instanci OpenAI clienta (singleton pattern)."""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAIClient()
    return _openai_client

# Convenience funkce pro přímé použití
def call_openai_chat(system_prompt: str, user_message: str, model: Optional[str] = None) -> Dict[str, Any]:
    """Convenience funkce pro chat completion."""
    client = get_openai_client()
    return client.chat_completion(system_prompt, user_message, model)

def call_openai_image(prompt: str, **kwargs) -> Dict[str, Any]:
    """Convenience funkce pro image generation."""
    client = get_openai_client()
    return client.image_generation(prompt, **kwargs)