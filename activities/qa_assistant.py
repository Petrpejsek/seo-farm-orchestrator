"""
QAAssistant - Quality Assurance krok v SEO pipeline
Kontroluje kvalitu, gramatiku a konzistenci finálního obsahu.
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

async def qa_assistant(content: str, assistant_id: Optional[str] = None) -> Dict[str, Any]:
    """Kontroluje kvalitu, gramatiku a konzistenci finálního obsahu."""
    
    logger.info(f"✅ QAAssistant kontroluje kvalitu: {len(content)} znaků")
    
    # 🚫 ŽÁDNÉ HARDCODED DEFAULT PROMPTY! Používám POUZE databázi!

    
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
        raise Exception("❌ ŽÁDNÝ assistant_id poskytnut! QAAssistant nemůže běžet bez databázové konfigurace!")
    
    # Inicializace OpenAI client
    from utils.api_keys import get_api_key
    
    api_key = get_api_key("openai")
    if not api_key:
        logger.error("❌ OpenAI API klíč není k dispozici")
        raise Exception("❌ OpenAI API klíč není k dispozici pro QAAssistant")
        
    client = OpenAI(api_key=api_key)
    
    # ✅ POUŽÍVÁME POUZE SYSTEM_PROMPT Z DATABÁZE!
    # Všechny instrukce jsou v databázi jako system_prompt
    user_message = f"Proveď QA kontrolu následujícího obsahu:\n\n{content}"
    
    try:
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
            if "```json" in result:
                json_start = result.find("```json") + 7
                json_end = result.find("```", json_start)
                if json_end != -1:
                    json_str = result[json_start:json_end].strip()
                    qa_result = json.loads(json_str)
                    return {"output": json.dumps(qa_result, ensure_ascii=False)}
            qa_result = json.loads(result)
            return {"output": json.dumps(qa_result, ensure_ascii=False)}
        except json.JSONDecodeError as e:
            logger.error(f"❌ QA JSON parsing selhalo: {e}")
            raise Exception(f"QAAssistant nelze parsovat JSON response: {e}")
        
    except Exception as e:
        logger.error(f"❌ QA kontrola selhala: {e}")
        raise Exception(f"QAAssistant selhal: {e}")

def qa_assistant_sync(content: str, assistant_id: Optional[str] = None) -> Dict[str, Any]:
    import asyncio
    return asyncio.run(qa_assistant(content, assistant_id))