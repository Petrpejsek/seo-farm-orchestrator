"""
HumanizerAssistant - Humanization krok v SEO pipeline
Humanizuje AI-generovaný content pro přirozenější čtení.
"""

import json
import logging
import os
from typing import Optional
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

async def humanizer_assistant(content: str, assistant_id: Optional[str] = None) -> str:
    """
    Humanizuje AI-generovaný content pro přirozenější čtení.
    
    Args:
        content (str): AI-generovaný obsah k humanizaci
        assistant_id (str, optional): ID asistenta pro načtení parametrů z DB
        
    Returns:
        str: Humanizovaný content
    """
    
    logger.info(f"👤 HumanizerAssistant humanizuje content: {len(content)} znaků")
    
    # Výchozí parametry
    default_params = {
        "model": "gpt-4o",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 2000,
        "system_prompt": "Jsi expert na humanizaci AI-generovaného obsahu. Tvým úkolem je udělat text přirozenější, čitelnější a více lidský, zachovat informační hodnotu a zlepšit flow textu."
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
    
    # Prompt pro humanizaci
    humanization_prompt = f"""
Humanizuj následující AI-generovaný obsah. Udělej ho přirozenější, čitelnější a více lidský:

{content}

POŽADAVKY:
- Zachovej všechny důležité informace a fakta
- Zlepši flow a čitelnost textu
- Přidej přirozené přechody mezi odstavci
- Použij variantnější slovník a formulace
- Odstraň příliš formální nebo robotický jazyk
- Zachovej HTML strukturu a tagy
- Přidej více osobnosti a tónu hlasu
- Udělej text poutavější pro čtenáře

Vrať pouze upravený text bez dodatečných komentářů.
    """
    
    try:
        # Sestavení zpráv pro OpenAI
        messages = []
        if params["system_prompt"]:
            messages.append({"role": "system", "content": params["system_prompt"]})
        messages.append({"role": "user", "content": humanization_prompt})
        
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
        
        return humanized_content
            
    except Exception as e:
        logger.error(f"❌ Chyba při volání OpenAI API: {e}")
        
        # Fallback - vrátíme původní content s mírnými úpravami
        return _fallback_humanization(content)

def _fallback_humanization(content: str) -> str:
    """Fallback humanizace když OpenAI API není dostupné"""
    logger.info(f"🔄 Používám fallback humanizaci")
    
    # Jednoduché úpravy pro humanizaci
    humanized = content
    
    # Nahrazení některých formálních frází
    replacements = {
        "V tomto článku": "Dnes se podíváme na",
        "Je důležité poznamenat": "Stojí za zmínku",
        "Na závěr lze říci": "Zkrátka a dobře",
        "Následující faktory": "Tyto věci",
        "Je nutné zdůraznit": "Důležité je",
        "V současné době": "Dnes",
        "Z výše uvedeného vyplývá": "Vidíme tedy"
    }
    
    for formal, casual in replacements.items():
        humanized = humanized.replace(formal, casual)
    
    # Přidání poznámky o fallback módu
    if "<p>" in humanized:
        humanized += "\n\n<p><em>Poznámka: Obsah byl upraven v základním módu. Pro plnou humanizaci doporučujeme ruční revizi.</em></p>"
    
    return humanized

# Synchronní wrapper pro zpětnou kompatibilitu
def humanizer_assistant_sync(content: str, assistant_id: Optional[str] = None) -> str:
    """Synchronní verze pro testování"""
    import asyncio
    return asyncio.run(humanizer_assistant(content, assistant_id))

# Testovací funkce pro vývoj
if __name__ == "__main__":
    test_content = """
<h1>AI nástroje pro content marketing</h1>

<p>V tomto článku se zaměříme na AI nástroje pro content marketing. Je důležité poznamenat, že tyto technologie zažívají exponenciální růst.</p>

<h2>Hlavní výhody AI nástrojů</h2>
<p>Následující faktory jsou klíčové pro úspěch AI nástrojů v marketingu.</p>
    """
    
    print("\n--- Humanization Test ---")
    result = humanizer_assistant_sync(test_content)
    print(f"Humanizovaný content ({len(result)} znaků):")
    print(result)