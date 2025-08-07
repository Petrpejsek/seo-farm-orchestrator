"""
PublishAssistant - Finální kompilace článku do JSON formátu pro landing page
"""

import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from llm_factory import LLMClient

logger = logging.getLogger(__name__)

async def publish_assistant(input_data: Dict[str, Any], assistant_id: Optional[str] = None) -> str:
    """
    Zkompiluje všechny výstupy z pipeline do finálního JSON formátu pro landing page.
    
    STRIKTNÍ POŽADAVKY:
    - ŽÁDNÉ fallback mechanismy
    - Přesný JSON formát pro landing pages
    - Extrakce dat ze všech 8 asistentů
    - Validace povinných komponent
    
    Args:
        input_data: Obsahuje topic a previous_outputs ze všech asistentů
        assistant_id: ID asistenta (optional)
    
    Returns:
        JSON string s finálním článkem
    """
    logger.info("🚀 PublishAssistant: Kompilace finálního článku")
    
    try:
        # Extrakce základních dat
        topic = input_data.get("topic", "")
        previous_outputs = input_data.get("previous_outputs", {})
        
        logger.info(f"📥 Previous outputs klíče: {list(previous_outputs.keys())}")
        
        # === EXTRAKCE DAT ZE VŠECH 8 ASISTENTŮ ===
        
        # 1. BRIEF DATA
        brief_data = previous_outputs.get("brief_assistant_output", "")
        logger.info(f"📋 Brief data: {len(str(brief_data))} znaků")
        
        # 2. RESEARCH DATA  
        research_data = previous_outputs.get("research_assistant_output", "")
        logger.info(f"🔍 Research data: {len(str(research_data))} znaků")
        
        # 3. DRAFT/HUMANIZER HTML CONTENT (priorita Humanizer)
        html_content = ""
        if "humanizer_assistant_output" in previous_outputs:
            html_content = previous_outputs["humanizer_assistant_output"]
            logger.info("📝 Používám HTML z HumanizerAssistant")
        elif "draft_assistant_output" in previous_outputs:
            html_content = previous_outputs["draft_assistant_output"]
            logger.info("📝 Používám HTML z DraftAssistant")
        
        # 4. SEO METADATA
        seo_metadata = previous_outputs.get("seo_assistant_output", "")
        logger.info(f"🎯 SEO metadata: {len(str(seo_metadata))} znaků")
        
        # 5. FACT VALIDATION
        validated_facts = previous_outputs.get("fact_validator_assistant_output", "")
        logger.info(f"✅ Validated facts: {len(str(validated_facts))} znaků")
        
        # 6. QA DATA
        qa_data = previous_outputs.get("qa_assistant_output", "")
        logger.info(f"🔍 QA data: {len(str(qa_data))} znaků")
        
        # 7. MULTIMEDIA DATA
        multimedia_data = previous_outputs.get("multimedia_assistant_output", "")
        logger.info(f"🎨 Multimedia data: {len(str(multimedia_data))} znaků")
        
        # 8. GENERATED IMAGES
        generated_images = previous_outputs.get("image_renderer_assistant_output", "")
        logger.info(f"🖼️ Generated images: {len(str(generated_images))} znaků")
        
        # STRICT VALIDATION - ŽÁDNÉ FALLBACKY!
        if not html_content:
            raise Exception("❌ PublishAssistant: Chybí HTML content z DraftAssistant nebo HumanizerAssistant")
        if not seo_metadata:
            raise Exception("❌ PublishAssistant: Chybí SEO metadata z SEOAssistant")
        
        logger.info("✅ Všechny povinné komponenty nalezeny")
        
        # === LLM CLIENT SETUP ===
        from config import get_llm_config
        llm_config = get_llm_config()
        
        client = OpenAI(api_key=llm_config["openai"]["api_key"])
        
        # PŘESNÝ FORMÁT JSON PRO LANDING PAGE
        prompt = f"""Vytvoř JSON pro landing page v PŘESNĚ tomto formátu z poskytnutých dat:

📥 VSTUPNÍ DATA:
HTML CONTENT: {html_content}
SEO METADATA: {seo_metadata}
QA DATA: {qa_data if qa_data else "Nedostupné"}
GENERATED IMAGES: {generated_images if generated_images else "Nedostupné"}

🎯 POŽADOVANÝ VÝSTUP - PŘESNĚ TENTO FORMÁT:
{{
  "title": "Název stránky z SEO metadata",
  "slug": "url-slug-bez-diakritiky-z-seo",
  "language": "cs",
  "meta": {{
    "description": "SEO popis z metadata",
    "keywords": ["klíčové", "slovo1", "slovo2"]
  }},
  "content_html": "HTML obsah PŘESNĚ jak je poskytnut",
  "visuals": [
    {{
      "url": "https://url-obrazku.jpg",
      "alt_text": "Popis obrázku", 
      "description": "Detailní popis"
    }}
  ],
  "faq": [
    {{
      "question": "Otázka?",
      "answer": "Odpověď na otázku"
    }}
  ],
  "facts_and_sources": [
    {{
      "fact": "Ověřený fakt",
      "source": "Zdroj nebo URL"
    }}
  ],
  "original_brief": {{
    "topic": "{topic}",
    "research_summary": "Shrnutí research dat",
    "creation_date": "2025-08-03"
  }},
  "schema_org": {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "Nadpis článku"
  }},
  "format": "html"
}}

📋 INSTRUKCE:
✅ Extrahuj title, slug, description, keywords z SEO metadata
✅ Vlož content_html PŘESNĚ bez úprav
✅ Vytvoř visuals array z generated_images (pokud jsou dostupné)
✅ Vytvoř FAQ z QA dat (pokud jsou dostupná)
✅ keywords MUSÍ být array stringů
✅ Vytvoř facts_and_sources z validated facts
✅ Základní schema_org s Article type

❌ NESMÍ OBSAHOVAT:
- Žádný text před/po JSON
- Žádné markdown formátování
- Žádné komentáře
- Žádné pipeline wrappery

OUTPUT: Pouze validní JSON objekt!"""
    
    try:
        response = client.chat.completions.create(
                model="gpt-4o",
            messages=[
                    {"role": "system", "content": "Jsi JSON export asistent pro landing pages. Vytvoříš POUZE čistý JSON objekt bez jakéhokoli dalšího textu. Používej vstupní data přesně jak jsou poskytnutá. Neformátuj markdown, nevytvářej komentáře."},
                {"role": "user", "content": prompt}
            ],
                temperature=0.2,
                top_p=0.8,
                max_tokens=8000
        )
        
        published_content = response.choices[0].message.content.strip()
            
            # Validace že je to validní JSON
            try:
                json.loads(published_content)
                logger.info(f"✅ Finální článek JSON připraven: {len(published_content)} znaků")
            except json.JSONDecodeError as e:
                logger.error(f"❌ LLM nevrátil validní JSON: {e}")
                raise Exception(f"❌ PublishAssistant: LLM nevrátil validní JSON: {e}")
        
        return published_content
        
    except Exception as e:
            logger.error(f"❌ PublishAssistant LLM volání selhalo: {e}")
            raise Exception(f"❌ PublishAssistant failed při kompilaci: {e}")
        
    except Exception as e:
        logger.error(f"❌ PublishAssistant celkové selhání: {e}")
        raise Exception(f"❌ PublishAssistant failed: {e}")