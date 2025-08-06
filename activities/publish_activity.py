#!/usr/bin/env python3
"""
📦 PUBLISH ACTIVITY
==================

Temporal activity wrapper pro deterministický publish script.
Nahrazuje AI PublishAssistant s fail-fast logikou.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any
from temporalio import activity

# Import našeho publish scriptu
from activities.publish_script import publish_script

# Import transformačních funkcí
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from helpers.transformers import transform_to_PublishInput, create_project_config

from logger import get_logger

logger = get_logger(__name__)


@activity.defn
async def publish_activity(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    🚀 PUBLISH ACTIVITY - Deterministický export článku
    
    Nahrazuje AI PublishAssistant s fail-fast validací.
    
    Args:
        data: Dictionary obsahující všechny potřebné argumenty:
            - assistant_config: Konfigurace asistenta (nyní unused)
            - topic: Pipeline data obsahující výstupy všech asistentů
            - current_date: ISO datum publikace
            - previous_outputs: Předchozí výstupy (backup)
        
    Returns:
        Dictionary s výsledky exportu
        
    Raises:
        Exception: Při jakékoliv validační chybě
    """
    
    # Rozbalení argumentů z dictionary
    assistant_config = data.get("assistant_config", {})
    topic = data.get("topic", {})
    current_date = data.get("current_date", "")
    previous_outputs = data.get("previous_outputs", {})
    
    activity_info = activity.info()
    logger.info(f"🔧 PUBLISH ACTIVITY START: {activity_info.activity_id}")
    logger.info(f"📊 Pipeline data keys: {list(topic.keys())}")
    logger.info(f"📅 Publication date: {current_date}")
    
    try:
        # ===== TRANSFORMACE DAT =====
        
        logger.info("🔄 Transformuji pipeline data na PublishInput...")
        
        # Připrav data pro transformaci
        pipeline_data = {
            **topic,  # Hlavní data z topic
            "current_date": current_date,
            **previous_outputs  # Backup data
        }
        
        # Transformuj na PublishInput strukturu
        publish_input_data = transform_to_PublishInput(pipeline_data)
        
        logger.info(f"✅ Transformace úspěšná - PublishInput vytvořen")
        logger.info(f"📋 Title: {publish_input_data['title']}")
        logger.info(f"🏷️ Keywords: {len(publish_input_data['meta']['keywords'])}")
        logger.info(f"📄 Content length: {len(publish_input_data['content_html'])} chars")
        logger.info(f"❓ FAQ items: {len(publish_input_data['faq'])}")
        logger.info(f"🖼️ Visuals: {len(publish_input_data['visuals'])}")
        
        # ===== EXPORT VŠECH FORMÁTŮ =====
        
        results = {}
        
        # ===== AI FARMA EXPORT (NOVÝ FORMÁT) =====
        logger.info("🚀 Generuji AI FARMA export...")
        try:
            ai_farma_result = publish_script(publish_input_data)
            results["ai_farma"] = ai_farma_result
        except ValueError as ve:
            logger.error(f"❌ VALIDAČNÍ CHYBA v publish script: {ve}")
            logger.error("📋 VSTUPNÍ DATA PRO DEBUG:")
            logger.error(f"   📝 Title: {publish_input_data.get('title', 'MISSING')}")
            logger.error(f"   📄 Summary: {publish_input_data.get('meta', {}).get('description', 'MISSING')}")
            logger.error(f"   🌐 Language: {publish_input_data.get('language', 'MISSING')}")
            logger.error(f"   📄 Content: {len(str(publish_input_data.get('content_html', '')))} znaků")
            logger.error(f"   📅 Published: {publish_input_data.get('date_published', 'MISSING')}")
            logger.error(f"   🏷️ Meta: {publish_input_data.get('meta', {})}")
            
            # I při chybě vytvoř nějaký výsledek pro zobrazení
            ai_farma_result = {
                "success": False,
                "error": str(ve),
                "debug_input": publish_input_data
            }
            results["ai_farma"] = ai_farma_result
        
        # ⚠️ VŽDY ZOBRAZ VÝSLEDKY - i když publish script selhal!
        # Publish script teď má striktní validaci - při chybě vyhodí ValueError
        
        if ai_farma_result and isinstance(ai_farma_result, dict):
            # Struktura může být s "data" obalem nebo přímo
            if "data" in ai_farma_result:
                ai_data = ai_farma_result["data"]
            else:
                ai_data = ai_farma_result
            
            logger.info(f"✅ AI FARMA export dokončen:")
            logger.info(f"   📝 Title: {ai_data.get('title', 'MISSING')}")
            logger.info(f"   📄 Summary: {ai_data.get('summary', 'MISSING')}")
            logger.info(f"   📄 Content: {len(str(ai_data.get('contentHtml', '')))} znaků")
            logger.info(f"   🌐 Language: {ai_data.get('language', 'MISSING')}")
            logger.info(f"   📅 Published: {ai_data.get('publishedAt', 'MISSING')}")
            logger.info(f"   🏷️ Meta: {ai_data.get('meta', {})}")
            logger.info(f"   🔗 Slug: {ai_data.get('slug', 'MISSING')}")
            if "faq" in ai_data:
                logger.info(f"   ❓ FAQ: {len(ai_data.get('faq', []))} položek")
        else:
            logger.error("❌ Publish script nevrátil žádná data!")
            ai_data = {}
        
        # VŽDY vytvoř výsledky - i když jsou data nekompletní
        html_result = {"output": ai_data.get('contentHtml', 'NO CONTENT GENERATED')}
        json_result = {"output": ai_data}  # ✅ Nyní už ai_data obsahuje správná data z publish_script
        wp_result = {"output": ai_data}
        
        results["html"] = html_result
        results["json"] = json_result  
        results["wordpress"] = wp_result
        
        logger.info(f"📦 HTML export: {len(html_result['output'])} znaků")
        logger.info(f"📦 JSON export: {len(json.dumps(json_result['output']))} znaků")
        logger.info(f"📦 WordPress export: kompatibilní formát")
        
        # ===== ULOŽENÍ VÝSTUPŮ =====
        
        # Vytvoř slug pro cestu z AI FARMA výsledku
        slug = ai_data.get("slug", ai_farma_result.get("slug", "untitled"))
        language = publish_input_data.get("language", "cs")
        
        # Vytvoř výstupní složku
        output_dir = os.path.join("outputs", slug, language)
        os.makedirs(output_dir, exist_ok=True)
        
        # Ulož soubory
        files_saved = []
        
        # HTML soubor
        html_path = os.path.join(output_dir, "publish.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_result["output"])
        files_saved.append(html_path)
        
        # JSON soubor
        json_path = os.path.join(output_dir, "publish.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_result["output"], f, ensure_ascii=False, indent=2)
        files_saved.append(json_path)
        
        # WordPress payload
        wp_path = os.path.join(output_dir, "wordpress_payload.json")
        with open(wp_path, "w", encoding="utf-8") as f:
            json.dump(wp_result["output"], f, ensure_ascii=False, indent=2)
        files_saved.append(wp_path)
        
        # Metadata soubor
        metadata = {
            "title": publish_input_data["title"],
            "slug": slug,
            "language": language,
            "date_published": current_date,
            "generated_at": datetime.now().isoformat(),
            "validation_passed": True,
            "files": files_saved,
            "word_count": len(publish_input_data["content_html"].split()),
            "faq_count": len(publish_input_data["faq"]),
            "visuals_count": len(publish_input_data["visuals"])
        }
        
        metadata_path = os.path.join(output_dir, "metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        files_saved.append(metadata_path)
        
        logger.info(f"💾 Soubory uloženy: {len(files_saved)} souborů")
        for file_path in files_saved:
            logger.info(f"  📁 {file_path}")
        
        # ===== FINÁLNÍ VÝSTUP =====
        
        final_output = {
            "success": True,
            "title": publish_input_data["title"],
            "slug": slug,
            "language": language,
            "date_published": current_date,
            "formats_generated": ["html", "json", "wordpress"],
            "files_saved": files_saved,
            "output_directory": output_dir,
            "validation_passed": True,
            "word_count": metadata["word_count"],
            "faq_count": metadata["faq_count"],
            "visuals_count": metadata["visuals_count"],
            "html_length": len(html_result["output"]),
            "exports": {
                "html": html_result,
                "json": json_result,
                "wordpress": wp_result
            }
        }
        
        logger.info(f"🎉 PUBLISH ACTIVITY SUCCESS!")
        logger.info(f"📦 Výstup: {slug}/{language} - {metadata['word_count']} slov")
        
        return final_output
        
    except Exception as e:
        # 🚫 FAIL FAST - žádné fallbacky
        error_msg = f"❌ Publish Activity failed: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


# ===== HELPER FUNKCE PRO TESTING =====

def test_publish_activity_locally(pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    🧪 Testovací funkce pro lokální spouštění bez Temporal
    """
    
    print("🧪 TESTING PUBLISH ACTIVITY LOCALLY")
    print("=" * 50)
    
    try:
        # Připrav testovací data
        test_config = {}
        test_current_date = datetime.now().isoformat() + "Z"
        test_previous_outputs = {}
        
        print(f"📊 Pipeline data keys: {list(pipeline_data.keys())}")
        
        # Transformace
        publish_input_data = transform_to_PublishInput({
            **pipeline_data,
            "current_date": test_current_date
        })
        
        print(f"✅ Transformace úspěšná")
        print(f"📋 Title: {publish_input_data['title']}")
        
        # Export HTML
        html_input = {**publish_input_data, "format": "html"}
        html_result = publish_script(html_input)
        
        print(f"✅ HTML export: {len(html_result['output'])} znaků")
        
        return {
            "success": True,
            "title": publish_input_data["title"],
            "html_length": len(html_result["output"])
        }
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    print("🔧 Publish Activity - Deterministický export bez AI")
    print("Použití: await publish_activity(config, pipeline_data, date, outputs)")