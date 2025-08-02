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
    
    default_params = {
        "model": "gpt-4o",
        "temperature": 0.5,
        "top_p": 0.9,
        "max_tokens": 2000,
        "system_prompt": "Jsi SEO expert. Optimalizuješ obsah pro vyhledávače - přidáváš meta tagy, optimalizuješ nadpisy, klíčová slova a strukturu pro lepší ranking."
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
Optimalizuj následující content pro SEO:

{content}

POŽADAVKY:
- Přidej/optimalizuj meta description (max 160 znaků)
- Optimalizuj nadpisy (H1, H2, H3) pro klíčová slova
- Přidej internal linking možnosti
- Optimalizuj keyword density
- Přidej schema.org markup kde je to vhodné
- Zlepši strukturu pro featured snippets
- Zachovej HTML strukturu

Vrať pouze optimalizovaný HTML obsah.
    """
    
    try:
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
        
        optimized_content = response.choices[0].message.content.strip()
        return {"output": optimized_content}
        
    except Exception as e:
        logger.error(f"❌ SEO optimalizace selhala: {e}")
        raise Exception(f"SEOAssistant selhal: {e}")

def seo_assistant_sync(content: str, assistant_id: Optional[str] = None) -> str:
    import asyncio
    return asyncio.run(seo_assistant(content, assistant_id))