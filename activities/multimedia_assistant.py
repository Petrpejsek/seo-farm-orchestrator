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
    
    default_params = {
        "model": "gpt-4o",
        "temperature": 0.8,
        "top_p": 0.9,
        "max_tokens": 1500,
        "system_prompt": "Jsi kreativní multimedia specialist. Navrhuješ obrázky, videa, infografiky a další vizuální elementy pro web content."
    }
    
    if assistant_id and DATABASE_AVAILABLE:
        try:
            prisma = await get_prisma_client()
            assistant = await prisma.assistant.find_unique(where={"id": assistant_id})
            if assistant:
                default_params.update({
                    "model": assistant.model or default_params["model"],
                    "temperature": assistant.temperature if assistant.temperature is not None else default_params["temperature"],
                    "top_p": assistant.top_p if assistant.top_p is not None else default_params["top_p"],
                    "max_tokens": assistant.max_tokens or default_params["max_tokens"],
                    "system_prompt": assistant.system_prompt or default_params["system_prompt"]
                })
        except Exception as e:
            logger.error(f"❌ Chyba při načítání parametrů: {e}")
    
    prompt = f"""
Na základě následujícího obsahu navrhni multimedia elementy:

{content[:1000]}...

Vytvoř strukturovaný JSON s návrhy:

1. IMAGES - návrhy obrázků/fotografií
2. INFOGRAPHICS - návrhy infografik  
3. VIDEOS - návrhy video obsahu
4. INTERACTIVE - interaktivní elementy
5. SOCIAL_MEDIA - social media assets

Pro každý element uveď:
- title: název
- description: popis
- purpose: účel (hero, illustration, social, etc.)
- alt_text: alt text pro SEO
- size_recommendation: doporučená velikost

Vrať pouze JSON bez dalšího textu.
    """
    
    try:
        # Inicializace OpenAI klienta
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise Exception("❌ OPENAI_API_KEY není nastavený")
        
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model=default_params["model"],
            messages=[
                {"role": "system", "content": default_params["system_prompt"]},
                {"role": "user", "content": prompt}
            ],
            temperature=default_params["temperature"],
            top_p=default_params["top_p"],
            max_tokens=default_params["max_tokens"]
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
            image_prompts = []
            if multimedia_data and "images" in multimedia_data:
                for img in multimedia_data["images"]:
                    image_prompts.append({
                        "type": "image",
                        "image_prompt": f"{img.get('description', img.get('title', 'Professional image'))}, {img.get('alt_text', '')}",
                        "title": img.get("title", "Professional image"),
                        "purpose": img.get("purpose", "illustration"),
                        "size": img.get("size_recommendation", "1024x1024")
                    })
            
            # Návrat s output klíčem pro workflow kompatibilitu
            return {
                "output": image_prompts,  # ✅ NATIVNÍ OBJEKT, NE STRING!
                "multimedia_suggestions": multimedia_data,
                "image_prompts_count": len(image_prompts)
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Multimedia JSON parsing selhalo: {e}")
            raise Exception(f"MultimediaAssistant nelze parsovat JSON response: {e}")
        
    except Exception as e:
        logger.error(f"❌ Multimedia generation selhala: {e}")
        raise Exception(f"MultimediaAssistant selhal: {e}")

def multimedia_assistant_sync(content: str, assistant_id: Optional[str] = None) -> Dict[str, Any]:
    import asyncio
    return asyncio.run(multimedia_assistant(content, assistant_id))