#!/usr/bin/env python3
"""
🔧 PUBLISH SCRIPT - Deterministický export bez AI
===================================================

Skript sestavuje článkový výstup určený k přímé publikaci z přesně definovaných 
výstupů jednotlivých asistentů. Výstup musí být SEO-ready, LLMO-kompatibilní 
a plně validní pro CMS export.

🚫 ZAKÁZANÉ:
- Žádné fallbacky nebo domýšlení
- Žádná úprava obsahu  
- Žádné LLM volání
- Žádné parsování stringů

✅ POVOLENÉ:
- Strukturování dat
- Validace vstupů
- Generování finálních formátů
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass
from urllib.parse import urlparse


# ===== TYPY A STRUKTURY =====

@dataclass
class PublishMeta:
    description: str
    keywords: List[str]
    canonical: str


@dataclass
class PublishVisual:
    image_url: str
    prompt: str
    alt: str
    position: Literal["top", "bottom"]
    srcset: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class PublishFAQ:
    question: str
    answer_html: str


@dataclass
class PublishInput:
    title: str
    meta: PublishMeta
    content_html: str
    faq: List[PublishFAQ]
    visuals: List[PublishVisual]
    schema_org: Dict[str, Any]
    format: Literal["html", "json", "wordpress"]
    language: str
    date_published: str


@dataclass
class PublishOutput:
    title: str
    slug: str
    language: str
    meta: Dict[str, Any]
    content_html: str
    visuals: List[Dict[str, Any]]
    faq: List[Dict[str, Any]]
    schema_org: Dict[str, Any]
    format: str


# ===== VALIDAČNÍ FUNKCE =====

def is_valid_url(url: str) -> bool:
    """Validuje URL struktura"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def is_valid_iso_date(date_str: str) -> bool:
    """Validuje ISO datum format"""
    try:
        datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False


def validate_image_format(url: str) -> bool:
    """Kontroluje povolené formáty obrázků"""
    allowed_formats = ['.webp', '.jpg', '.jpeg', '.png']
    return any(url.lower().endswith(fmt) for fmt in allowed_formats)


def count_words(html: str) -> int:
    """Počítá slova v HTML (bez tagů)"""
    text = re.sub(r'<[^>]+>', '', html)
    words = re.findall(r'\b\w+\b', text)
    return len(words)


def count_h2_tags(html: str) -> int:
    """Počítá H2 tagy v HTML"""
    return len(re.findall(r'<h2[^>]*>', html, re.IGNORECASE))


def has_article_wrapper(html: str) -> bool:
    """Kontroluje přítomnost <article> wrapperu"""
    return '<article' in html.lower()


# ===== HLAVNÍ VALIDACE =====

