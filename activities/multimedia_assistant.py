"""
MultimediaAssistant - Multimedia generation krok v SEO pipeline
Generuje multimedia elementy (obrazky, video nápady, infografiky).
"""

import json
import logging
import os
from typing import Dict, Any, Optional
from openai import OpenAI
from datetime import datetime

# Import pro databázi
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from api.database import get_prisma_client
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def multimedia_assistant(content: str, assistant_id: Optional[str] = None) -> Dict[str, Any]:
    """Generuje multimedia elementy (obrazky, video nápady, infografiky)."""
    
    logger.info(f"🎨 MultimediaAssistant generuje multimedia pro: {len(content)} znaků")
    
    # BEZ FALLBACK PROMPTU!

    
    if assistant_id and DATABASE_AVAILABLE:
        try:
            prisma = await get_prisma_client()
            assistant = await prisma.assistant.find_unique(where={"id": assistant_id})
            if assistant:
                if not all([assistant.model, assistant.temperature is not None, assistant.top_p is not None, assistant.max_tokens, assistant.system_prompt]):
                    raise Exception(f"❌ Asistent {assistant_id} má neúplnou konfiguraci!")
                
                params = {
                    "model": assistant.model,
                    "temperature": assistant.temperature,
                    "top_p": assistant.top_p,
                    "max_tokens": assistant.max_tokens,
                    "system_prompt": assistant.system_prompt
                }
        except Exception as e:
            logger.error(f"❌ Chyba při načítání parametrů: {e}")
            raise Exception(f"❌ Nelze načíst asistenta {assistant_id}: {e}")
    else:
        raise Exception("❌ ŽÁDNÝ assistant_id poskytnut! MultimediaAssistant nemůže běžet bez databázové konfigurace!")
    
    # ✅ POUŽÍVÁME POUZE SYSTEM_PROMPT Z DATABÁZE!
    # Všechny instrukce jsou v databázi jako system_prompt
    user_message = f"Navrhni multimedia elementy pro následující obsah:\n\n{content[:1000]}..."
    
    try:
        # Inicializace OpenAI klienta
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise Exception("❌ OPENAI_API_KEY není nastavený")
        
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model=params["model"],
            messages=[
                {"role": "system", "content": params["system_prompt"]},
                {"role": "user", "content": user_message}
            ],
            temperature=params["temperature"],
            top_p=params["top_p"],
            max_tokens=params["max_tokens"]
        )
        
        result = response.choices[0].message.content.strip()
        
        # Pokusíme se parsovat JSON
        try:
            multimedia_data = None
            if "```json" in result:
                json_start = result.find("```json") + 7
                json_end = result.find("```", json_start)
                if json_end != -1:
                    json_str = result[json_start:json_end].strip()
                    multimedia_data = json.loads(json_str)
            else:
                multimedia_data = json.loads(result)
            
            # Konverze na formát kompatibilní s ImageRendererAssistant
            primary_visuals = []
            if multimedia_data and "images" in multimedia_data:
                # 🚨 DVOJÍ HARD LIMIT: Vždy max 4 obrázky!
                images_to_process = multimedia_data["images"][:4]  # První limit
                if len(multimedia_data["images"]) > 4:
                    logger.error(f"🚨 GPT IGNOROVAL INSTRUKCE! Navrhlo {len(multimedia_data['images'])} obrázků místo max 4!")
                    logger.error(f"🚨 OPRAVUJI: Beru pouze prvních 4 obrázků")
                
                for img in images_to_process:
                    if len(primary_visuals) >= 4:  # Druhý limit - extra bezpečnost
                        logger.warning(f"🚨 EXTRA BEZPEČNOST: Dosaženo limitu 4 obrázků, ignoruji zbytek")
                        break
                        
                    primary_visuals.append({
                        "type": "image",
                        "image_prompt": f"{img.get('description', img.get('title', 'Professional image'))}, {img.get('alt_text', '')}",
                        "title": img.get("title", "Professional image"),
                        "purpose": img.get("purpose", "illustration"),
                        "alt_text": img.get("alt_text", ""),
                        "size": img.get("size_recommendation", "1024x1024")
                    })
            
            # 🚨 FINÁLNÍ KONTROLA: Nikdy víc než 4!
            if len(primary_visuals) > 4:
                logger.error(f"🚨 FINÁLNÍ KONTROLA: {len(primary_visuals)} > 4! Ořezávám.")
                primary_visuals = primary_visuals[:4]
            
            logger.info(f"🎨 MultimediaAssistant vygeneroval {len(primary_visuals)} primary visuals pro ImageRenderer")
            
            # Vrať ve formátu očekávaném ImageRenderer
            output_format = {
                "primary_visuals": primary_visuals,
                "optional_visuals": []
            }
            
            return {"status": "success", "output": output_format}
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Multimedia JSON parsing selhalo: {e}")
            raise Exception(f"MultimediaAssistant nelze parsovat JSON response: {e}")
        
    except Exception as e:
        logger.error(f"❌ Multimedia generation selhala: {e}")
        raise Exception(f"MultimediaAssistant selhal: {e}")

def multimedia_assistant_sync(content: str, assistant_id: Optional[str] = None) -> Dict[str, Any]:
    import asyncio
    return asyncio.run(multimedia_assistant(content, assistant_id))