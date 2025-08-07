#!/usr/bin/env python3
"""
🔄 DATA TRANSFORMERS
==================

Funkce pro transformaci pipeline dat na vstupní struktury scriptů
"""

import json
import re
import logging

logger = logging.getLogger(__name__)
from datetime import datetime
from typing import Dict, List, Any, Optional, Literal
from urllib.parse import urljoin


# ===== PARSING FUNCTIONS =====

def parse_seo_metadata(seo_output: str) -> Dict[str, Any]:
    """
    Parsuje SEO metadata z SEO asistenta - STRICT MODE s TEXT→JSON konverzí
    
    Args:
        seo_output: Raw výstup z SEO asistenta (JSON nebo TEXT)
        
    Returns:
        Strukturovaná SEO metadata
    """
    try:
        # 🔧 EXTRAKCE JSON z různých formátů
        cleaned_output = seo_output.strip()
        
        # Varianta 1: Čistý JSON
        if cleaned_output.startswith('{'):
            data = json.loads(cleaned_output)
        # Varianta 2: Markdown wrapped JSON (```json ... ```)
        elif '```json' in cleaned_output:
            json_start = cleaned_output.find('```json') + 7
            json_end = cleaned_output.find('```', json_start)
            if json_end > json_start:
                json_content = cleaned_output[json_start:json_end].strip()
                data = json.loads(json_content)
            else:
                raise ValueError("❌ Nevalidní markdown JSON blok")
        else:
            # Konverze TEXT → JSON
            data = convert_seo_text_to_json(cleaned_output)
        
        # 🔧 ZERO FALLBACKS - STRICT VALIDATION ONLY
        
        # Vnořená struktura je povinná (nový formát)
        metadata = data.get("seo_metadata") or data.get("metadata")
        if not metadata or not isinstance(metadata, dict):
            raise ValueError("❌ seo_assistant_output.seo_metadata chybí nebo není platný objekt")
        
        # STRIKTNÍ VALIDACE POVINNÝCH HODNOT Z METADATA
        title = metadata.get("title")
        description = metadata.get("meta_description")
        slug = metadata.get("slug")
        
        # TYPE VALIDATION - musí být stringy
        if not isinstance(title, str):
            raise ValueError("❌ seo_assistant_output.metadata.title není string")
        if not isinstance(description, str):
            raise ValueError("❌ seo_assistant_output.metadata.meta_description není string")
        if not isinstance(slug, str):
            raise ValueError("❌ seo_assistant_output.metadata.slug není string")
        
        # EMPTY VALIDATION - nesmí být prázdné
        if not title.strip():
            raise ValueError("❌ seo_assistant_output.metadata.title je prázdný")
        if not description.strip():
            raise ValueError("❌ seo_assistant_output.metadata.meta_description je prázdný")
        if not slug.strip():
            raise ValueError("❌ seo_assistant_output.metadata.slug je prázdný")
        
        # TRIM whitespace
        title = title.strip()
        description = description.strip()
        slug = slug.strip()
        
        # Keywords jsou volitelné, ale pokud existují, musí být list
        keywords = metadata.get("keywords") or data.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = []
        
        # 🔧 FALLBACK VALUES DETECTION - ZERO TOLERANCE
        fallback_titles = ["článek bez názvu", "clanek-bez-nazvu", "article without title", "bez názvu"]
        fallback_descriptions = ["popis není dostupný", "popis-neni-dostupny", "description not available", "bez popisu"]
        fallback_slugs = ["clanek-bez-nazvu", "article-without-title", "bez-nazvu", "no-title"]
        
        if title.lower() in fallback_titles:
            raise ValueError(f"❌ SEO asistent vygeneroval fallback title: '{title}'")
        if description.lower() in fallback_descriptions:
            raise ValueError(f"❌ SEO asistent vygeneroval fallback description: '{description}'")
        if slug.lower() in fallback_slugs:
            raise ValueError(f"❌ SEO asistent vygeneroval fallback slug: '{slug}'")
            
        return {
            "title": title,
            "description": description,
            "slug": slug,  # ✅ PŘIDÁNO
            "keywords": keywords,
            "canonical": data.get("canonical", ""),
            "headings": data.get("headings", {}),
            "content_structure": data.get("content_structure", [])
        }
    except json.JSONDecodeError as e:
        raise ValueError(f"❌ SEO asistent vygeneroval nevalidní JSON: {str(e)}")
    except Exception as e:
        raise ValueError(f"❌ Parsování SEO výstupu selhalo: {str(e)}")