def validate_publish_input_debug(input_data: PublishInput) -> PublishInput:
    """
    🔍 DIAGNOSTIC VALIDACE - označí problémy ve výstupu místo failování
    
    Místo:
    - ❌ Strict mode (fail) 
    - ❌ Fallback (fake data)
    
    Použije:
    - ✅ Označí chybějící data jako "[CHYBÍ - ...]" 
    - ✅ Výstup bude zelený ale ukáže co nefunguje
    - ✅ Perfektní pro debugging pipeline
    """
    from logger import get_logger
    logger = get_logger(__name__)
    
    # Zkopíruj data pro úpravu
    import copy
    fixed_data = copy.deepcopy(input_data)
    
    # Title validace - UKÁŽ PROBLÉM VE VÝSTUPU
    if not fixed_data.title:
        logger.warning("⚠️ TITLE chybí")
        fixed_data.title = "[CHYBÍ - Žádný title]"
    elif len(fixed_data.title) > 70:
        logger.warning(f"⚠️ TITLE příliš dlouhý ({len(fixed_data.title)}/70)")
        fixed_data.title = f"[DLOUHÝ-{len(fixed_data.title)}] {fixed_data.title[:50]}..."
    
    # Meta description - UKÁŽ PROBLÉM VE VÝSTUPU
    if not fixed_data.meta.description:
        logger.warning("⚠️ DESCRIPTION chybí")  
        fixed_data.meta.description = "[CHYBÍ - Žádná meta description]"
    elif len(fixed_data.meta.description) > 160:
        logger.warning(f"⚠️ DESCRIPTION příliš dlouhá ({len(fixed_data.meta.description)}/160)")
        fixed_data.meta.description = f"[DLOUHÁ-{len(fixed_data.meta.description)}] {fixed_data.meta.description[:120]}..."
    
    # Keywords - UKÁŽ PROBLÉM VE VÝSTUPU
    if len(fixed_data.meta.keywords) < 5:
        logger.warning(f"⚠️ MÁLO KEYWORDS ({len(fixed_data.meta.keywords)}/5)")
        missing_count = 5 - len(fixed_data.meta.keywords)
        fixed_data.meta.keywords.extend([f"[CHYBÍ-KW-{i+1}]" for i in range(missing_count)])
    
    if len(fixed_data.meta.keywords) > 10:
        logger.warning(f"⚠️ MOC KEYWORDS ({len(fixed_data.meta.keywords)}/10)")
        fixed_data.meta.keywords = fixed_data.meta.keywords[:9] + [f"[+{len(fixed_data.meta.keywords)-9}-VÍCE]"]
        
    # Unikátnost keywords
    if len(set(fixed_data.meta.keywords)) != len(fixed_data.meta.keywords):
        logger.warning("⚠️ DUPLICITNÍ KEYWORDS")
        seen = set()
        unique_kw = []
        for kw in fixed_data.meta.keywords:
            if kw not in seen:
                unique_kw.append(kw)
                seen.add(kw)
            else:
                unique_kw.append(f"[DUPLIKÁT-{kw}]")
        fixed_data.meta.keywords = unique_kw
    
    # Canonical URL - UKÁŽ PROBLÉM VE VÝSTUPU
    if not fixed_data.meta.canonical:
        logger.warning("⚠️ CANONICAL URL chybí")
        fixed_data.meta.canonical = "[CHYBÍ - Žádná canonical URL]"
    elif not is_valid_url(fixed_data.meta.canonical):
        logger.warning("⚠️ CANONICAL URL neplatná")
        fixed_data.meta.canonical = f"[NEPLATNÁ] {fixed_data.meta.canonical}"
    
    # Content HTML - UKÁŽ PROBLÉM VE VÝSTUPU
    if not fixed_data.content_html:
        logger.warning("⚠️ CONTENT HTML chybí")
        fixed_data.content_html = f"""
        <article>
            <h1>[CHYBÍ OBSAH]</h1>
            <p><strong>PROBLÉM:</strong> Žádný content HTML nebyl vygenerován.</p>
            <p><em>Zkontrolujte Draft a Humanizer asistenty.</em></p>
        </article>
        """
    
    # Article wrapper
    if not has_article_wrapper(fixed_data.content_html):
        logger.warning("⚠️ CHYBÍ ARTICLE WRAPPER")
        fixed_data.content_html = f"<article>\n{fixed_data.content_html}\n</article>"
    
    # Word count check (DIAGNOSTIC, ne fail)
    word_count = count_words(fixed_data.content_html)
    if word_count < 1200:
        logger.warning(f"⚠️ KRÁTKÝ ČLÁNEK ({word_count}/1200 slov)")
    
    return fixed_data


