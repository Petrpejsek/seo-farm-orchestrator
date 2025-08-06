"""
FactValidatorAssistant - Fact validation krok v SEO pipeline
Validuje fakta a kontroluje přesnost informací v contentu.
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

async def fact_validator_assistant(input_data: Dict[str, Any], assistant_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Validuje fakta a kontroluje přesnost informací v contentu.
    
    Args:
        input_data (Dict[str, Any]): Data k validaci (například research data nebo draft)
        assistant_id (str, optional): ID asistenta pro načtení parametrů z DB
        
    Returns:
        Dict[str, Any]: JSON s výsledky validace a opravami
    """
    
    logger.info(f"✅ FactValidatorAssistant validuje data: {len(str(input_data))} znaků")
    


    
    # Pokud máme assistant_id, načteme parametry z databáze
    if assistant_id:
        try:
            prisma = await get_prisma_client()
            assistant = await prisma.assistant.find_unique(where={"id": assistant_id})
            
            if assistant:
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
        raise Exception("❌ ŽÁDNÝ assistant_id poskytnut! FactValidatorAssistant nemůže běžet bez databázové konfigurace!")
    
    # Extrakce obsahu k validaci
    content_to_validate = ""
    if isinstance(input_data, dict):
        # Zkusíme najít text k validaci z různých možných klíčů
        content_keys = ['research_data', 'content', 'draft', 'generated', 'text', 'data']
        for key in content_keys:
            if key in input_data:
                if isinstance(input_data[key], str):
                    content_to_validate = input_data[key]
                else:
                    content_to_validate = json.dumps(input_data[key], ensure_ascii=False)
                break
        
        if not content_to_validate:
            content_to_validate = json.dumps(input_data, ensure_ascii=False)
    else:
        content_to_validate = str(input_data)
    
    # ✅ POUŽÍVÁME POUZE SYSTEM_PROMPT Z DATABÁZE!
    # Všechny instrukce jsou v databázi jako system_prompt
    user_message = f"Proveď fact-check validaci následujícího obsahu:\n\n{content_to_validate}"
    
    # ✅ STRICT IMPLEMENTATION - funguje pouze přes workflow systém!
    if not assistant_id:
        raise Exception("❌ FactValidator vyžaduje assistant_id pro databázovou konfiguraci!")
    
    try:
        # Volání OpenAI API
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
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
        
        validation_result = response.choices[0].message.content.strip()
        
        result_data = {
            "validation_results": validation_result,
            "validation_status": "completed",
            "assistant": "FactValidatorAssistant",
            "assistant_id": assistant_id,
            "model_used": params["model"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ FactValidator selhal: {e}")
        raise Exception(f"❌ FactValidator selhal: {str(e)} - workflow nemůže pokračovat")
    
    return {"output": json.dumps(result_data, ensure_ascii=False)}



# Synchronní wrapper pro zpětnou kompatibilitu
def fact_validator_assistant_sync(input_data: Dict[str, Any], assistant_id: Optional[str] = None) -> Dict[str, Any]:
    """Synchronní verze pro testování"""
    import asyncio
    return asyncio.run(fact_validator_assistant(input_data, assistant_id))

# Testovací funkce pro vývoj
if __name__ == "__main__":
    # Test příklady
    test_data = {
        "research_data": {
            "key_facts": [
                "AI technologie zažívají exponenciální růst",
                "Trh s AI má hodnotu přes 100 miliard dolarů",
                "ChatGPT má 180 milionů aktivních uživatelů"
            ],
            "statistics": "OpenAI byla založena v roce 2015",
            "sources": ["McKinsey AI Report", "Gartner Research"]
        }
    }
    
    print("\n--- Fact Validation Test ---")
    result = fact_validator_assistant_sync(test_data)
    print(json.dumps(result, indent=2, ensure_ascii=False))