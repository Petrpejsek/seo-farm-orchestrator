"""
PublishAssistant - Publishing krok v SEO pipeline
Připravuje content pro publikaci a zajišťuje finální formátování.
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

async def publish_assistant(input_data: Dict[str, Any], assistant_id: Optional[str] = None) -> str:
    """Připravuje content pro publikaci a zajišťuje finální formátování."""
    
    logger.info(f"🚀 PublishAssistant připravuje k publikaci: {len(str(input_data))} znaků")
    logger.info(f"🔍 PublishAssistant input_data keys: {list(input_data.keys()) if isinstance(input_data, dict) else 'Not a dict'}")
    
    # 🔧 OPRAVA: Inicializace OpenAI client
    from utils.api_keys import get_api_key
    
    api_key = get_api_key("openai")
    if not api_key:
        logger.error("❌ OpenAI API klíč není k dispozici pro PublishAssistant")
        return "Chyba: OpenAI API klíč není k dispozici"
        
    client = OpenAI(api_key=api_key)
    
    default_params = {
        "model": "gpt-4o",
        "temperature": 0.3,  # Nízká pro konzistentní formátování
        "top_p": 0.9,
        "max_tokens": 2000,
        "system_prompt": "Jsi specialist na finální přípravu obsahu k publikaci. Zajišťuješ správné formátování, strukturu a publikační metadata."
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
    
    # 🔧 OPRAVA: Správný parsing výstupů od asistentů 
    # Input_data obsahuje všechny výstupy z pipeline jako {assistant_name: {output: "...", metadata: {...}}}
    
    logger.info(f"🔍 DEBUG: input_data type: {type(input_data)}")
    logger.info(f"🔍 DEBUG: input_data sample: {str(input_data)[:500]}...")
    
    # Extrahuj výstupy od jednotlivých asistentů
    seo_output = ""
    humanized_content = ""
    qa_results = {}
    multimedia_data = ""
    
    if isinstance(input_data, dict):
        # Hledej výstupy od klíčových asistentů
        for assistant_name, assistant_data in input_data.items():
            if isinstance(assistant_data, dict) and "output" in assistant_data:
                output = assistant_data["output"]
                
                if "seo" in assistant_name.lower():
                    seo_output = output
                    logger.info(f"✅ Nalezen SEO output: {len(output)} znaků")
                elif "humanizer" in assistant_name.lower():
                    humanized_content = output
                    logger.info(f"✅ Nalezen Humanizer output: {len(output)} znaků")
                elif "qa" in assistant_name.lower():
                    # QA může být JSON string
                    try:
                        qa_results = json.loads(output) if isinstance(output, str) else output
                        logger.info(f"✅ Nalezen QA output: {len(str(qa_results))} znaků")
                    except:
                        qa_results = {"raw": output}
                elif "multimedia" in assistant_name.lower():
                    multimedia_data = output
                    logger.info(f"✅ Nalezen Multimedia output: {len(output)} znaků")
    
    # Priorita pro obsah: SEO > Humanized > největší dostupný obsah
    content = ""
    if seo_output and len(seo_output) > 100:
        content = seo_output
        logger.info("📄 Používám SEO optimalizovaný obsah")
    elif humanized_content and len(humanized_content) > 100:
        content = humanized_content  
        logger.info("📄 Používám humanizovaný obsah")
    else:
        # Fallback - hledej největší textový obsah
        logger.warning("⚠️ Hledám fallback obsah...")
        if isinstance(input_data, dict):
            for key, value in input_data.items():
                if isinstance(value, dict) and "output" in value:
                    output = value["output"]
                    if isinstance(output, str) and len(output) > len(content):
                        content = output
                        logger.info(f"📄 Fallback obsah z {key}: {len(content)} znaků")
    
    if not content:
        content = json.dumps(input_data, ensure_ascii=False)
    
    prompt = f"""
Připrav následující obsah k finální publikaci:

OBSAH:
{content}

QA VÝSLEDKY:
{json.dumps(qa_results, ensure_ascii=False) if qa_results else "Žádné QA výsledky"}

POŽADAVKY NA PUBLIKAČNÍ FORMÁT:
1. Zkontroluj a oprav všechny HTML tagy
2. Přidej chybějící meta tagy (description, keywords)
3. Optimalizuj strukturu nadpisů (H1, H2, H3)
4. Přidej Open Graph meta tagy pro social media
5. Zkontroluj responsive elementy
6. Přidej schema.org markup kde je vhodné
7. Finální kontrola před publikací

VÝSTUP:
Vrať pouze finální HTML obsah připravený k publikaci na web.
Obsah musí být kompletní, validní a optimalizovaný.
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
        
        published_content = response.choices[0].message.content.strip()
        logger.info(f"✅ Content připraven k publikaci: {len(published_content)} znaků")
        
        return published_content
        
    except Exception as e:
        logger.error(f"❌ Chyba při přípravě k publikaci: {e}")
        
        # Fallback - základní publikační formát
        return _fallback_publish_format(content, input_data)

def _fallback_publish_format(content: str, input_data: Dict[str, Any]) -> str:
    """Fallback formátování když OpenAI API není dostupné"""
    logger.info(f"🔄 Používám fallback publikační formát")
    
    # Základní HTML struktura
    if not content.startswith('<!DOCTYPE') and not content.startswith('<html'):
        formatted_content = f"""<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Kvalitní obsah připravený k publikaci">
    <title>Článek - {input_data.get('topic', 'Neznámé téma')}</title>
</head>
<body>
    <article>
        {content}
    </article>
    
    <footer>
        <p><em>Publikováno: {datetime.now().strftime('%d.%m.%Y')}</em></p>
        <p><em>Obsah byl připraven automaticky v fallback módu.</em></p>
    </footer>
</body>
</html>"""
    else:
        formatted_content = content
    
    return formatted_content

def publish_assistant_sync(input_data: Dict[str, Any], assistant_id: Optional[str] = None) -> str:
    import asyncio
    return asyncio.run(publish_assistant(input_data, assistant_id))