"""
DraftAssistant - Draft creation krok v SEO pipeline
Vytváří první draft článku na základě research dat a briefu.
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
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def draft_assistant(input_data: Dict[str, Any], assistant_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Vytváří první draft článku na základě research dat a briefu.
    
    Args:
        input_data (Dict[str, Any]): Kombinace briefu a research dat
        assistant_id (str, optional): ID asistenta pro načtení parametrů z DB
        
    Returns:
        str: První draft článku v HTML nebo markdown formátu
    """
    
    logger.info(f"✍️ DraftAssistant vytváří draft z dat: {len(str(input_data))} znaků")
    
    # Výchozí parametry - BEZ FALLBACK PROMPTU!

    
    # Pokud máme assistant_id, načteme parametry z databáze
    if assistant_id:
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
                logger.info(f"✅ Načteny parametry asistenta {assistant_id}")
            else:
                raise Exception(f"❌ Asistent {assistant_id} nenalezen v databázi! Workflow MUSÍ selhat!")
        except Exception as e:
            logger.error(f"❌ Chyba při načítání parametrů asistenta: {e}")
            raise Exception(f"❌ Nelze načíst asistenta {assistant_id}: {e}")
    else:
        raise Exception("❌ ŽÁDNÝ assistant_id poskytnut! DraftAssistant nemůže běžet bez databázové konfigurace!")
    
    # ✅ POUŽÍVÁME POUZE SYSTEM_PROMPT Z DATABÁZE!
    # Všechny instrukce jsou v databázi jako system_prompt
    user_message = f"Vytvoř článek na základě těchto podkladů:\n\n{str(input_data)[:2000]}..."
    
    try:
        # Inicializace OpenAI client
        from utils.api_keys import get_api_key
        
        api_key = get_api_key("openai")
        if not api_key:
            logger.error("❌ OpenAI API klíč není k dispozici")
            raise Exception("❌ OpenAI API klíč není k dispozici pro DraftAssistant")
            
        client = OpenAI(api_key=api_key)
        
        # Sestavení zpráv pro OpenAI
        messages = []
        if params["system_prompt"]:
            messages.append({"role": "system", "content": params["system_prompt"]})
        messages.append({"role": "user", "content": user_message})
        
        # Volání OpenAI API
        logger.info(f"🤖 Volám OpenAI API s modelem {params['model']}")
        response = client.chat.completions.create(
            model=params["model"],
            messages=messages,
            temperature=params["temperature"],
            top_p=params["top_p"],
            max_tokens=params["max_tokens"]
        )
        
        draft_content = response.choices[0].message.content.strip()
        logger.info(f"✅ OpenAI API úspěšně vytvořilo draft: {len(draft_content)} znaků")
        
        return {"output": draft_content}
            
    except Exception as e:
        logger.error(f"❌ Draft creation selhala: {e}")
        raise Exception(f"DraftAssistant selhal: {e}")



# Synchronní wrapper pro zpětnou kompatibilitu
def draft_assistant_sync(input_data: Dict[str, Any], assistant_id: Optional[str] = None) -> str:
    """Synchronní verze pro testování"""
    import asyncio
    return asyncio.run(draft_assistant(input_data, assistant_id))

# Testovací funkce pro vývoj
if __name__ == "__main__":
    # Test příklady
    test_data = {
        "topic": "AI nástroje pro content marketing",
        "brief": {
            "brief": "Vytvoř průvodce AI nástroji pro content marketing v roce 2025",
            "metadata": {
                "type": "SEO",
                "intent": "informative",
                "audience": "marketéři",
                "keyword_focus": "ai content marketing tools"
            }
        },
        "research_data": {
            "key_facts": [
                "AI nástroje zvyšují produktivitu o 40%",
                "95% marketérů plánuje použít AI v roce 2025",
                "Content AI trh roste o 30% ročně"
            ],
            "target_audience": {
                "primary": "Marketéři a content tvůrci",
                "demographics": "25-40 let, marketing background"
            },
            "content_angles": [
                "ROI AI nástrojů",
                "Nejlepší AI nástroje 2025",
                "Implementace do workflow"
            ]
        }
    }
    
    print("\n--- Draft Creation Test ---")
    result = draft_assistant_sync(test_data)
    print(f"Draft délka: {len(result)} znaků")
    print(result[:500] + "..." if len(result) > 500 else result)