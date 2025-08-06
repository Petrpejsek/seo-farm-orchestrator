"""
BriefAssistant - První krok v SEO pipeline
Transformuje volně zadané téma na jednoznačně formulované SEO zadání s metadaty.
"""

import json
import logging
import os
from typing import Dict, Any, Optional
from openai import OpenAI
from datetime import datetime

# Import pro databázi - musíme ho importovat z backend struktury
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from api.database import get_prisma_client

logger = logging.getLogger(__name__)

# Inicializace OpenAI klienta
try:
    from utils.api_keys import get_api_key
    client = OpenAI(api_key=get_api_key("openai"))
except Exception as e:
    logger.error(f"❌ Nelze inicializovat OpenAI client: {e}")
    # STRICT MODE - žádné fallbacky na environment variables
    raise Exception(f"❌ OpenAI client inicializace selhala: {e}")

async def brief_assistant(topic: str, assistant_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Transformuje volné téma na SEO-ready zadání s metadaty.
    
    Args:
        topic (str): Volně zadané téma od uživatele
        assistant_id (str, optional): ID asistenta pro načtení parametrů z DB
        
    Returns:
        Dict[str, Any]: JSON s transformovaným zadáním a metadaty
    """
    
    logger.info(f"🎯 BriefAssistant zpracovává téma: {topic}")
    
    # Výchozí parametry - BEZ FALLBACK PROMPTU!

    
    # Pokud máme assistant_id, načteme parametry z DB
    if assistant_id:
        try:
            prisma = await get_prisma_client()
            assistant = await prisma.assistant.find_unique(where={"id": assistant_id})
            
            if assistant:
                logger.info(f"📋 Načten asistent: {assistant.name}")
                params = {
                    "model": assistant.model,
                    "temperature": assistant.temperature,
                    "top_p": assistant.top_p,
                    "max_tokens": assistant.max_tokens,
                    "system_prompt": assistant.system_prompt
                }
            else:
                raise Exception(f"❌ Asistent {assistant_id} nenalezen v databázi! Workflow MUSÍ selhat!")
        except Exception as e:
            logger.error(f"❌ Chyba při načítání asistenta: {e}")
            raise Exception(f"❌ Nelze načíst asistenta {assistant_id}: {e}")
    else:
        raise Exception("❌ ŽÁDNÝ assistant_id poskytnut! BriefAssistant nemůže běžet bez databázové konfigurace!")
    
    logger.info(f"🔧 Parametry: model={params['model']}, temp={params['temperature']}, max_tokens={params['max_tokens']}")
    
    # Inicializace OpenAI client
    from utils.api_keys import get_api_key
    
    api_key = get_api_key("openai")
    if not api_key:
        logger.error("❌ OpenAI API klíč není k dispozici")
        raise Exception("❌ OpenAI API klíč není k dispozici pro BriefAssistant")
        
    client = OpenAI(api_key=api_key)
    
    # ✅ POUŽÍVÁME POUZE SYSTEM_PROMPT Z DATABÁZE!
    # Všechny instrukce jsou v databázi jako system_prompt
    user_message = f"Zpracuj téma: {topic}"
    
    # Volání OpenAI API
    try:
        messages = [
            {
                "role": "system",
                "content": params["system_prompt"]
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
        
        response = client.chat.completions.create(
            model=params["model"],
            messages=messages,
            temperature=params["temperature"],
            top_p=params["top_p"],
            max_tokens=params["max_tokens"]
        )
        
        # Výstup přímo z LLM (system_prompt z databáze obsahuje instrukce)
        brief_content = response.choices[0].message.content.strip()
        
        result = {
            "output": brief_content,  # 🚨 REQUIRED klíč pro workflow
            "assistant": "BriefAssistant",
            "assistant_id": assistant_id,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ BriefAssistant dokončen: {len(brief_content)} znaků")
        return result
        
    except Exception as e:
        logger.error(f"❌ Chyba při volání OpenAI: {e}")
        # ❌ ŽÁDNÉ FALLBACKY - podle memory 4982004
        raise Exception(f"BriefAssistant selhal: {e}")



# Synchronní wrapper pro zpětnou kompatibilitu
def brief_assistant_sync(topic: str, assistant_id: Optional[str] = None) -> Dict[str, Any]:
    """Synchronní verze pro testování"""
    import asyncio
    return asyncio.run(brief_assistant(topic, assistant_id))

# Testovací funkce pro vývoj
if __name__ == "__main__":
    # Test příklady
    test_topics = [
        "solární panely do bytu",
        "AI nástroje pro marketing", 
        "e-commerce optimalizace",
        "zdravé vaření"
    ]
    
    for topic in test_topics:
        print(f"\n--- Test: {topic} ---")
        result = brief_assistant_sync(topic)
        print(json.dumps(result, indent=2, ensure_ascii=False))