"""
Claude (Anthropic) LLM Client pro SEO Farm Orchestrator.
Implementuje Anthropic Claude API s multi-provider podporou.
"""

import logging
from typing import Dict, Any, List, Optional
import httpx
import json

from .base import BaseLLMClient

logger = logging.getLogger(__name__)

# Claude konfigurace
CLAUDE_CONFIG = {
    "temperature": 0.7,
    "max_tokens": 4000,  # Claude má vyšší limit
    "timeout": 120,
    "api_version": "2023-06-01"
}

class ClaudeClient(BaseLLMClient):
    """
    Claude (Anthropic) LLM Client implementace.
    Podporuje Claude-3 modely pro text generation.
    """
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": CLAUDE_CONFIG["api_version"],
            "content-type": "application/json"
        }
        self._log_config()
    
    def _log_config(self):
        """Loguje aktuální konfiguraci pro audit."""
        logger.info(f"📊 CLAUDE CONFIG AUDIT:")
        logger.info(f"   Temperature: {CLAUDE_CONFIG['temperature']}")
        logger.info(f"   Max tokens: {CLAUDE_CONFIG['max_tokens']}")
        logger.info(f"   API Version: {CLAUDE_CONFIG['api_version']}")
    
    async def chat_completion(
        self, 
        system_prompt: str, 
        user_message: str, 
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 800,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Claude Chat Completion přes Anthropic API.
        """
        self._log_request(model, system_prompt, user_message)
        
        # Ověření modelu
        if not self.validate_model(model):
            raise ValueError(f"Model {model} není podporován Claude providerem")
        
        # Varování před nepodporovanými parametry
        unsupported = set(kwargs.keys()) - set(self.get_supported_parameters())
        if unsupported:
            logger.warning(f"⚠️ [CLAUDE] Ignoruji nepodporované parametry: {list(unsupported)}")
        
        # Claude má specifický formát pro system prompt
        messages = [
            {"role": "user", "content": user_message}
        ]
        
        # Claude vyžaduje povinně max_tokens field s validní hodnotou
        if max_tokens is None or max_tokens == -1:
            effective_max_tokens = 4096  # Claude-3 maximum
        else:
            effective_max_tokens = max_tokens
            
        payload = {
            "model": model,
            "max_tokens": effective_max_tokens,
            "temperature": temperature,
            "system": system_prompt,  # Claude má samostatné system pole
            "messages": messages
        }
        
        try:
            async with httpx.AsyncClient(timeout=CLAUDE_CONFIG["timeout"]) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Claude response format parsing
                content = ""
                if "content" in data and len(data["content"]) > 0:
                    content = data["content"][0].get("text", "")
                
                usage = data.get("usage", {})
                
                result = self._standardize_response(
                    content=content,
                    model=data.get("model", model),
                    usage={
                        "prompt_tokens": usage.get("input_tokens", 0),
                        "completion_tokens": usage.get("output_tokens", 0),
                        "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                    },
                    metadata={
                        "config_used": {
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        },
                        "claude_data": {
                            "stop_reason": data.get("stop_reason"),
                            "stop_sequence": data.get("stop_sequence")
                        }
                    }
                )
                
                self._log_response(result)
                return result
                
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                error_detail = error_data.get("error", {}).get("message", str(e))
            except:
                error_detail = str(e)
            
            logger.error(f"❌ [CLAUDE] HTTP Error {e.response.status_code}: {error_detail}")
            raise Exception(f"Claude API error: {error_detail}")
            
        except Exception as e:
            logger.error(f"❌ [CLAUDE] Chat completion selhalo: {str(e)}")
            raise
    
    async def image_generation(
        self, 
        prompt: str, 
        model: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Claude nepodporuje image generation.
        """
        raise NotImplementedError("Claude nepodporuje generování obrázků")
    
    def get_supported_models(self) -> Dict[str, List[str]]:
        """Vrátí podporované Claude modely dle nejnovější dokumentace."""
        return {
            "text": [
                # Nejnovější 2025 modely
                "claude-3-opus-20250514",
                "claude-sonnet-4-20250514",
                "claude-3-7-sonnet-20250219",
                # Aktuální 3.5 série
                "claude-3-5-sonnet-20241022",  # v2
                "claude-3-5-sonnet-20240620",
                "claude-3-5-haiku-20241022",
                # Základní modely
                "claude-3-opus-20240229",
                "claude-3-haiku-20240307"
            ],
            "image": []  # Claude nepodporuje image generation
        }
    
    def get_supported_parameters(self) -> List[str]:
        """Vrátí podporované parametry pro Claude."""
        return ["temperature", "max_tokens", "system_prompt"]
    
    def validate_model(self, model: str) -> bool:
        """Ověří platnost Claude modelu."""
        all_models = []
        for model_list in self.get_supported_models().values():
            all_models.extend(model_list)
        return model in all_models