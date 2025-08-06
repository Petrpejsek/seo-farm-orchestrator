"""
ResearchAssistant - Research krok v SEO pipeline
Provádí online research a shromažďuje podklady k zadanému tématu.
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

async def research_assistant(topic: str, assistant_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Provádí research k zadanému tématu a shromažďuje podklady.
    
    Args:
        topic (str): Téma pro research
        assistant_id (str, optional): ID asistenta pro načtení parametrů z DB
        
    Returns:
        Dict[str, Any]: JSON s výsledky research a shromážděnými podklady
    """
    
    logger.info(f"🔍 ResearchAssistant provádí research k tématu: {topic}")
    
    # Výchozí parametry

    
    # Pokud máme assistant_id, načteme parametry z databáze
    if assistant_id:
        try:
            prisma = await get_prisma_client()
            assistant = await prisma.assistant.find_unique(where={"id": assistant_id})
            
            if assistant:
                # Použijeme parametry z databáze
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
        raise Exception("❌ ŽÁDNÝ assistant_id poskytnut! ResearchAssistant nemůže běžet bez databázové konfigurace!")
    
    # ✅ POUŽÍVÁME POUZE SYSTEM_PROMPT Z DATABÁZE!
    # Všechny instrukce jsou v databázi jako system_prompt
    user_message = f"Proveď research k tématu: {topic}"
    
    try:
        # Inicializace OpenAI client
        from utils.api_keys import get_api_key
        
        api_key = get_api_key("openai")
        if not api_key:
            logger.error("❌ OpenAI API klíč není k dispozici")
            raise Exception("❌ OpenAI API klíč není k dispozici pro ResearchAssistant")
            
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
        
        research_result = response.choices[0].message.content.strip()
        logger.info("✅ OpenAI API úspěšně vrátilo výsledek")
        
        # Pokus o parsování JSON z odpovědi
        try:
            # Pokud odpověď obsahuje JSON block, extrahujeme ho
            if "```json" in research_result:
                json_start = research_result.find("```json") + 7
                json_end = research_result.find("```", json_start)
                if json_end != -1:
                    json_str = research_result[json_start:json_end].strip()
                    parsed_data = json.loads(json_str)
                else:
                    # Pokud není ukončovací ```, zkusíme celý zbytek
                    json_str = research_result[json_start:].strip()
                    parsed_data = json.loads(json_str)
            else:
                # Pokusíme se parsovat celou odpověď jako JSON
                parsed_data = json.loads(research_result)
            
            return {
                "research_data": parsed_data,
                "raw_response": research_result,
                "topic": topic,
                "research_status": "success",
                "assistant": "ResearchAssistant",
                "assistant_id": assistant_id,
                "model_used": params["model"],
                "timestamp": datetime.now().isoformat()
            }
            
        except json.JSONDecodeError:
            # Pokud nelze parsovat JSON, vrátíme raw text ve struktuře
            logger.warning("⚠️ Nelze parsovat JSON z OpenAI odpovědi")
            return {
                "research_data": {
                    "key_facts": [research_result[:500] + "..." if len(research_result) > 500 else research_result],
                    "competitive_analysis": "Detailní analýza vyžaduje další zpracování",
                    "target_audience": "Obecná audience zájemci o " + topic,
                    "content_angles": ["Základní přehled tématu", "Praktické tipy", "Aktuální trendy"],
                    "sources": ["OpenAI knowledge base"]
                },
                "raw_response": research_result,
                "topic": topic,
                "research_status": "partial",
                "assistant": "ResearchAssistant",
                "assistant_id": assistant_id,
                "model_used": params["model"],
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"❌ Chyba při volání OpenAI API: {e}")
        raise Exception(f"❌ ResearchAssistant selhal: {str(e)} - workflow nemůže pokračovat")



# Synchronní wrapper pro zpětnou kompatibilitu
def research_assistant_sync(topic: str, assistant_id: Optional[str] = None) -> Dict[str, Any]:
    """Synchronní verze pro testování"""
    import asyncio
    return asyncio.run(research_assistant(topic, assistant_id))

# Testovací funkce pro vývoj
if __name__ == "__main__":
    # Test příklady
    test_topics = [
        "AI nástroje pro content marketing",
        "udržitelná energie v ČR", 
        "e-commerce trendy 2025",
        "zdravá výživa pro sportovce"
    ]
    
    for topic in test_topics:
        print(f"\n--- Research Test: {topic} ---")
        result = research_assistant_sync(topic)
        print(json.dumps(result, indent=2, ensure_ascii=False))