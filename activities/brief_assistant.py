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

try:
    from api.database import get_prisma_client
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    print("⚠️ Database import failed - using fallback mode")

logger = logging.getLogger(__name__)

# Inicializace OpenAI klienta
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    
    # Výchozí parametry
    default_params = {
        "model": "gpt-4o",
        "temperature": 0.8,
        "top_p": 0.9,
        "max_tokens": 800,
        "system_prompt": "Jsi expert na SEO a content marketing. Tvým úkolem je transformovat volně zadaná témata na precizní SEO zadání s jasně definovanými metadaty. Zaměř se na search intent, target audience a keyword strategy."
    }
    
    # Pokud máme assistant_id, načteme parametry z DB
    if assistant_id and DATABASE_AVAILABLE:
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
                    "system_prompt": assistant.system_prompt or default_params["system_prompt"]
                }
            else:
                logger.warning(f"⚠️ Asistent {assistant_id} nenalezen, používám výchozí parametry")
                params = default_params
        except Exception as e:
            logger.error(f"❌ Chyba při načítání asistenta: {e}")
            params = default_params
    else:
        params = default_params
    
    logger.info(f"🔧 Parametry: model={params['model']}, temp={params['temperature']}, max_tokens={params['max_tokens']}")
    
    # Volání OpenAI API
    try:
        messages = [
            {
                "role": "system",
                "content": params["system_prompt"]
            },
            {
                "role": "user", 
                "content": f"""Transformuj toto volně zadané téma na profesionální SEO zadání:

TÉMA: "{topic}"

Vrať JSON odpověď v tomto formátu:
{{
  "brief": "Přesně formulované SEO zadání (max 150 znaků)",
  "metadata": {{
    "type": "SEO",
    "intent": "informative/commercial/navigational/transactional",
    "audience": "target skupina",
    "keyword_focus": "hlavní klíčové slovo",
    "content_type": "guide/comparison/howto/review/list",
    "estimated_length": "1500-2000 words",
    "difficulty": "easy/medium/hard"
  }}
}}"""
            }
        ]
        
        response = client.chat.completions.create(
            model=params["model"],
            messages=messages,
            temperature=params["temperature"],
            top_p=params["top_p"],
            max_tokens=params["max_tokens"],
            response_format={"type": "json_object"}
        )
        
        # Parsování OpenAI odpovědi
        openai_content = response.choices[0].message.content
        parsed_response = json.loads(openai_content)
        
        # Finální struktura odpovědi
        result = {
            "brief": parsed_response.get("brief", f"SEO průvodce: {topic}"),
            "metadata": parsed_response.get("metadata", {
                "type": "SEO",
                "intent": "informative",
                "audience": "general",
                "keyword_focus": topic.lower(),
                "content_type": "guide",
                "estimated_length": "2000-3000 words",
                "difficulty": "medium"
            }),
            "original_topic": topic,
            "transformation_status": "success",
            "assistant": "BriefAssistant",
            "assistant_id": assistant_id,
            "openai_params": params,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ BriefAssistant dokončen: {result['brief']}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Chyba při volání OpenAI: {e}")
        
        # Fallback na původní logiku při selhání
        return await brief_assistant_fallback(topic, assistant_id)

async def brief_assistant_fallback(topic: str, assistant_id: Optional[str] = None) -> Dict[str, Any]:
    """Fallback verze bez OpenAI pro případy selhání"""
    
    logger.warning("🔄 Používám fallback verzi BriefAssistant")
    
    # Původní placeholder logika
    topic_lower = topic.lower()
    
    if "solární" in topic_lower or "solar" in topic_lower:
        brief = "Instalace solárních panelů pro byty ve městech – ekonomika, omezení a dotace 2025"
        metadata = {
            "type": "SEO",
            "intent": "informative",
            "audience": "homeowners",
            "keyword_focus": "solární panely byty",
            "content_type": "guide",
            "estimated_length": "2500-3000 words",
            "difficulty": "medium"
        }
    elif "ai" in topic_lower or "umělá inteligence" in topic_lower:
        brief = f"AI nástroje pro {topic} – kompletní průvodce výběrem a implementací"
        metadata = {
            "type": "SEO", 
            "intent": "commercial",
            "audience": "professionals",
            "keyword_focus": "ai nástroje",
            "content_type": "comparison",
            "estimated_length": "3000-4000 words",
            "difficulty": "medium"
        }
    else:
        brief = f"Komplexní průvodce: {topic} – tipy, trendy a praktické rady 2025"
        metadata = {
            "type": "SEO",
            "intent": "informative",
            "audience": "general",
            "keyword_focus": topic.lower(),
            "content_type": "guide",
            "estimated_length": "2000-3000 words", 
            "difficulty": "medium"
        }
    
    return {
        "brief": brief,
        "metadata": metadata,
        "original_topic": topic,
        "transformation_status": "fallback",
        "assistant": "BriefAssistant",
        "assistant_id": assistant_id,
        "timestamp": datetime.now().isoformat()
    }

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