def validate_publish_input(input_data: PublishInput) -> None:
    """
    🔐 STRIKTNÍ VALIDACE - fail-fast na jakoukoliv chybu (DEPRECATED - používej debug verzi)
    """
    
    # Title validace
    if not input_data.title or len(input_data.title) > 70:
        raise ValueError("Missing or invalid title")
    
    # Meta description validace
    if not input_data.meta.description or len(input_data.meta.description) > 160:
        raise ValueError("Missing or invalid meta description")
    
    # Keywords validace
    if len(input_data.meta.keywords) < 5 or len(input_data.meta.keywords) > 10:
        raise ValueError("Invalid or missing keywords")
    
    # Kontrola unikátnosti klíčových slov
    if len(set(input_data.meta.keywords)) != len(input_data.meta.keywords):
        raise ValueError("Keywords must be unique")
    
    # Canonical URL validace - STRICT MODE, žádné fallbacky
    if not input_data.meta.canonical or not is_valid_url(input_data.meta.canonical):
        raise ValueError("Invalid canonical URL")
    
    # Content HTML validace
    if not input_data.content_html:
        raise ValueError("Missing content_html")
    
    if not has_article_wrapper(input_data.content_html):
        raise ValueError("Invalid or incomplete content_html - missing <article> wrapper")
    
    word_count = count_words(input_data.content_html)
    if word_count < 1200:
        raise ValueError(f"Invalid or incomplete content_html - only {word_count} words (minimum 1200)")
    
    h2_count = count_h2_tags(input_data.content_html)
    if h2_count < 5:
        raise ValueError(f"Invalid or incomplete content_html - only {h2_count} H2 tags (minimum 5)")
    
    # FAQ validace
    if len(input_data.faq) < 3:
        raise ValueError("Insufficient FAQ items")
    
    for i, faq_item in enumerate(input_data.faq):
        if not faq_item.question or not faq_item.answer_html:
            raise ValueError(f"FAQ item {i+1} missing question or answer")
    
    # Visuals validace
    if len(input_data.visuals) != 2:
        raise ValueError("Invalid visuals block - must contain exactly 2 items")
    
    for i, visual in enumerate(input_data.visuals):
        if not visual.image_url or not validate_image_format(visual.image_url):
            raise ValueError(f"Visual {i+1} has invalid image_url or unsupported format")
        
        if not visual.alt or not visual.position:
            raise ValueError(f"Visual {i+1} missing alt text or position")
        
        if visual.position not in ["top", "bottom"]:
            raise ValueError(f"Visual {i+1} invalid position - must be 'top' or 'bottom'")
    
    # Schema.org validace
    if not input_data.schema_org or input_data.schema_org.get("@type") != "Article":
        raise ValueError("Invalid schema_org - must be Article type")
    
    required_schema_fields = ["headline", "author", "datePublished"]
    for field in required_schema_fields:
        if field not in input_data.schema_org:
            raise ValueError(f"Invalid schema_org - missing {field}")
    
    # Date published validace
    if not is_valid_iso_date(input_data.date_published):
        raise ValueError("Invalid date_published format")
    
    # Language validace
    if not input_data.language:
        raise ValueError("Missing language")
    
    # Format validace
    if input_data.format not in ["html", "json", "wordpress"]:
        raise ValueError("Invalid format - must be html, json, or wordpress")


# ===== GENEROVÁNÍ SLUG =====

def generate_slug(title: str) -> str:
    """Generuje URL-safe slug z titulu"""
    # Převod na lowercase a normalizace
    slug = title.lower()
    
    # Nahrazení českých znaků
    czech_map = {
        'á': 'a', 'č': 'c', 'ď': 'd', 'é': 'e', 'ě': 'e',
        'í': 'i', 'ň': 'n', 'ó': 'o', 'ř': 'r', 'š': 's',
        'ť': 't', 'ú': 'u', 'ů': 'u', 'ý': 'y', 'ž': 'z'
    }
    
    for czech, latin in czech_map.items():
        slug = slug.replace(czech, latin)
    
    # Odstranění speciálních znaků a nahrazení mezerami
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    
    # Nahrazení mezer a vícenásobných pomlček jednou pomlčkou
    slug = re.sub(r'[\s-]+', '-', slug)
    
    # Oříznutí pomlček na začátku a konci
    slug = slug.strip('-')
    
    # Omezení délky
    if len(slug) > 60:
        slug = slug[:60].rstrip('-')
    
    return slug


# ===== HTML EXPORT =====

