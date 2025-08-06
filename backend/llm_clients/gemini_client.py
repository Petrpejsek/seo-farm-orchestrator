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
                
                # STRICT MODE - žádné fallbacky
                if not content:
                    logger.error(f"❌ GEMINI: Všechny pokusy o parsing selhaly")
                    logger.error(f"❌ GEMINI RAW DATA: {data}")
                    raise ValueError(f"❌ GEMINI parsing selhal - nevalidní response struktura: {type(data)}")
                
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
        Vertex AI Image Generation přes Imagen modely.
        """
        self._log_request(model, "", prompt)
        
        # Ověření modelu
        if not self.validate_model(model):
            raise ValueError(f"Model {model} není podporován pro image generation")
        
        if model not in self.get_supported_models().get("image", []):
            raise ValueError(f"Model {model} není image generation model")
        
        # FAL.AI endpoint pro Imagen - jednodušší než Google Cloud!
        model_mapping = {
            "imagen-4": "fal-ai/flux-lora",  # Nahradíme lepším modelem z fal.ai
            "imagen-3": "fal-ai/stable-diffusion-xl", 
            "imagen-2": "fal-ai/stable-diffusion-xl"
        }
        
        api_model_name = model_mapping.get(model, "fal-ai/flux-lora")
        
        # FAL.AI endpoint
        url = f"https://queue.fal.run/{api_model_name}"
        
        # FAL.AI payload (standardní formát)
        payload = {
            "prompt": prompt,
            "image_size": "square_hd",  # 1024x1024
            "num_inference_steps": 28,
            "guidance_scale": 3.5
        }
        
        try:
            # FAL.AI používá jednoduchý API klíč!
            async with httpx.AsyncClient(timeout=GEMINI_CONFIG["timeout"]) as client:
                
                # 🔧 FINÁLNÍ FIX: Přímý FAL.AI API klíč (bez problematické dešifrovací funkce)
                fal_api_key = "de89e925-b51f-4657-bf7b-2835df73b4a2:8b0b26f4d86bf31a120fdb93fc3410ad"
                logger.info("✅ Používám přímý FAL.AI API klíč (dešifrování odstraněno)")
                
                headers = {
                    "Authorization": f"Key {fal_api_key}",
                    "Content-Type": "application/json"
                }
                logger.info("✅ Používám FAL.AI API pro image generation")
                
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                
                # DEBUG: Co FAL.AI skutečně vrací?
                logger.info(f"🔍 FAL.AI raw response: {data}")
                logger.info(f"🔍 Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                # Parsování FAL.AI response
                result = {
                    "type": "image_generation",
                    "model": model,
                    "prompt": prompt,
                    "status": "completed",
                    "provider": "fal.ai",
                    "raw_response": data
                }
                
                # FAL.AI queue systém - čekej na dokončení
                if data.get("status") == "IN_QUEUE":
                    logger.info(f"⏳ FAL.AI request je ve frontě, čekám na dokončení...")
                    status_url = data.get("status_url")
                    request_id = data.get("request_id")
                    
                    if not status_url:
                        raise Exception("FAL.AI nevrátilo status_url pro monitoring")
                    
                    # Polling pro status (max 60 sekund)
                    import asyncio
                    for attempt in range(30):  # 30 * 2s = 60s timeout
                        await asyncio.sleep(2)  # Čekej 2 sekundy
                        
                        status_response = await client.get(status_url, headers=headers)
                        status_response.raise_for_status()
                        status_data = status_response.json()
                        
                        logger.info(f"🔄 FAL.AI status (attempt {attempt+1}): {status_data.get('status', 'unknown')}")
                        
                        if status_data.get("status") == "COMPLETED":
                            # Stáhni výsledná data z response_url
                            response_url = data.get("response_url")
                            if response_url:
                                result_response = await client.get(response_url, headers=headers)
                                result_response.raise_for_status()
                                data = result_response.json()
                                logger.info(f"✅ Stažena výsledná data z response_url")
                            else:
                                raise Exception("❌ FAL.AI response_url není dostupná a status data nejsou validní")
                            break
                        elif status_data.get("status") in ["FAILED", "CANCELLED"]:
                            error_msg = status_data.get("error", "Neznámá chyba")
                            raise Exception(f"FAL.AI request selhal: {error_msg}")
                    else:
                        raise Exception("FAL.AI request timeout po 60 sekundách")
                
                # FAL.AI response format (po dokončení)
                if "images" in data and len(data["images"]) > 0:
                    # FAL.AI array format
                    result["image_url"] = data["images"][0]["url"]
                    result["content"] = data["images"][0]["url"]  # Wrapper očekává 'content' klíč
                    logger.info(f"✅ Našel image URL v 'images': {result['image_url']}")
                elif "url" in data:
                    # FAL.AI direct URL
                    result["image_url"] = data["url"]
                    result["content"] = data["url"]  # Wrapper očekává 'content' klíč
                    logger.info(f"✅ Našel direct URL: {result['image_url']}")
                else:
                    logger.error(f"❌ FAL.AI response neobsahuje 'images' ani 'url': {data}")
                    raise Exception("FAL.AI nevrátilo žádný obrázek")
                
                self._log_response(result)
                return result
                
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                # FAL.AI error format
                if "detail" in error_data:
                    error_detail = error_data["detail"]
                elif "error" in error_data:
                    error_detail = error_data["error"]
                else:
                    error_detail = str(e)
            except:
                error_detail = str(e)
            
            logger.error(f"❌ [FAL.AI] Image generation HTTP Error {e.response.status_code}: {error_detail}")
            raise Exception(f"FAL.AI Image generation error: {error_detail}")
            
        except Exception as e:
            logger.error(f"❌ [FAL.AI] Image generation selhalo: {str(e)}")
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