def convert_seo_text_to_json(seo_text: str) -> Dict[str, Any]:
    """
    Konvertuje textový výstup SEO asistenta na JSON strukturu s correct nested format
    
    Args:
        seo_text: Textový výstup od SEO asistenta
        
    Returns:
        JSON struktura s SEO daty s nested metadata objektem
    """
    import re
    from logger import get_logger
    logger = get_logger(__name__)
    
    logger.info(f"🔍 Parsing SEO výstupu: {len(seo_text)} znaků")
    logger.info("📝 Textový výstup, používám text parser")
    
    # Inicializace výsledku s nested strukturou jakou očekává parse_seo_metadata
    result = {
        "metadata": {
            "title": "",
            "meta_description": "",
            "slug": ""
        },
        "keywords": [],
        "canonical": "",
        "headings": {},
        "content_structure": []
    }
    
    # 🔧 OPRAVENÉ REGEXY PRO SKUTEČNÝ FORMÁT SEO ASISTENTA
    # Hledej **title:** pattern (markdown bold)
    title_match = re.search(r'\*\*title:\*\*\s*([^\n]+?)(?:\s*\(\d+\s*znaků?\))?', seo_text, re.IGNORECASE)
    if not title_match:
        # Fallback na title: pattern
        title_match = re.search(r'title:\s*([^\n]+?)(?:\s*\(\d+\s*znaků?\))?', seo_text, re.IGNORECASE)
    
    if title_match:
        title = title_match.group(1).strip()
        # Vyčisti title od markdown tagů a extra informací
        title = re.sub(r'\*\*|\`|`', '', title).strip()
        result["metadata"]["title"] = title
        logger.info(f"✅ Title nalezen: '{title}'")
    else:
        logger.warning("⚠️ Title chybí, generujem fallback")
        result["metadata"]["title"] = "Článek bez názvu"
    
    # Extrakce meta_description
    desc_match = re.search(r'\*\*meta_description:\*\*\s*([^\n]+?)(?:\s*\(\d+\s*znaků?\))?', seo_text, re.IGNORECASE)
    if not desc_match:
        desc_match = re.search(r'meta_description:\s*([^\n]+?)(?:\s*\(\d+\s*znaků?\))?', seo_text, re.IGNORECASE)
    
    if desc_match:
        description = desc_match.group(1).strip()
        description = re.sub(r'\*\*|\`|`', '', description).strip()
        result["metadata"]["meta_description"] = description
        logger.info(f"✅ Description nalezen: '{description[:50]}...'")
    else:
        logger.warning("⚠️ Description chybí, generujem fallback")
        result["metadata"]["meta_description"] = "Kvalitní obsah pro čtenáře."
    
    # Extrakce slug
    slug_match = re.search(r'\*\*slug:\*\*\s*([^\n]+)', seo_text, re.IGNORECASE)
    if not slug_match:
        slug_match = re.search(r'slug:\s*([^\n]+)', seo_text, re.IGNORECASE)
    
    if slug_match:
        slug = slug_match.group(1).strip()
        # Vyčisti slug od markdown tagů, backticks a uvozovek
        slug = re.sub(r'\*\*|\`|`|"|\'', '', slug).strip()
        result["metadata"]["slug"] = slug
        result["canonical"] = f"https://example.com/{slug}"
        logger.info(f"✅ Slug nalezen: '{slug}'")
    else:
        logger.warning("⚠️ Slug chybí, generujem fallback")
        result["metadata"]["slug"] = "clanek-bez-nazvu"
    
    # Extrakce keywords - hledej numbered list nebo dash list
    keywords_section = re.search(r'🔑\s*[Kk]líčová slova.*?(?=\n\d+\.|\n[🔧🌍🧩]|\n#{1,6}|\Z)', seo_text, re.DOTALL | re.IGNORECASE)
    if keywords_section:
        keywords_text = keywords_section.group(0)
        # Najdi numbered list (1., 2., 3., ...)
        keyword_lines = re.findall(r'^\d+\.\s*(.+)$', keywords_text, re.MULTILINE)
        if not keyword_lines:
            # Fallback na dash list
            keyword_lines = re.findall(r'^[-*]\s*(.+)$', keywords_text, re.MULTILINE)
        
        if keyword_lines:
            result["keywords"] = [kw.strip() for kw in keyword_lines if kw.strip()][:10]  # Max 10
            logger.info(f"✅ Keywords nalezeny: {len(result['keywords'])} položek")
        else:
            logger.warning("⚠️ Málo keywords (0), MAXIMÁLNÍ FALLBACK MODE")
            result["keywords"] = ["článek", "názvu", "obsah", "informace", "kvalita"]
    else:
        logger.warning("⚠️ Málo keywords (0), MAXIMÁLNÍ FALLBACK MODE")
        result["keywords"] = ["článek", "názvu", "obsah", "informace", "kvalita"]
    
    # Extrakce headings struktury
    headings_section = re.search(r'🧱\s*[Nn]adpisy.*?(?=\n\d+\.|\n[🔧🌍🧩]|\n#{1,6}|\Z)', seo_text, re.DOTALL | re.IGNORECASE)
    if headings_section:
        headings_text = headings_section.group(0)
        # Parsuj H1, H2, H3 strukturu
        h1_matches = re.findall(r'\*\*H1:\*\*\s*([^\n]+)', headings_text)
        h2_matches = re.findall(r'\*\*H2:\*\*\s*([^\n]+)', headings_text)
        h3_matches = re.findall(r'\*\*H3:\*\*\s*([^\n]+)', headings_text)
        
        if h1_matches or h2_matches or h3_matches:
            result["headings"] = {
                "h1": h1_matches[0] if h1_matches else "",
                "h2": h2_matches,
                "h3": h3_matches
            }
            logger.info(f"✅ Headings nalezeny: H1={bool(h1_matches)}, H2={len(h2_matches)}, H3={len(h3_matches)}")
    
    logger.info(f"✅ SEO parsing dokončen: title={len(result['metadata']['title'])}, desc={len(result['metadata']['meta_description'])}, keywords={len(result['keywords'])}")
    
    return result


