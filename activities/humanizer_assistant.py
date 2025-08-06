"""
HumanizerAssistant - Humanization krok v SEO pipeline
Humanizuje AI-generovaný content pro přirozenější čtení.
"""

import json
import logging
import os
from typing import Optional, Dict, Any
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)

async def humanizer_assistant(content: str, assistant_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Humanizuje AI-generovaný content pro přirozenější čtení.
    
    Args:
        content (str): AI-generovaný obsah k humanizaci
        assistant_id (str, optional): ID asistenta pro načtení parametrů z DB
        
    Returns:
        Dict[str, Any]: Dictionary s output klíčem obsahujícím humanizovaný content
    """
    
    logger.info(f"👤 HumanizerAssistant humanizuje content: {len(content)} znaků")
    
    # Výchozí parametry - BEZ FALLBACK PROMPTU!

    
    # Pokud máme assistant_id, načteme parametry z databáze
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
            else:
                raise Exception(f"❌ Asistent {assistant_id} nenalezen v databázi! Workflow MUSÍ selhat!")
        except Exception as e:
            logger.error(f"❌ Chyba při načítání parametrů: {e}")
            raise Exception(f"❌ Nelze načíst asistenta {assistant_id}: {e}")
    else:
        raise Exception("❌ ŽÁDNÝ assistant_id poskytnut! HumanizerAssistant nemůže běžet bez databázové konfigurace!")
    
    # ✅ POUŽÍVÁME POUZE SYSTEM_PROMPT Z DATABÁZE!
    # Všechny instrukce jsou v databázi jako system_prompt
    user_message = f"Humanizuj následující obsah:\n\n{content}"
    
    try:
        # Inicializace OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ OpenAI API klíč není dostupný")
            raise Exception("HumanizerAssistant: OpenAI API klíč není dostupný")
            
        client = OpenAI(api_key=api_key)
        
        # Sestavení zpráv pro OpenAI
        messages = [
            {"role": "system", "content": params["system_prompt"]},
            {"role": "user", "content": user_message}
        ]
        
        # Volání OpenAI API
        logger.info(f"🤖 Volám OpenAI API s modelem {params['model']}")
        response = client.chat.completions.create(
            model=params["model"],
            messages=messages,
            temperature=params["temperature"],
            top_p=params["top_p"],
            max_tokens=params["max_tokens"]
        )
        
        humanized_content = response.choices[0].message.content.strip()
        logger.info(f"✅ OpenAI API úspěšně humanizovalo content: {len(humanized_content)} znaků")
        
        # 🔧 FIX: Workflow očekává formát s "output" klíčem
        return {"output": humanized_content}
            
    except Exception as e:
        logger.error(f"❌ Humanization selhala: {e}")
        raise Exception(f"HumanizerAssistant selhal: {e}")



# Synchronní wrapper pro zpětnou kompatibilitu
def humanizer_assistant_sync(content: str, assistant_id: Optional[str] = None) -> Dict[str, Any]:
    """Synchronní verze pro testování"""
    import asyncio
    return asyncio.run(humanizer_assistant(content, assistant_id))