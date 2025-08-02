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
    
    # Výchozí parametry
    default_params = {
        "model": "gpt-4o",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 2000,
        "system_prompt": "Jsi expert na humanizaci AI-generovaného obsahu. Tvým úkolem je udělat text přirozenější, čitelnější a více lidský, zachovat informační hodnotu a zlepšit flow textu."
    }
    
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
        # Inicializace OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ OpenAI API klíč není dostupný")
            raise Exception("HumanizerAssistant: OpenAI API klíč není dostupný")
            
        client = OpenAI(api_key=api_key)
        
        # Sestavení zpráv pro OpenAI
        messages = [
            {"role": "system", "content": default_params["system_prompt"]},
            {"role": "user", "content": humanization_prompt}
        ]
        
        # Volání OpenAI API
        logger.info(f"🤖 Volám OpenAI API s modelem {default_params['model']}")
        response = client.chat.completions.create(
            model=default_params["model"],
            messages=messages,
            temperature=default_params["temperature"],
            top_p=default_params["top_p"],
            max_tokens=default_params["max_tokens"]
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