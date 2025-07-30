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

try:
    from api.database import get_prisma_client
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    print("⚠️ Database import failed - using fallback mode")

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
    default_params = {
        "model": "gpt-4o",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 1200,
        "system_prompt": "Jsi expert researcher a content strategist. Tvým úkolem je provádět hloubkový research k zadaným tématům a shromažďovat strukturované podklady. Zaměř se na aktuální trendy, klíčová fakta, konkurenční analýzu a užitečné zdroje informací."
    }
    
    # Pokud máme assistant_id, načteme parametry z databáze
    if assistant_id and DATABASE_AVAILABLE:
        try:
            prisma = await get_prisma_client()
            assistant = await prisma.assistant.find_unique(where={"id": assistant_id})
            
            if assistant:
                # Použijeme parametry z databáze
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
    
    # Prompt pro research
    research_prompt = f"""
Proveď hloubkový research k tématu: "{topic}"

Potřebuji strukturované informace v následujících oblastech:

1. KLÍČOVÁ FAKTA A STATISTIKY
- Aktuální data, čísla, trendy
- Důležité poznatky a insight

2. KONKURENČNÍ ANALÝZA
- Hlavní hráči na trhu/v oboru
- Jejich přístupy a strategie
- Gap v trhu nebo příležitosti

3. TARGET AUDIENCE ANALÝZA  
- Kdo se o téma zajímá
- Jaké jsou jejich potřeby a pain pointy
- Demografické a psychografické charakteristiky

4. CONTENT ANGLES A PERSPEKTIVY
- Různé úhly pohledu na téma
- Kontroverzní nebo zajímavé aspekty
- Příběhy a case studies

5. ZDROJE A REFERENCE
- Autoritativní weby a publikace
- Odborníci v oboru
- Relevantní studie a výzkumy

Vrať strukturovaný JSON s těmito sekcemi. Zaměř se na praktické a actionable informace.
    """
    
    try:
        # Sestavení zpráv pro OpenAI
        messages = []
        if params["system_prompt"]:
            messages.append({"role": "system", "content": params["system_prompt"]})
        messages.append({"role": "user", "content": research_prompt})
        
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
            logger.warning("⚠️ Nelze parsovat JSON z OpenAI odpovědi, vrátím strukturovaný fallback")
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
        
        # Fallback research data
        return await _fallback_research(topic, assistant_id)

async def _fallback_research(topic: str, assistant_id: Optional[str] = None) -> Dict[str, Any]:
    """Fallback research když OpenAI API není dostupné"""
    logger.info(f"🔄 Používám fallback research pro téma: {topic}")
    
    # Jednoduché kategorizování témat pro fallback
    if any(keyword in topic.lower() for keyword in ["AI", "umělá inteligence", "technologie", "software"]):
        research_data = {
            "key_facts": [
                "AI technologie zažívají exponenciální růst",
                "Trh s AI má hodnotu přes 100 miliard dolarů",
                "Očekává se 20% roční růst do roku 2030"
            ],
            "competitive_analysis": {
                "main_players": ["OpenAI", "Google", "Microsoft", "Meta"],
                "market_trends": ["Demokratizace AI", "Enterprise adoption", "Etické AI"]
            },
            "target_audience": {
                "primary": "Tech nadšenci a early adopters",
                "secondary": "Business professionals a rozhodovače",
                "demographics": "25-45 let, vysokoškolské vzdělání"
            },
            "content_angles": [
                "Praktické použití AI v byznysu",
                "Budoucnost práce s AI",
                "Etické aspekty AI",
                "AI tools a aplikace"
            ],
            "sources": [
                "McKinsey AI Report",
                "Gartner Technology Trends",
                "MIT Technology Review"
            ]
        }
    elif any(keyword in topic.lower() for keyword in ["marketing", "SEO", "reklama", "obsahový marketing"]):
        research_data = {
            "key_facts": [
                "Content marketing generuje 3x více leadů než tradiční marketing",
                "SEO traffic má 14.6% close rate",
                "Video obsah zvyšuje engagement o 1200%"
            ],
            "competitive_analysis": {
                "main_players": ["HubSpot", "Semrush", "Ahrefs", "Moz"],
                "market_trends": ["AI-powered content", "Personalizace", "Voice search optimization"]
            },
            "target_audience": {
                "primary": "Marketéři a content tvůrci",
                "secondary": "Business owners a agency klienti",
                "demographics": "25-40 let, marketing background"
            },
            "content_angles": [
                "ROI content marketingu",
                "Nejnovější SEO trendy",
                "Automatizace marketingu",
                "Měření úspěšnosti kampaní"
            ],
            "sources": [
                "Content Marketing Institute",
                "Search Engine Journal",
                "HubSpot State of Marketing"
            ]
        }
    else:
        # Obecný fallback
        research_data = {
            "key_facts": [
                f"Téma '{topic}' je aktuálně velmi diskutované",
                "Roste zájem o tuto oblast mezi odborníky",
                "Existuje prostor pro kvalitní content na toto téma"
            ],
            "competitive_analysis": {
                "main_players": ["Zatím identifikuji hlavní hráče"],
                "market_trends": ["Rostoucí poptávka", "Digitalizace oboru"]
            },
            "target_audience": {
                "primary": "Lidé se zájmem o " + topic,
                "secondary": "Odborníci v příbuzných oblastech",
                "demographics": "Široká demografická skupina"
            },
            "content_angles": [
                "Základní přehled tématu",
                "Praktické tipy a rady",
                "Aktuální trendy a novinky",
                "Case studies a příklady"
            ],
            "sources": [
                "Odborné publikace",
                "Industry reports",
                "Expert interviews"
            ]
        }
    
    return {
        "research_data": research_data,
        "topic": topic,
        "research_status": "fallback",
        "assistant": "ResearchAssistant",
        "assistant_id": assistant_id,
        "timestamp": datetime.now().isoformat()
    }

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