def generate_html_output(input_data: PublishInput) -> str:
    """
    Generuje kompletní SEO-ready HTML článek
    """
    
    slug = generate_slug(input_data.title)
    
    # Meta tagy
    meta_keywords = ', '.join(input_data.meta.keywords)
    
    # Schema.org JSON-LD
    schema_json = json.dumps(input_data.schema_org, ensure_ascii=False, indent=2)
    
    # Visuals - rozdělení na top/bottom
    top_visuals = [v for v in input_data.visuals if v.position == "top"]
    bottom_visuals = [v for v in input_data.visuals if v.position == "bottom"]
    
    def render_visual(visual: PublishVisual) -> str:
        srcset_attr = f' srcset="{visual.srcset}"' if visual.srcset else ''
        width_attr = f' width="{visual.width}"' if visual.width else ''
        height_attr = f' height="{visual.height}"' if visual.height else ''
        
        return f'''
        <figure class="article-visual">
            <img src="{visual.image_url}" 
                 alt="{visual.alt}"{srcset_attr}{width_attr}{height_attr}
                 loading="lazy" />
            <figcaption>{visual.alt}</figcaption>
        </figure>'''
    
    # FAQ sekce
    faq_items = []
    for faq in input_data.faq:
        faq_items.append(f'''
        <div class="faq-item">
            <h3 class="faq-question">{faq.question}</h3>
            <div class="faq-answer">{faq.answer_html}</div>
        </div>''')
    
    faq_section = f'''
    <section id="faq" class="faq-section">
        <h2>Často kladené otázky</h2>
        {''.join(faq_items)}
    </section>'''
    
    # Sestavení kompletního HTML
    html_output = f'''<!DOCTYPE html>
<html lang="{input_data.language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{input_data.title}</title>
    <meta name="description" content="{input_data.meta.description}">
    <meta name="keywords" content="{meta_keywords}">
    <link rel="canonical" href="{input_data.meta.canonical}">
    <meta property="og:title" content="{input_data.title}">
    <meta property="og:description" content="{input_data.meta.description}">
    <meta property="og:url" content="{input_data.meta.canonical}">
    <meta property="og:type" content="article">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{input_data.title}">
    <meta name="twitter:description" content="{input_data.meta.description}">
    
    <script type="application/ld+json">
{schema_json}
    </script>
</head>
<body>
    <header>
        <h1>{input_data.title}</h1>
        <time datetime="{input_data.date_published}">{input_data.date_published}</time>
    </header>
    
    <main>
        {''.join(render_visual(v) for v in top_visuals)}
        
        <section class="article-content">
            {input_data.content_html}
        </section>
        
        {''.join(render_visual(v) for v in bottom_visuals)}
        
        {faq_section}
    </main>
    
    <footer>
        <p>Publikováno: {input_data.date_published}</p>
    </footer>
</body>
</html>'''
    
    return html_output


# ===== JSON EXPORT =====

def generate_json_output(input_data: PublishInput) -> Dict[str, Any]:
    """
    Generuje strukturovaný JSON výstup
    """
    
    return {
        "title": input_data.title,
        "slug": generate_slug(input_data.title),
        "language": input_data.language,
        "meta": {
            "title": getattr(input_data.meta, 'title', input_data.title),  # ✅ PŘIDÁNO
            "description": input_data.meta.description,
            "slug": getattr(input_data.meta, 'slug', generate_slug(input_data.title)),  # ✅ PŘIDÁNO
            "keywords": input_data.meta.keywords,
            "canonical": input_data.meta.canonical
        },
        "content_html": input_data.content_html,
        "visuals": [
            {
                "image_url": v.image_url,
                "alt": v.alt,
                "position": v.position,
                "srcset": v.srcset,
                "width": v.width,
                "height": v.height
            } for v in input_data.visuals
        ],
        "faq": [
            {
                "question": faq.question,
                "answer_html": faq.answer_html
            } for faq in input_data.faq
        ],
        "schema_org": input_data.schema_org,
        "date_published": input_data.date_published,
        "format": input_data.format
    }


# ===== WORDPRESS EXPORT =====

def generate_wordpress_output(input_data: PublishInput) -> Dict[str, Any]:
    """
    Generuje WordPress import payload
    """
    
    # WordPress formát content
    wp_content = input_data.content_html
    
    # Přidání FAQ sekce do content
    faq_html = '<h2>Často kladené otázky</h2>\n'
    for faq in input_data.faq:
        faq_html += f'<h3>{faq.question}</h3>\n{faq.answer_html}\n'
    
    wp_content += f'\n\n{faq_html}'
    
    # WordPress meta fields
    wp_meta = {
        "_yoast_wpseo_title": input_data.title,
        "_yoast_wpseo_metadesc": input_data.meta.description,
        "_yoast_wpseo_canonical": input_data.meta.canonical,
        "_yoast_wpseo_focuskw": input_data.meta.keywords[0] if input_data.meta.keywords else "",
        "_featured_image": input_data.visuals[0].image_url if input_data.visuals else "",
        "_schema_org": json.dumps(input_data.schema_org)
    }
    
    return {
        "post_title": input_data.title,
        "post_content": wp_content,
        "post_status": "draft",
        "post_type": "post",
        "post_date": input_data.date_published,
        "meta_input": wp_meta,
        "tags_input": input_data.meta.keywords,
        "post_category": [],  # Kategorie se nastaví ručně
        "post_name": generate_slug(input_data.title)
    }


# ===== HLAVNÍ FUNKCE =====

