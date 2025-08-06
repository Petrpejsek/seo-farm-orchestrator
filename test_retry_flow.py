#!/usr/bin/env python3
"""
Test přesného flow retry_publish_script s reálnými SEO daty
"""
import sys
import json
sys.path.append('.')

def test_retry_flow():
    """Simuluje přesný flow retry endpointu"""
    print("🧪 TESTOVÁNÍ RETRY FLOW...")
    
    # Simulace reálných SEO dat jak je produkuje asistent
    seo_assistant_output = """```json
{
  "metadata": {
    "title": "Fotovoltaika pro domácnosti 2025: Ceny, technologie, návratnost",
    "meta_description": "Kompletní průvodce fotovoltaikou v roce 2025: ceny, technologie, návratnost. Zjistěte, jak optimalizovat investici.",
    "slug": "fotovoltaika-pro-domacnosti-2025-ceny-technologie-navratnost"
  },
  "keywords": ["fotovoltaika 2025", "domácí fotovoltaika", "cenové rozpětí"]
}
```"""

    # Simulace components jak jsou extrahovány z stage_logs
    components = {
        "draft_assistant_output": "# Test článek\n\nObsah článku...",
        "seo_assistant_output": seo_assistant_output,
        "humanizer_output_after_fact_validation": "# Test článek\n\nObsah článku...",
        "multimedia_assistant_output": '{"primary_visuals": [{"position": "úvod", "type": "infographic", "description": "Test obrázek 1"}, {"position": "střed", "type": "diagram", "description": "Test obrázek 2"}]}',
        "qa_assistant_output": '{"faq": [{"question": "Test otázka 1?", "answer": "Test odpověď 1"}, {"question": "Test otázka 2?", "answer": "Test odpověď 2"}, {"question": "Test otázka 3?", "answer": "Test odpověď 3"}]}',
        "current_date": "2025-08-05T21:30:00.000Z"
    }
    
    print("📊 Simuluji retry flow:")
    print(f"   SEO output length: {len(components['seo_assistant_output'])}")
    
    try:
        # 1. Debug parsing (jak je v retry endpointu)
        from helpers.transformers import parse_seo_metadata
        seo_data = parse_seo_metadata(components.get('seo_assistant_output', ''))
        print(f"✅ Debug SEO parsing:")
        print(f"   Title: {seo_data.get('title', 'MISSING')}")
        print(f"   Description: {seo_data.get('description', 'MISSING')[:100]}...")
        print(f"   Slug: {seo_data.get('slug', 'MISSING')}")
        
        # 2. Transform (jak je v retry endpointu)
        from helpers.transformers import transform_to_PublishInput
        publish_input = transform_to_PublishInput(components)
        print(f"✅ Transform dokončen:")
        print(f"   PublishInput title: {publish_input.get('title', 'MISSING')}")
        print(f"   PublishInput summary: {publish_input.get('summary', 'MISSING')[:100]}...")
        print(f"   PublishInput meta.title: {publish_input.get('meta', {}).get('title', 'MISSING')}")
        print(f"   PublishInput meta.slug: {publish_input.get('meta', {}).get('slug', 'MISSING')}")
        
        # 3. Publish script (jak je v retry endpointu)
        from activities.publish_script import publish_script
        result = publish_script(publish_input)
        print(f"✅ Publish script dokončen:")
        print(f"   Result success: {result.get('success', 'MISSING')}")
        
        if result.get('success'):
            data = result.get('data', {})
            meta = data.get('meta', {})
            print(f"   Final meta.title: {meta.get('title', 'MISSING')}")
            print(f"   Final meta.description: {meta.get('description', 'MISSING')[:100]}...")
            print(f"   Final meta.slug: {meta.get('slug', 'MISSING')}")
            
            # Kontrola na fallback hodnoty
            title = meta.get('title', '')
            slug = meta.get('slug', '')
            if 'článek bez názvu' in title.lower() or 'clanek-bez-nazvu' in slug.lower():
                print("❌ NALEZENY FALLBACK HODNOTY!")
                return False
            else:
                print("✅ Žádné fallback hodnoty!")
                return True
        else:
            print("❌ Publish script selhal")
            return False
            
    except Exception as e:
        print(f"❌ Chyba v testu: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔬 TEST RETRY FLOW S REÁLNÝMI SEO DATY")
    print("=" * 60)
    
    success = test_retry_flow()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 TEST PROŠEL! Flow funguje správně.")
    else:
        print("❌ TEST SELHAL! Problém v flow.")
    print("=" * 60)