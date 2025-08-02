"""
Gemini (Google) LLM Client pro SEO Farm Orchestrator.
Implementuje Google Gemini API s multi-provider podporou.
"""

import logging
from typing import Dict, Any, List, Optional
import httpx
import json

from .base import BaseLLMClient

logger = logging.getLogger(__name__)

# Gemini konfigurace
GEMINI_CONFIG = {
    "temperature": 0.7,
    "max_output_tokens": 2048,  # Gemini používá max_output_tokens
    "timeout": 120,
    "api_version": "v1"
}

class GeminiClient(BaseLLMClient):
    """
    Gemini (Google) LLM Client implementace.
    Podporuje Gemini-1.5 a Gemini-1.0 modely pro text generation.
    """
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.api_key = api_key
        self.base_url = f"https://generativelanguage.googleapis.com/{GEMINI_CONFIG['api_version']}"
        self._log_config()
    
    def _log_config(self):
        """Loguje aktuální konfiguraci pro audit."""
        logger.info(f"📊 GEMINI CONFIG AUDIT:")
        logger.info(f"   Temperature: {GEMINI_CONFIG['temperature']}")
        logger.info(f"   Max output tokens: {GEMINI_CONFIG['max_output_tokens']}")
        logger.info(f"   API Version: {GEMINI_CONFIG['api_version']}")
    
    async def chat_completion(
        self, 
        system_prompt: str, 
        user_message: str, 
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,  # Bez omezení tokenov
        **kwargs
    ) -> Dict[str, Any]:
        """
        Gemini Chat Completion přes Google Generative AI API.
        """
        self._log_request(model, system_prompt, user_message)
        
        # Ověření modelu
        if not self.validate_model(model):
            raise ValueError(f"Model {model} není podporován Gemini providerem")
        
        # Varování před nepodporovanými parametry
        unsupported = set(kwargs.keys()) - set(self.get_supported_parameters())
        if unsupported:
            logger.warning(f"⚠️ [GEMINI] Ignoruji nepodporované parametry: {list(unsupported)}")
        
        # Gemini formát - kombinuje system a user message
        combined_prompt = f"{system_prompt}\n\nUser: {user_message}\n\nAssistant:"
        
        # Gemini API endpoint
        url = f"{self.base_url}/models/{model}:generateContent"
        
        generation_config = {
            "temperature": temperature,
            "candidateCount": 1
        }
        
        # Přidáme maxOutputTokens pouze pokud je specifikováno a není -1 (neomezeno)
        if max_tokens is not None and max_tokens != -1:
            generation_config["maxOutputTokens"] = max_tokens
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": combined_prompt}
                    ]
                }
            ],
            "generationConfig": generation_config
        }
        
        try:
            async with httpx.AsyncClient(timeout=GEMINI_CONFIG["timeout"]) as client:
                response = await client.post(
                    url,
                    params={"key": self.api_key},
                    headers={"Content-Type": "application/json"},
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                
                # 🔧 ROBUSTNÍ GEMINI RESPONSE PARSING
                content = ""
                logger.info(f"🔍 GEMINI RAW RESPONSE KEYS: {list(data.keys())}")
                
                # Pokus 1: Standardní Gemini formát
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    logger.info(f"🔍 GEMINI CANDIDATE KEYS: {list(candidate.keys())}")
                    
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        logger.info(f"🔍 GEMINI PARTS COUNT: {len(parts)}")
                        if len(parts) > 0 and "text" in parts[0]:
                            content = parts[0]["text"]
                            logger.info(f"✅ GEMINI STANDARD PARSING: {len(content)} chars")
                
                # Pokus 2: Alternativní formáty
                if not content and "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    
                    # Zkus různé možné cesty k text obsahu
                    possible_paths = [
                        ["content", "parts", 0, "text"],
                        ["text"],
                        ["content", "text"],
                        ["output", "text"],
                        ["message", "content"],
                        ["choices", 0, "text"]
                    ]
                    
                    for path in possible_paths:
                        try:
                            temp_content = candidate
                            for key in path:
                                if isinstance(key, int):
                                    temp_content = temp_content[key]
                                else:
                                    temp_content = temp_content[key]
                            if isinstance(temp_content, str) and temp_content.strip():
                                content = temp_content
                                logger.info(f"✅ GEMINI ALTERNATIVE PATH {path}: {len(content)} chars")
                                break
                        except (KeyError, IndexError, TypeError):
                            continue
                
                # Pokus 3: Fallback na raw response jako string
                if not content and data:
                    # Pokud nic nefunguje, zkus převést celou response na string
                    if isinstance(data, dict) and any(key in data for key in ["text", "content", "message"]):
                        content = str(data.get("text") or data.get("content") or data.get("message", ""))
                        if content:
                            logger.warning(f"⚠️ GEMINI FALLBACK PARSING: {len(content)} chars")
                
                if not content:
                    logger.error(f"❌ GEMINI: Všechny pokusy o parsing selhaly")
                    logger.error(f"❌ GEMINI RAW DATA: {data}")
                    content = ""  # Explicitně nastavit prázdný string
                
                # Gemini usage metadata
                usage_metadata = data.get("usageMetadata", {})
                
                result = self._standardize_response(
                    content=content,
                    model=model,
                    usage={
                        "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
                        "completion_tokens": usage_metadata.get("candidatesTokenCount", 0),
                        "total_tokens": usage_metadata.get("totalTokenCount", 0)
                    },
                    metadata={
                        "config_used": {
                            "temperature": temperature,
                            "max_output_tokens": max_tokens
                        },
                        "gemini_data": {
                            "finish_reason": data.get("candidates", [{}])[0].get("finishReason"),
                            "safety_ratings": data.get("candidates", [{}])[0].get("safetyRatings", [])
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
            
            logger.error(f"❌ [GEMINI] HTTP Error {e.response.status_code}: {error_detail}")
            raise Exception(f"Gemini API error: {error_detail}")
            
        except Exception as e:
            logger.error(f"❌ [GEMINI] Chat completion selhalo: {str(e)}")
            raise
    
    async def image_generation(
        self, 
        prompt: str, 
        model: str = "imagen-4",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Gemini Image Generation přes Imagen-4 model.
        """
        self._log_request(model, "", prompt)
        
        # Ověření modelu
        if not self.validate_model(model):
            raise ValueError(f"Model {model} není podporován pro image generation")
        
        if model not in self.get_supported_models().get("image", []):
            raise ValueError(f"Model {model} není image generation model")
        
        # Imagen API endpoint (může se lišit od text API)
        url = f"{self.base_url}/models/{model}:generateContent"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"Generate an image: {prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "candidateCount": 1
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=GEMINI_CONFIG["timeout"]) as client:
                response = await client.post(
                    url,
                    params={"key": self.api_key},
                    headers={"Content-Type": "application/json"},
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Parsování Imagen response (může se lišit od text response)
                result = {
                    "type": "image_generation",
                    "model": model,
                    "prompt": prompt,
                    "status": "completed",
                    "provider": "gemini",
                    "raw_response": data
                }
                
                # Extrakce image URL nebo base64 dat
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    # TODO: Implementovať správne parsovanie podľa skutočného Imagen API response
                    result["image_url"] = candidate.get("imageUrl", "")
                    result["image_data"] = candidate.get("imageData", "")
                else:
                    raise Exception("Gemini nevrátil žádný obrázek")
                
                self._log_response(result)
                return result
                
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                error_detail = error_data.get("error", {}).get("message", str(e))
            except:
                error_detail = str(e)
            
            logger.error(f"❌ [GEMINI] Image generation HTTP Error {e.response.status_code}: {error_detail}")
            raise Exception(f"Gemini Imagen API error: {error_detail}")
            
        except Exception as e:
            logger.error(f"❌ [GEMINI] Image generation selhalo: {str(e)}")
            raise
    
    def get_supported_models(self) -> Dict[str, List[str]]:
        """Vrátí podporované Gemini modely dle nejnovější dokumentace."""
        return {
            "text": [
                # Nejnovější 2.5 série (text + multimodal)
                "gemini-2.5-pro",
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
                # Existující 1.5 série
                "gemini-1.5-pro",
                "gemini-1.5-flash", 
                "gemini-1.0-pro"
            ],
            "image": [
                "imagen-4"  # Nejnovější image generation model
            ],
            "video": [
                "veo-3"  # Video generation model
            ],
            "embedding": [
                "gemini-embedding-001"  # Embedding model
            ]
        }
    
    def get_supported_parameters(self) -> List[str]:
        """Vrátí podporované parametry pro Gemini."""
        return ["temperature", "max_tokens", "system_prompt"]
    
    def validate_model(self, model: str) -> bool:
        """Ověří platnost Gemini modelu."""
        all_models = []
        for model_list in self.get_supported_models().values():
            all_models.extend(model_list)
        return model in all_models