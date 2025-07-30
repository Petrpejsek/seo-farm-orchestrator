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

try:
    from api.database import get_prisma_client
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    print("⚠️ Database import failed - using fallback mode")

logger = logging.getLogger(__name__)

# Inicializace OpenAI klienta
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def draft_assistant(input_data: Dict[str, Any], assistant_id: Optional[str] = None) -> str:
    """
    Vytváří první draft článku na základě research dat a briefu.
    
    Args:
        input_data (Dict[str, Any]): Kombinace briefu a research dat
        assistant_id (str, optional): ID asistenta pro načtení parametrů z DB
        
    Returns:
        str: První draft článku v HTML nebo markdown formátu
    """
    
    logger.info(f"✍️ DraftAssistant vytváří draft z dat: {len(str(input_data))} znaků")
    
    # Výchozí parametry
    default_params = {
        "model": "gpt-4o",
        "temperature": 0.8,  # Vyšší pro kreativní psaní
        "top_p": 0.9,
        "max_tokens": 2000,
        "system_prompt": "Jsi expert copywriter a content creator. Tvým úkolem je vytvářet kvalitní, poutavé a SEO-optimalizované články na základě poskytnutých dat a briefu. Zaměř se na čitelnost, strukturu a hodnotu pro čtenáře."
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
    
    # Extrakce dat pro článek
    brief_data = input_data.get('brief', '')
    research_data = input_data.get('research_data', {})
    topic = input_data.get('topic', 'Nespecifikované téma')
    
    # Pokud brief je dict, extrahujeme ho
    if isinstance(brief_data, dict):
        brief_text = brief_data.get('brief', json.dumps(brief_data, ensure_ascii=False))
    else:
        brief_text = str(brief_data)
    
    # Pokud research_data jsou string, parsujeme je
    if isinstance(research_data, str):
        try:
            research_data = json.loads(research_data)
        except:
            research_data = {"content": research_data}
    
    # Sestavení informací pro draft
    research_summary = ""
    if isinstance(research_data, dict):
        if 'key_facts' in research_data:
            research_summary += f"Klíčová fakta: {', '.join(research_data['key_facts'][:5])}\n"
        if 'target_audience' in research_data:
            audience = research_data['target_audience']
            if isinstance(audience, dict):
                research_summary += f"Cílová skupina: {audience.get('primary', 'N/A')}\n"
            else:
                research_summary += f"Cílová skupina: {audience}\n"
        if 'content_angles' in research_data:
            angles = research_data['content_angles']
            if isinstance(angles, list):
                research_summary += f"Content angles: {', '.join(angles[:3])}\n"
    
    # Prompt pro tvorbu draftu
    draft_prompt = f"""
Vytvoř kvalitní článek na základě následujících informací:

TÉMA: {topic}

BRIEF/ZADÁNÍ:
{brief_text}

RESEARCH DATA:
{research_summary}

POŽADAVKY NA ČLÁNEK:
- Délka: 1500-2500 slov
- Struktura: Úvod, hlavní části s podnadpisy, závěr
- Styl: Profesionální, ale čitelný a poutavý
- SEO: Optimalizovaný pro vyhledávače
- Hodnota: Praktické informace a actionable insights

FORMÁT VÝSTUPU:
Použij HTML tagy pro strukturu:
- <h1> pro hlavní nadpis
- <h2> pro podnadpisy sekcí  
- <h3> pro podnadpisy podsekcí
- <p> pro odstavce
- <ul>/<li> pro seznamy
- <strong> pro zvýraznění klíčových bodů

Vytvoř kompletní článek, který je připravený k publikaci.
    """
    
    try:
        # Sestavení zpráv pro OpenAI
        messages = []
        if params["system_prompt"]:
            messages.append({"role": "system", "content": params["system_prompt"]})
        messages.append({"role": "user", "content": draft_prompt})
        
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
        
        return draft_content
            
    except Exception as e:
        logger.error(f"❌ Chyba při volání OpenAI API: {e}")
        
        # Fallback draft
        return _fallback_draft(topic, brief_text, research_summary)

def _fallback_draft(topic: str, brief: str, research: str) -> str:
    """Fallback draft když OpenAI API není dostupné"""
    logger.info(f"🔄 Používám fallback draft pro téma: {topic}")
    
    fallback_content = f"""
<h1>{topic}</h1>

<p>Tento článek se zabývá tématem <strong>{topic}</strong> a poskytuje přehled klíčových informací a poznatků.</p>

<h2>Úvod</h2>
<p>V dnešní době je téma {topic} velmi aktuální a důležité. Následující článek vám poskytne komplexní pohled na tuto problematiku.</p>

{f'<p><strong>Zadání:</strong> {brief}</p>' if brief else ''}

<h2>Hlavní body</h2>
<ul>
<li>Komplexní analýza tématu {topic}</li>
<li>Praktické tipy a doporučení</li>
<li>Aktuální trendy a novinky</li>
<li>Závěry a doporučení pro praxi</li>
</ul>

{f'<h2>Research poznatky</h2><p>{research}</p>' if research else ''}

<h2>Závěr</h2>
<p>Téma {topic} je složité a vyžaduje důkladnou analýzu. Doufáme, že tento článek vám poskytl užitečné informace a poznatky.</p>

<p><em>Poznámka: Tento článek byl vygenerován v fallback módu. Pro finální verzi doporučujeme ruční revizi a rozšíření obsahu.</em></p>
    """
    
    return fallback_content.strip()

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