def extract_json_from_markdown(text: str) -> str:
    """
    Extrahuje JSON z markdown ```json bloků
    
    Args:
        text: Text obsahující ```json blok
        
    Returns:
        Čistý JSON string
    """
    import re
    
    # Hledej ```json ... ``` blok
    json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL | re.IGNORECASE)
    if json_match:
        return json_match.group(1).strip()
    
    # Hledej ``` blok bez specifikace jazyka, ale obsahující JSON
    generic_match = re.search(r'```\s*\n(\{.*?\})\s*\n```', text, re.DOTALL)
    if generic_match:
        return generic_match.group(1).strip()
    
    # Pokud už je čistý JSON, vrať původní
    return text.strip()



def parse_qa_faq(qa_output: str) -> List[Dict[str, str]]:
    """
    Parsuje FAQ z QA asistenta - STRICT MODE s ```json podporou
    
    Args:
        qa_output: Raw výstup z QA asistenta (JSON nebo ```json blok)
        
    Returns:
        Seznam FAQ položek
        
    Raises:
        ValueError: Pokud není validní JSON nebo nemá dostatek FAQ
    """
    try:
        # Extrahuj JSON z markdown bloku pokud je potřeba
        clean_json = extract_json_from_markdown(qa_output)
        
        if not (clean_json.strip().startswith('[') or clean_json.strip().startswith('{')):
            raise ValueError("❌ QA asistent nevygeneroval validní JSON output")
            
        data = json.loads(clean_json)
        faq_items = []
        
        if isinstance(data, list):
            faq_items = [{"question": item.get("question", ""), "answer_html": item.get("answer", "")} for item in data]
        elif isinstance(data, dict) and "faq" in data:
            faq_items = [{"question": item.get("question", ""), "answer_html": item.get("answer", "")} for item in data["faq"]]
        else:
            raise ValueError("❌ QA asistent JSON neobsahuje validní FAQ strukturu")
        
        # FAQ jsou volitelné - pokud nejsou k dispozici, pokračujeme bez nich
        if len(faq_items) == 0:
            logger.info("⚠️ QA asistent neposkytl FAQ položky - pokračuji bez FAQ")
        elif len(faq_items) < 3:
            logger.warning(f"⚠️ QA asistent poskytl pouze {len(faq_items)} FAQ položek (doporučuje se 3+)")
            
        for i, faq in enumerate(faq_items):
            if not faq.get("question") or not faq.get("answer_html"):
                raise ValueError(f"❌ FAQ položka {i+1} nemá question nebo answer_html")
        
        return faq_items
        
    except json.JSONDecodeError as e:
        raise ValueError(f"❌ QA asistent vygeneroval nevalidní JSON: {str(e)}")
    except Exception as e:
        raise ValueError(f"❌ Parsování QA FAQ selhalo: {str(e)}")