def publish_script(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    🚀 AI FARMA FORMÁT - ČISTÝ JSON PRO LANDING PAGE API
    
    Generuje čistý JSON v AI Farma formátu bez meta-informací z orchestrátoru.
    
    Args:
        input_data: Slovník s daty od asistentů
        
    Returns:
        Čistý AI Farma JSON nebo Legacy formát podle specifikace
    """
    
    def clean_text(text: str) -> str:
        """Očistí text od debug prefixů a neplatných znaků"""
        if not text:
            return ""
        # Odstranění debug prefixů
        text = re.sub(r'^(\*\*:\s*"|\[.*?\]\s*)', '', text.strip())
        # Odstranění koncových uvozovek
        text = text.rstrip('"').strip()
        return text
    
    def fix_iso_date(date_str: str) -> str:
        """Opraví datum na správný ISO formát"""
        if not date_str:
            from datetime import datetime, timezone
            return datetime.now(timezone.utc).isoformat()
        
        # Pokud je datum ve špatném formátu, oprav
        if not is_valid_iso_date(date_str):
            try:
                # Pokus se parsovat různé formáty
                from datetime import datetime, timezone
                
                # Formát "05. 08. 2025Z"
                if re.match(r'\d{1,2}\.\s*\d{1,2}\.\s*\d{4}Z?', date_str):
                    parts = re.findall(r'\d+', date_str)
                    if len(parts) >= 3:
                        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                        dt = datetime(year, month, day, tzinfo=timezone.utc)
                        return dt.isoformat()
                
                # STRICT MODE - žádné fallbacky na současné datum
                raise ValueError("❌ Nevalidní datum formát - datum musí být explicitně předán")
            except Exception as e:
                # STRICT MODE - žádné fallbacky
                raise ValueError(f"❌ Chyba při parsování data: {str(e)}")
        
        return date_str
    
    try:
        # ===== STRIKTNÍ VALIDACE BEZ FALLBACKŮ =====
        
        # 1. TITLE - povinné, neprázdné
        title = input_data.get("title")
        if not title or not isinstance(title, str) or not title.strip():
            raise ValueError("Missing or invalid title")
        title = clean_text(title.strip())
        
        # 2. META - povinné, neprázdné dict
        meta_data = input_data.get("meta")
        if not meta_data or not isinstance(meta_data, dict):
            raise ValueError("Missing or invalid meta")
        
        # 🔧 META.TITLE - STRIKTNÍ VALIDACE, ZERO FALLBACKS
        meta_title = meta_data.get("title")
        if not isinstance(meta_title, str):
            raise ValueError("❌ InvalidMetadataException: meta.title není string")
        if not meta_title.strip():
            raise ValueError("❌ InvalidMetadataException: meta.title je prázdný")
        
        meta_title = clean_text(meta_title.strip())
        
        # FALLBACK DETECTION - ZERO TOLERANCE
        fallback_titles = ["článek bez názvu", "clanek-bez-nazvu", "article without title", "bez názvu"]
        if meta_title.lower() in fallback_titles:
            raise ValueError(f"❌ Meta title obsahuje fallback hodnotu: '{meta_title}'")
        
        # 🔧 META.SLUG - POVINNÉ, neprázdné string, BEZ FALLBACKŮ
        meta_slug = meta_data.get("slug")
        if not isinstance(meta_slug, str):
            raise ValueError("❌ InvalidMetadataException: meta.slug není string")
        if not meta_slug.strip():
            raise ValueError("❌ InvalidMetadataException: meta.slug je prázdný")
        
        meta_slug = clean_text(meta_slug.strip())
        
        # FALLBACK DETECTION - ZERO TOLERANCE  
        fallback_slugs = ["clanek-bez-nazvu", "article-without-title", "bez-nazvu", "no-title"]
        if meta_slug.lower() in fallback_slugs:
            raise ValueError(f"❌ Meta slug obsahuje fallback hodnotu: '{meta_slug}'")
        
        # 3. SUMMARY - STRIKTNÍ VALIDACE (z meta.description)
        summary = meta_data.get("description")
        if not isinstance(summary, str):
            raise ValueError("❌ InvalidMetadataException: meta.description není string")
        if not summary.strip():
            raise ValueError("❌ InvalidMetadataException: meta.description je prázdný")
        
        summary = clean_text(summary.strip())
        
        # FALLBACK DETECTION pro description
        fallback_descriptions = ["popis není dostupný", "popis-neni-dostupny", "description not available", "bez popisu"]
        if summary.lower() in fallback_descriptions:
            raise ValueError(f"❌ Meta description obsahuje fallback hodnotu: '{summary}'")
        
        # 4. KEYWORDS - povinné v meta, musí být list
        keywords = meta_data.get("keywords")
        if not isinstance(keywords, list):
            raise ValueError("❌ InvalidMetadataException: meta.keywords není list")
        # Keywords mohou být prázdný list, ale musí být list
        
        # 5. LANGUAGE - povinné, platná hodnota
        language = input_data.get("language")
        if not language or not isinstance(language, str):
            raise ValueError("Missing or invalid language")
        language = language.strip().lower()
        if language not in ["cs", "en", "de", "fr", "es"]:
            raise ValueError("Missing or invalid language")
        
        # 6. CONTENT_HTML - povinné, neprázdné
        content_html = input_data.get("content_html")
        if not content_html or not isinstance(content_html, str) or not content_html.strip():
            raise ValueError("Missing or invalid contentHtml")
        content_html = content_html.strip()
        
        # 7. PUBLISHED_AT - povinné, ISO 8601 formát
        published_at_raw = input_data.get("date_published")
        if not published_at_raw or not isinstance(published_at_raw, str):
            raise ValueError("Missing or invalid publishedAt")
        published_at = fix_iso_date(published_at_raw)
        if not published_at:
            raise ValueError("Missing or invalid publishedAt")
        
        # 8. FAQ - volitelné, ale pokud existuje musí být validní
        faq_data = input_data.get("faq")
        cleaned_faq = []
        if faq_data is not None:
            if not isinstance(faq_data, list):
                raise ValueError("FAQ is malformed")
            
            for faq_item in faq_data:
                if not isinstance(faq_item, dict):
                    raise ValueError("FAQ is malformed")
                
                question = faq_item.get("question")
                answer = faq_item.get("answer_html")
                
                if not question or not isinstance(question, str) or not question.strip():
                    raise ValueError("FAQ is malformed")
                if not answer or not isinstance(answer, str) or not answer.strip():
                    raise ValueError("FAQ is malformed")
                    
                cleaned_faq.append({
                    "question": clean_text(question.strip()),
                    "answer": answer.strip()
                })
        
        # Slug - generovat z title
        slug = generate_slug(title)
        
        # ===== AI FARMA FORMÁT - VŠECHNA POLE POVINNÁ =====
        ai_farma_result = {
            "title": meta_title,  # ✅ OPRAVA: Použít správný title z meta
            "summary": summary,   # ✅ summary už je správný (z meta.description)
            "language": language,
            "contentHtml": content_html,
            "meta": {
                "title": meta_title,  # ✅ PŘIDÁNO - ze seo_assistant_output.metadata.title
                "description": summary,  # ✅ ze seo_assistant_output.metadata.meta_description
                "slug": meta_slug,  # ✅ PŘIDÁNO - ze seo_assistant_output.metadata.slug
                "keywords": keywords
            },
            "publishedAt": published_at,
            "slug": meta_slug  # ✅ OPRAVA: Použít správný slug z meta
        }
        
        # FAQ je volitelné, ale pokud existuje, přidat ho
        if cleaned_faq:
            ai_farma_result["faq"] = cleaned_faq
        
        # Obrázek z visuals (pokud existuje)
        visuals = input_data.get("visuals", [])
        if visuals and len(visuals) > 0:
            first_visual = visuals[0]
            image_url = first_visual.get("image_url", "")
            if image_url and is_valid_url(image_url):
                ai_farma_result["imageUrl"] = image_url
        
        print("✅ ČISTÝ AI FARMA VÝSTUP:")
        print("=" * 60)
        print(json.dumps(ai_farma_result, indent=2, ensure_ascii=False))
        print("=" * 60)
        
        # Wrap s success statusem pro backend kompatibilitu
        return {
            "success": True,
            "data": ai_farma_result,
            **ai_farma_result  # Také přímo pro kompatibilitu
        }
        
    except Exception as e:
        print(f"❌ VALIDAČNÍ CHYBA V PUBLISH SCRIPT: {e}")
        # Žádné fallbacky! Vyhodit výjimku aby se uživatel dozvěděl co je špatně
        raise


if __name__ == "__main__":
    print("🔧 Publish Script - Deterministický export bez AI")
    print("Použití: import publish_script; publish_script.publish_script(data)")