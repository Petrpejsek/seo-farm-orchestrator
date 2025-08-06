#!/usr/bin/env python3
"""
🧪 TEST AI FARMA FORMÁTU
========================

Rychlý test aby ověřil že nový publish_script správně generuje AI FARMA formát.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from activities.publish_script import publish_script

def test_ai_farma_format():
    """Test AI FARMA formátu s minimálními daty"""
    
    test_data = {
        "title": "Test článek pro AI FARMA",
        "content_html": "<article><h1>Test článek</h1><p>Toto je testovací obsah pro AI FARMA formát. Musí mít minimálně 100 znaků aby prošel validací. Takže přidám ještě trochu více textu aby bylo jasné že validace funguje správně.</p></article>",
        "meta": {
            "description": "Testovací popis článku pro AI FARMA formát",
            "keywords": ["test", "ai", "farma", "format", "validace"],
            "canonical": "https://example.com/test-clanek"
        },
        "language": "cs",
        "date_published": "2024-01-15T10:30:00.000Z",
        "faq": [
            {"question": "Test otázka 1?", "answer_html": "<p>Test odpověď 1</p>"},
            {"question": "Test otázka 2?", "answer_html": "<p>Test odpověď 2</p>"},
            {"question": "Test otázka 3?", "answer_html": "<p>Test odpověď 3</p>"}
        ],
        "visuals": [
            {"image_url": "https://example.com/image1.jpg", "alt": "Test obrázek 1", "position": "top"},
            {"image_url": "https://example.com/image2.jpg", "alt": "Test obrázek 2", "position": "bottom"}
        ],
        "schema_org": {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "Test článek pro AI FARMA",
            "author": {"@type": "Person", "name": "Test Author"}
        }
    }
    
    print("🧪 Testuju AI FARMA formát...")
    print("=" * 50)
    
    try:
        result = publish_script(test_data)
        
        print(f"✅ Výsledek: {result}")
        print("")
        
        # Kontrola formátu
        if "error" in result:
            print(f"❌ CHYBA: {result['error']}")
            if "details" in result:
                for detail in result["details"]:
                    print(f"   - {detail}")
            return False
        else:
            print(f"✅ STATUS: {result.get('status', 'unknown')}")
            print(f"✅ URL: {result.get('url', 'missing')}")
            print(f"✅ SLUG: {result.get('slug', 'missing')}")
            
            if "data" in result:
                data = result["data"]
                print(f"✅ DATA FIELDS:")
                print(f"   - title: {data.get('title', 'missing')}")
                print(f"   - language: {data.get('language', 'missing')}")
                print(f"   - keywords: {len(data.get('keywords', []))} items")
                print(f"   - contentHtml: {len(data.get('contentHtml', ''))} znaků")
                print(f"   - faq: {len(data.get('faq', []))} items")
            
            return True
            
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_ai_farma_format()
    if success:
        print("\n🎉 TEST ÚSPĚŠNÝ - AI FARMA formát funguje!")
    else:
        print("\n💥 TEST SELHAL - AI FARMA formát má problémy!")
        sys.exit(1)