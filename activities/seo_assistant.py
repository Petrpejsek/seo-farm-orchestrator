"""
SEOAssistant - SEO optimization krok v SEO pipeline
Optimalizuje content pro vyhledávače (meta tagy, klíčová slova, struktura).
"""

import logging
import os
from typing import Optional, Dict, Any
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

async def seo_assistant(content: str, assistant_id: Optional[str] = None) -> Dict[str, Any]:
    """Optimalizuje content pro vyhledávače (meta tagy, klíčová slova, struktura)."""
    
    logger.info(f"📈 SEOAssistant optimalizuje content: {len(content)} znaků")
    

    
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
        raise Exception("❌ ŽÁDNÝ assistant_id poskytnut! SEOAssistant nemůže běžet bez databázové konfigurace!")
    
    # ✅ POUŽÍVÁME POUZE SYSTEM_PROMPT Z DATABÁZE!
    # Všechny instrukce jsou v databázi jako system_prompt
    user_message = f"Optimalizuj následující content pro SEO:\n\n{content}"
    
    try:
        # Inicializace OpenAI client
        from utils.api_keys import get_api_key
        
        api_key = get_api_key("openai")
        if not api_key:
            logger.error("❌ OpenAI API klíč není k dispozici")
            raise Exception("❌ OpenAI API klíč není k dispozici pro SEOAssistant")
            
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
        
        optimized_content = response.choices[0].message.content.strip()
        return {"output": optimized_content}
        
    except Exception as e:
        logger.error(f"❌ SEO optimalizace selhala: {e}")
        raise Exception(f"SEOAssistant selhal: {e}")

def seo_assistant_sync(content: str, assistant_id: Optional[str] = None) -> str:
    import asyncio
    return asyncio.run(seo_assistant(content, assistant_id))