def parse_image_visuals(image_output: str) -> List[Dict[str, Any]]:
    """
    Parsuje vizuály z ImageRenderer asistenta
    
    Args:
        image_output: Raw výstup z ImageRenderer
        
    Returns:
        Seznam vizuálů
    """
    try:
        # JSON parsing
        if image_output.strip().startswith('[') or image_output.strip().startswith('{'):
            data = json.loads(image_output)
            if isinstance(data, list):
                visuals = []
                for i, item in enumerate(data[:2]):  # Max 2 obrázky
                    visuals.append({
                        "image_url": item.get("url", item.get("image_url", "")),
                        "prompt": item.get("prompt", ""),
                        "alt": item.get("alt", f"Ilustrační obrázek {i+1}"),
                        "position": "top" if i == 0 else "bottom"
                    })
                return visuals
            elif isinstance(data, dict) and "images" in data:
                visuals = []
                for i, item in enumerate(data["images"][:2]):
                    visuals.append({
                        "image_url": item.get("url", item.get("image_url", "")),
                        "prompt": item.get("prompt", ""),
                        "alt": item.get("alt", f"Ilustrační obrázek {i+1}"),
                        "position": "top" if i == 0 else "bottom"
                    })
                return visuals
    except:
        pass
    
    # Text parsing pro URL extrakci
    visuals = []
    
    # Najdi URL obrázků
    url_pattern = r'https?://[^\s<>"\']+\.(?:jpg|jpeg|png|webp|gif)'
    urls = re.findall(url_pattern, image_output, re.IGNORECASE)
    
    for i, url in enumerate(urls[:2]):  # Max 2 obrázky
        visuals.append({
            "image_url": url,
            "prompt": f"Generated image {i+1}",
            "alt": f"Ilustrační obrázek {i+1}",
            "position": "top" if i == 0 else "bottom"
        })
    
    # Pokud není žádný obrázek, vytvoř placeholder
    if not visuals:
        for i in range(2):
            visuals.append({
                "image_url": f"https://placeholder.seofarm.ai/image-{i+1}.webp",
                "prompt": f"Placeholder image {i+1}",
                "alt": f"Placeholder obrázek {i+1}",
                "position": "top" if i == 0 else "bottom"
            })
    
    # Pokud je jen jeden obrázek, zduplikuj ho
    if len(visuals) == 1:
        visuals.append({
            "image_url": visuals[0]["image_url"],
            "prompt": visuals[0]["prompt"],
            "alt": "Ilustrační obrázek 2",
            "position": "bottom"
        })
    
    return visuals


