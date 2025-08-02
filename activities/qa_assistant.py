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
    
    default_params = {
        "model": "gpt-4o",
        "temperature": 0.2,  # Nízká pro precizní analýzu
        "top_p": 0.9,
        "max_tokens": 1500,
        "system_prompt": "Jsi expert na Quality Assurance pro web content. Kontroluješ gramatiku, styl, SEO, UX a celkovou kvalitu obsahu před publikací."
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
Proveď komplexní QA kontrolu následujícího obsahu:

{content}

Kontroluj tyto oblasti a vrať strukturovaný JSON:

1. GRAMMAR_CHECK:
   - errors: seznam gramatických chyb
   - suggestions: návrhy oprav
   - score: skóre 0-100

2. SEO_ANALYSIS:
   - title_optimization: analýza nadpisů
   - meta_tags: kontrola meta tagů
   - keyword_density: analýza klíčových slov
   - score: SEO skóre 0-100

3. READABILITY:
   - sentence_length: analýza délky vět
   - paragraph_structure: struktura odstavců
   - clarity: jasnost a srozumitelnost
   - score: čitelnost 0-100

4. TECHNICAL_CHECK:
   - html_validation: kontrola HTML
   - link_check: kontrola odkazů
   - image_alt_texts: alt texty obrázků
   - score: technické skóre 0-100

5. OVERALL_ASSESSMENT:
   - ready_for_publish: true/false
   - priority_fixes: seznam prioritních oprav
   - overall_score: celkové skóre 0-100

Vrať pouze JSON bez komentářů.
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