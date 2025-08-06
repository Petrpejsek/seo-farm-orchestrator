#!/usr/bin/env python3
"""
Test transformace dat ze stage_logs na publish_input
"""

import json
import sys
import os
from datetime import datetime, timezone

sys.path.append(os.getcwd())

def test_data_transformation():
    """Test transformace dat ze starých pipeline logs"""
    
    print("🔧 TESTOVÁNÍ TRANSFORMACE DAT")
    print("=" * 50)
    
    # Simulace dat ze staré pipeline (problematická data)
    old_pipeline_data = {
        "stage_logs": [
            {
                "stage": "seo_assistant",
                "status": "COMPLETED",
                "output": """{
  "seo_metadata": {
    "title": "Jak vybrat spolehlivou firmu na fotovoltaiku v roce 2025",
    "meta_description": "Naučte se, jak vybrat spolehlivou firmu na fotovoltaiku. Přehled kritérií, certifikací a záruk pro efektivní investici.",
    "slug": "jak-vybrat-firmu-na-fotovoltaiku-2025"
  },
  "headings": {
    "h1": "Jak vybrat spolehlivou firmu na fotovoltaiku v roce 2025",
    "h2": [
      "Základní kritéria pro výběr firmy na fotovoltaiku",
      "Ověření důvěryhodnosti a historie firmy"
    ],
    "h3": [
      "Oprávnění a certifikace",
      "Členství v profesních organizacích"
    ]
  },
  "keywords": [
    "fotovoltaika"
  ]
}"""
            },
            {
                "stage": "humanizer_assistant",
                "status": "COMPLETED",
                "output": """<article><h1>Test</h1><p>Content</p></article>"""
            },
            {
                "stage": "qa_assistant", 
                "status": "COMPLETED",
                "output": """[{"question": "Test?", "answer": "Odpověď"}]"""
            },
            {
                "stage": "multimedia_assistant",
                "status": "COMPLETED", 
                "output": """{"primary_visuals": [{"type": "image", "prompt": "test", "placement": "top", "alt_text": "test"}]}"""
            }
        ]
    }
    
    # Extrakce dat ze stage_logs (jako v backend retry kódu)
    components = {
        "seo_assistant_output": "",
        "humanizer_assistant_output": "",
        "qa_assistant_output": "",
        "multimedia_assistant_output": "",
        "current_date": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }
    
    stage_logs = old_pipeline_data.get("stage_logs", [])
    
    for log in stage_logs:
        stage_name = log.get("stage", "")
        output = log.get("output", "")
        
        if stage_name and output:
            if "seo" in stage_name.lower():
                components["seo_assistant_output"] = output
                print(f"✅ SEO output: {len(str(output))} znaků")
            elif "humanizer" in stage_name.lower():
                components["humanizer_assistant_output"] = output
                print(f"✅ Humanizer output: {len(str(output))} znaků")
            elif "qa" in stage_name.lower():
                components["qa_assistant_output"] = output
                print(f"✅ QA output: {len(str(output))} znaků")
            elif "multimedia" in stage_name.lower():
                components["multimedia_assistant_output"] = output
                print(f"✅ Multimedia output: {len(str(output))} znaků")
    
    print(f"\n📊 Extraktované komponenty: {list(components.keys())}")
    
    # Test transform_to_PublishInput
    try:
        from helpers.transformers import transform_to_PublishInput
        
        print("\n🔧 Testování transform_to_PublishInput...")
        publish_input = transform_to_PublishInput(components)
        print(f"✅ Transformace úspěšná!")
        print(f"📊 Publish input keys: {list(publish_input.keys())}")
        
        # Test publish_script 
        from activities.publish_script import publish_script
        
        print("\n🔧 Testování publish_script...")
        result = publish_script(publish_input)
        print(f"✅ PUBLISH SCRIPT ÚSPĚŠNÝ!")
        print(f"📊 Výsledek: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ CHYBA: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_data_transformation()