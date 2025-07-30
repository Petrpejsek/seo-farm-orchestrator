#!/usr/bin/env python3
"""
CLI nástroj pro testování jednotlivých aktivit SEO Farm Orchestrátoru
Podporuje bulk processing témat z CSV souboru
"""

import asyncio
import sys
import os
import json
import csv
import argparse
from datetime import datetime

# Přidání cesty pro import aktivit
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from activities.generate_llm_friendly_content import generate_llm_friendly_content
from activities.inject_structured_markup import inject_structured_markup
from activities.enrich_with_entities import enrich_with_entities
from activities.add_conversational_faq import add_conversational_faq
from activities.save_output import save_output_to_json

async def test_activity(activity_name: str, topic: str):
    """Testuje jednotlivou aktivitu"""
    
    print(f"🧪 Testuji aktivitu: {activity_name}")
    print(f"📝 Téma: {topic}")
    print("-" * 50)
    
    try:
        if activity_name == "generate_llm_friendly_content":
            result = await generate_llm_friendly_content(topic)
            
        elif activity_name == "inject_structured_markup":
            # Pro tuto aktivitu potřebujeme vstupní obsah
            test_content = f"# {topic}\n\nTest obsah pro markup."
            result = await inject_structured_markup(test_content)
            
        elif activity_name == "enrich_with_entities":
            test_content = f"# {topic}\n\nTest obsah pro obohacení."
            result = await enrich_with_entities(test_content)
            
        elif activity_name == "add_conversational_faq":
            test_content = f"# {topic}\n\nTest obsah pro FAQ."
            result = await add_conversational_faq(test_content)
            
        elif activity_name == "save_output_to_json":
            test_data = {
                "topic": topic,
                "generated": f"Test content for {topic}",
                "structured": "Test structured content",
                "enriched": "Test enriched content", 
                "faq_final": "Test FAQ content",
                "workflow_id": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            result = await save_output_to_json(test_data)
            
        else:
            print(f"❌ Neznámá aktivita: {activity_name}")
            return
            
        print(f"✅ Výsledek:")
        print(result)
        print(f"\n📏 Délka výstupu: {len(str(result))} znaků")
        
    except Exception as e:
        print(f"❌ Chyba při testování aktivity: {e}")

async def process_single_topic(topic: str, topic_index: int = None) -> str:
    """Zpracuje jedno téma celým pipeline"""
    
    if topic_index is not None:
        print(f"🔄 [{topic_index}] Zpracovávám: {topic}")
    else:
        print(f"🚀 Zpracovávám: {topic}")
    print("=" * 60)
    
    try:
        # 1️⃣ Generování LLM-friendly obsahu
        print("1️⃣ Generování obsahu...")
        content = await generate_llm_friendly_content(topic)
        print(f"   ✅ Dokončeno ({len(content)} znaků)")
        
        # 2️⃣ Přidání strukturovaného JSON-LD
        print("2️⃣ Přidání JSON-LD markup...")
        structured = await inject_structured_markup(content)
        print(f"   ✅ Dokončeno ({len(structured)} znaků)")
        
        # 3️⃣ Obohacení entitami
        print("3️⃣ Obohacení entitami...")
        enriched = await enrich_with_entities(structured)
        print(f"   ✅ Dokončeno ({len(enriched)} znaků)")
        
        # 4️⃣ Přidání konverzačních FAQ
        print("4️⃣ Přidání FAQ...")
        faq_final = await add_conversational_faq(enriched)
        print(f"   ✅ Dokončeno ({len(faq_final)} znaků)")
        
        # 5️⃣ Ukládání do JSON a DB
        print("5️⃣ Ukládání výstupu...")
        
        # Vytvoření bezpečného názvu souboru z tématu
        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_topic = safe_topic.replace(' ', '_')[:50]  # Omezení délky
        
        result_data = {
            "topic": topic,
            "generated": content,
            "structured": structured,
            "enriched": enriched,
            "faq_final": faq_final,
            "workflow_id": f"cli_{safe_topic}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        saved_path = await save_output_to_json(result_data)
        print(f"   ✅ Uloženo do: {saved_path}")
        
        print(f"✅ Pipeline dokončen pro: {topic}")
        return saved_path
        
    except Exception as e:
        print(f"❌ Chyba v pipeline pro téma '{topic}': {e}")
        return None

async def process_csv_topics(csv_file: str):
    """Zpracuje témata z CSV souboru"""
    
    if not os.path.exists(csv_file):
        print(f"❌ CSV soubor neexistuje: {csv_file}")
        return
    
    topics = []
    
    # Načtení témat z CSV
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f)
            for row_num, row in enumerate(csv_reader, 1):
                if row and row[0].strip():  # Přeskočit prázdné řádky
                    topics.append(row[0].strip())
                    
    except Exception as e:
        print(f"❌ Chyba při čtení CSV souboru: {e}")
        return
    
    if not topics:
        print(f"❌ Žádná témata nenalezena v CSV souboru: {csv_file}")
        return
    
    print(f"📋 Nalezeno {len(topics)} témat v souboru: {csv_file}")
    print("🚀 Začínám bulk processing...")
    print("=" * 80)
    
    successful = 0
    failed = 0
    results = []
    
    for i, topic in enumerate(topics, 1):
        print(f"\n[{i}/{len(topics)}] " + "="*50)
        result = await process_single_topic(topic, i)
        
        if result:
            successful += 1
            results.append({"topic": topic, "file": result})
        else:
            failed += 1
        
        # Pauza mezi tématy pro předejití rate limitů
        if i < len(topics):
            print(f"⏱️  Pauza 2s před dalším tématem...")
            await asyncio.sleep(2)
    
    print("\n" + "="*80)
    print(f"📊 SOUHRN BULK PROCESSINGU:")
    print(f"   ✅ Úspěšně zpracováno: {successful}")
    print(f"   ❌ Neúspěšných: {failed}")
    print(f"   📁 Výsledky uloženy v: outputs/")
    
    if results:
        print(f"\n📋 Seznam vytvořených souborů:")
        for result in results:
            print(f"   • {result['topic']} → {result['file']}")

def main():
    parser = argparse.ArgumentParser(
        description="🛠️ SEO Farm Orchestrator - Test CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Příklady použití:
  python scripts/test_cli.py pipeline "AI nástroje pro marketing"
  python scripts/test_cli.py --csv input/topics.csv
        """
    )
    
    parser.add_argument(
        'command', 
        nargs='?',
        choices=['pipeline'],
        help='Příkaz k provedení'
    )
    
    parser.add_argument(
        'topic',
        nargs='?',
        help='Téma pro zpracování'
    )
    
    parser.add_argument(
        '--csv',
        type=str,
        help='Cesta k CSV souboru s tématy (jeden řádek = jedno téma)'
    )
    
    args = parser.parse_args()
    
    # Zpracování CSV souboru
    if args.csv:
        asyncio.run(process_csv_topics(args.csv))
        return
    
    # Jednotlivé téma
    if not args.command:
        parser.print_help()
        return
    
    if not args.topic:
        print("❌ Chybí téma. Použijte: python scripts/test_cli.py pipeline 'Vaše téma'")
        return
    
    if args.command == "pipeline":
        asyncio.run(process_single_topic(args.topic))

if __name__ == "__main__":
    main() 