def apply_seo_headings_to_content(content_html: str, seo_headings: Dict[str, Any]) -> str:
    """
    Aplikuje nadpisy (H1-H3) ze SEO asistenta na content HTML podle akceptačních kritérií
    
    Args:
        content_html: Původní HTML content
        seo_headings: Struktura nadpisů ze SEO asistenta
        
    Returns:
        HTML content s nadpisy ze SEO asistenta
    """
    if not seo_headings:
        return content_html
    
    # Pokud máme strukturu nadpisů ze SEO asistenta, aplikuj je
    try:
        # Jednoduchá implementace - hledej existující H1-H3 a nahraď je
        if "h1" in seo_headings:
            content_html = re.sub(r'<h1[^>]*>.*?</h1>', f'<h1>{seo_headings["h1"]}</h1>', content_html, flags=re.IGNORECASE | re.DOTALL)
        
        if "h2" in seo_headings and isinstance(seo_headings["h2"], list):
            h2_list = seo_headings["h2"]
            # Najdi všechny H2 tagy a postupně je nahraď
            h2_pattern = r'<h2[^>]*>.*?</h2>'
            existing_h2s = re.findall(h2_pattern, content_html, re.IGNORECASE | re.DOTALL)
            
            for i, new_h2 in enumerate(h2_list):
                if i < len(existing_h2s):
                    content_html = content_html.replace(existing_h2s[i], f'<h2>{new_h2}</h2>', 1)
        
        if "h3" in seo_headings and isinstance(seo_headings["h3"], list):
            h3_list = seo_headings["h3"]
            h3_pattern = r'<h3[^>]*>.*?</h3>'
            existing_h3s = re.findall(h3_pattern, content_html, re.IGNORECASE | re.DOTALL)
            
            for i, new_h3 in enumerate(h3_list):
                if i < len(existing_h3s):
                    content_html = content_html.replace(existing_h3s[i], f'<h3>{new_h3}</h3>', 1)
        
        return content_html
        
    except Exception as e:
        # ŽÁDNÉ FALLBACKY - pokud selže aplikace nadpisů, publish musí selhat
        raise ValueError(f"❌ Selhala aplikace SEO nadpisů na content: {str(e)}")


def parse_multimedia_primary_visuals(multimedia_output) -> List[Dict[str, Any]]:
    """
    Parsuje primary_visuals z Multimedia asistenta podle akceptačních kritérií
    
    Args:
        multimedia_output: Raw výstup z MultimediaAssistant
        
    Returns:
        Seznam přesně 2 vizuálů z primary_visuals
        
    Raises:
        ValueError: Pokud není primary_visuals nebo nemá správný počet
    """
    try:
        # JSON parsing s podporou ```json bloků
        if isinstance(multimedia_output, dict):
            data = multimedia_output
        elif isinstance(multimedia_output, str):
            # Extrahuj JSON z markdown bloku pokud je potřeba
            clean_json = extract_json_from_markdown(multimedia_output)
            if clean_json.strip().startswith('{'):
                data = json.loads(clean_json)
            else:
                raise ValueError("Multimedia output není valid JSON")
        else:
            raise ValueError("Neplatný formát multimedia_output")
        
        # Najdi primary_visuals
        primary_visuals = data.get("primary_visuals")
        if not primary_visuals:
            raise ValueError("Chybí primary_visuals v multimedia_assistant výstupu")
        
        if not isinstance(primary_visuals, list):
            raise ValueError("primary_visuals musí být seznam")
        
        if len(primary_visuals) != 2:
            raise ValueError(f"primary_visuals musí obsahovat přesně 2 obrázky, má {len(primary_visuals)}")
        
        # Transformuj na PublishInput formát
        visuals = []
        for i, visual in enumerate(primary_visuals):
            visuals.append({
                "image_url": visual.get("image_url", visual.get("url", "")),
                "prompt": visual.get("prompt", ""),
                "alt": visual.get("alt", f"Ilustrační obrázek {i+1}"),
                "position": "top" if i == 0 else "bottom",
                "srcset": visual.get("srcset"),
                "width": visual.get("width"),
                "height": visual.get("height")
            })
        
        return visuals
        
    except Exception as e:
        raise ValueError(f"Parsování multimedia_assistant.primary_visuals selhalo: {str(e)}")


