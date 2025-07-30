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
    
    # Extrakce obsahu z input_data
    content = ""
    qa_results = {}
    seo_content = ""
    
    if isinstance(input_data, dict):
        # Priorita: finální optimalizovaný content
        if 'seo_optimized_content' in input_data:
            content = input_data['seo_optimized_content']
        elif 'humanized_content' in input_data:
            content = input_data['humanized_content']
        elif 'draft_content' in input_data:
            content = input_data['draft_content']
        elif 'content' in input_data:
            content = input_data['content']
        else:
            # Pokusíme se najít největší string hodnotu
            for key, value in input_data.items():
                if isinstance(value, str) and len(value) > len(content):
                    content = value
        
        # QA výsledky pro finální kontrolu
        qa_results = input_data.get('qa_results', {})
    
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