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

try:
    from api.database import get_prisma_client
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    print("⚠️ Database import failed - using fallback mode")

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
    
    # Výchozí parametry
    default_params = {
        "model": "gpt-4o",
        "temperature": 0.3,  # Nižší pro přesnější validaci
        "top_p": 0.9,
        "max_tokens": 1000,
        "system_prompt": "Jsi expert fact-checker a validátor informací. Tvým úkolem je kontrolovat přesnost faktů, statistik a tvrzení v poskytnutém obsahu. Zaměř se na ověření dat, zdrojů a logické konzistence informací."
    }
    
    # Pokud máme assistant_id, načteme parametry z databáze
    if assistant_id and DATABASE_AVAILABLE:
        try:
            prisma = await get_prisma_client()
            assistant = await prisma.assistant.find_unique(where={"id": assistant_id})
            
            if assistant:
                params = {
                    "model": assistant.model or default_params["model"],
                    "temperature": assistant.temperature if assistant.temperature is not None else default_params["temperature"],
                    "top_p": assistant.top_p if assistant.top_p is not None else default_params["top_p"],
                    "max_tokens": assistant.max_tokens or default_params["max_tokens"],
                    "system_prompt": assistant.system_prompt or default_params["system_prompt"]
                }
                logger.info(f"✅ Načteny parametry asistenta {assistant_id}")
            else:
                params = default_params
                logger.warning(f"⚠️ Asistent {assistant_id} nenalezen, používám výchozí parametry")
        except Exception as e:
            logger.error(f"❌ Chyba při načítání parametrů asistenta: {e}")
            params = default_params
    else:
        params = default_params
    
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
    
    # Prompt pro fact validation
    validation_prompt = f"""
Proveď důkladnou fact-check validaci následujícího obsahu:

{content_to_validate}

Potřebuji strukturovanou analýzu v těchto oblastech:

1. FACTUAL ACCURACY
- Kontrola čísel, statistik a dat
- Ověření tvrzení a claims
- Identifikace potenciálně nepřesných informací

2. SOURCE VERIFICATION
- Kontrola citovaných zdrojů
- Ověření autoritativnosti odkazů
- Doporučení na lepší/aktuálnější zdroje

3. LOGICAL CONSISTENCY
- Kontrola logických spojitostí
- Identifikace rozporů v argumentaci
- Ověření kauzálních vztahů

4. COMPLETENESS CHECK
- Chybějící důležité informace
- Oblasti vyžadující rozšíření
- Gaps v pokrytí tématu

5. CORRECTIONS & IMPROVEMENTS
- Konkrétní opravy faktických chyb
- Doporučené úpravy a doplnění
- Priority pro revision

Vrať strukturovaný JSON s těmito sekcemi a overall confidence score (0-100%).
    """
    
    try:
        # Sestavení zpráv pro OpenAI
        messages = []
        if params["system_prompt"]:
            messages.append({"role": "system", "content": params["system_prompt"]})
        messages.append({"role": "user", "content": validation_prompt})
        
        # Volání OpenAI API
        logger.info(f"🤖 Volám OpenAI API s modelem {params['model']}")
        response = client.chat.completions.create(
            model=params["model"],
            messages=messages,
            temperature=params["temperature"],
            top_p=params["top_p"],
            max_tokens=params["max_tokens"]
        )
        
        validation_result = response.choices[0].message.content.strip()
        logger.info("✅ OpenAI API úspěšně vrátilo výsledek validace")
        
        # Pokus o parsování JSON z odpovědi
        try:
            if "```json" in validation_result:
                json_start = validation_result.find("```json") + 7
                json_end = validation_result.find("```", json_start)
                if json_end != -1:
                    json_str = validation_result[json_start:json_end].strip()
                    parsed_data = json.loads(json_str)
                else:
                    json_str = validation_result[json_start:].strip()
                    parsed_data = json.loads(json_str)
            else:
                parsed_data = json.loads(validation_result)
            
            result_data = {
                "validation_results": parsed_data,
                "raw_response": validation_result,
                "input_data": input_data,
                "validation_status": "success",
                "assistant": "FactValidatorAssistant",
                "assistant_id": assistant_id,
                "model_used": params["model"],
                "timestamp": datetime.now().isoformat()
            }
            return {"output": json.dumps(result_data, ensure_ascii=False)}
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ FactValidator JSON parsing selhalo: {e}")
            raise Exception(f"FactValidatorAssistant nelze parsovat JSON response: {e}")
            
    except Exception as e:
        logger.error(f"❌ Fact validation selhala: {e}")
        raise Exception(f"FactValidatorAssistant selhal: {e}")



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