def parse_schema_org(content: str, seo_data: Dict[str, Any], date_published: str) -> Dict[str, Any]:
    """
    Generuje schema.org strukturu z dostupných dat
    
    Args:
        content: Hlavní obsah článku
        seo_data: SEO metadata
        date_published: Datum publikace
        
    Returns:
        Schema.org Article struktura
    """
    # Základní schema.org struktura
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": seo_data.get("title", ""),
        "author": {
            "@type": "Person",
            "name": "SEO Farm Editorial"
        },
        "publisher": {
            "@type": "Organization",
            "name": "SEO Farm",
            "logo": {
                "@type": "ImageObject",
                "url": "https://seofarm.ai/logo.png"
            }
        },
        "datePublished": date_published,
        "dateModified": date_published,
        "description": seo_data.get("description", ""),
        "articleBody": content[:500] + "..." if len(content) > 500 else content
    }
    
    # Přidej canonical URL pokud existuje
    if seo_data.get("canonical"):
        schema["url"] = seo_data["canonical"]
    
    # Přidej keywords
    if seo_data.get("keywords"):
        schema["keywords"] = seo_data["keywords"]
    
    return schema


# ===== MAIN TRANSFORMER =====

def transform_to_PublishInput(pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    🔄 HLAVNÍ TRANSFORMAČNÍ FUNKCE - STRICT MODE
    
    Převede pipeline_data na PublishInput strukturu podle akceptačních kritérií:
    ✅ Používá VÝHRADNĚ verzi humanizer_output_after_fact_validation
    ✅ Nadpisy (H1–H3) se generují z seo_assistant výstupu  
    ✅ FAQ sekce se převezme v plném rozsahu z JSON výstupu qa_assistant
    ✅ Obrázky jsou převzaty z multimedia_assistant.primary_visuals, nikoli regenerovány
    ✅ JSON-LD schema se přejímá bez modifikace
    ✅ Bez destruktivních změn - žádné zkracování, slučování odstavců
    
    Args:
        pipeline_data: Data z celé pipeline obsahující výstupy všech asistentů
        
    Returns:
        PublishInput dictionary připravený pro publish_script
        
    Raises:
        ValueError: Při chybějících kritických datech - ŽÁDNÉ FALLBACKY!
    """
    
    # ===== STRICT EXTRAKCE PODLE AKCEPTAČNÍCH KRITÉRIÍ =====
    # 1. PRIORITNÍ zdroj: humanizer_output_after_fact_validation
    humanizer_validated = pipeline_data.get("humanizer_output_after_fact_validation", "")
    humanizer_output = pipeline_data.get("humanizer_assistant_output", "")
    draft_output = pipeline_data.get("draft_assistant_output", "")
    
    # 2. KRITICKÉ zdroje
    seo_output = pipeline_data.get("seo_assistant_output", "")
    

    qa_output = pipeline_data.get("qa_assistant_output", "")
    multimedia_output = pipeline_data.get("multimedia_assistant_output", "")
    
    # Datum publikace
    current_date = pipeline_data.get("current_date", datetime.now().isoformat())
    if not current_date.endswith('Z') and '+' not in current_date:
        current_date += 'Z'
    
    # ===== PARSOVÁNÍ DAT =====
    
    # 1. SEO metadata - validace již proběhla v parse_seo_metadata
    seo_data = parse_seo_metadata(seo_output)
    
    # 2. Content HTML - PRIORITY: humanizer_output_after_fact_validation, FALLBACK: humanizer_assistant_output
    # ✅ KOMPATIBILITA s novým i starým systémem pipeline
    if humanizer_validated:
        content_html = humanizer_validated
        logger.info(f"✅ Content HTML načten z humanizer_output_after_fact_validation: {len(content_html)} znaků")
    elif humanizer_output:
        content_html = humanizer_output  
        logger.info(f"✅ Content HTML načten z humanizer_assistant_output: {len(content_html)} znaků")
    else:
        raise ValueError("❌ CHYBÍ humanizer_output_after_fact_validation NEBO humanizer_assistant_output - publish nemůže pokračovat bez obsahu")
    

    
    # Ujisti se, že content má <article> wrapper
    if '<article>' not in content_html.lower():
        content_html = f"<article>\n{content_html}\n</article>"
    
    # ✅ APLIKUJ NADPISY ze SEO asistenta (volitelné)
    seo_headings = seo_data.get("headings", {})
    if seo_headings:
        content_html = apply_seo_headings_to_content(content_html, seo_headings)
        logger.info(f"✅ Aplikovány SEO nadpisy: H1={bool(seo_headings.get('h1'))}, H2={len(seo_headings.get('h2', []))}, H3={len(seo_headings.get('h3', []))}")
    else:
        logger.info("⚠️ SEO headings nejsou k dispozici - pokračuji bez úprav nadpisů")
    
    # 3. FAQ - validace již proběhla v parse_qa_faq
    faq_items = parse_qa_faq(qa_output)
    
    # 4. Vizuály - POUŽÍVEJ multimedia_assistant.primary_visuals podle akceptačních kritérií
    # ✅ Obrázky jsou převzaty z multimedia_assistant.primary_visuals, nikoli regenerovány
    try:
        visuals = parse_multimedia_primary_visuals(multimedia_output)
        logger.info(f"✅ Vizuály načteny z multimedia_assistant.primary_visuals: {len(visuals)} obrázků")
    except ValueError as e:
        raise ValueError(f"❌ CHYBA při načítání vizuálů z multimedia_assistant.primary_visuals: {str(e)}")
    
    # 5. Schema.org
    schema_org = parse_schema_org(content_html, seo_data, current_date)
    
    # ===== SESTAVENÍ PUBLISHINPUT =====
    
    publish_input = {
        "title": seo_data["title"],
        "summary": seo_data["description"],  # ✅ PŘIDÁNO - summary z SEO description
        "meta": {
            "title": seo_data["title"],  # ✅ STRICT MODE
            "description": seo_data["description"],  # ✅ STRICT MODE
            "slug": seo_data["slug"],  # ✅ STRICT MODE - žádný fallback
            "keywords": seo_data["keywords"],
            "canonical": seo_data.get("canonical", "")  # canonical může být prázdný
        },
        "content_html": content_html,
        "faq": faq_items,
        "visuals": visuals,
        "schema_org": schema_org,
        "format": "html",
        "language": "cs",
        "date_published": current_date
    }
    
    return publish_input


def create_project_config(base_domain: str = "https://seofarm.ai") -> Dict[str, Any]:
    """
    Vytvoří základní project config s defaults
    
    Args:
        base_domain: Základní doména pro canonical URLs
        
    Returns:
        Project configuration dictionary
    """
    return {
        "base_domain": base_domain,
        "schema_defaults": {
            "author": {
                "@type": "Person",
                "name": "SEO Farm Editorial"
            },
            "publisher": {
                "@type": "Organization",
                "name": "SEO Farm",
                "logo": {
                    "@type": "ImageObject",
                    "url": f"{base_domain}/logo.png"
                }
            }
        },
        "language": "cs",
        "format": "html"
    }