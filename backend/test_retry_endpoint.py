#!/usr/bin/env python3
"""
🧪 TEST RETRY ENDPOINT
Jednoduchý test endpoint pro retry publish script
"""

from fastapi import FastAPI, HTTPException
import json
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

app = FastAPI()

@app.post("/api/test-retry-publish")
async def test_retry_publish(request: dict):
    """Test retry endpoint s mock daty"""
    
    try:
        print("🧪 TEST RETRY PUBLISH - S FUNKČNÍMI DATY")
        print("=" * 50)
        
        # Mock funkční data
        components = {
            "seo_assistant_output": json.dumps({
                "seo_metadata": {
                    "title": "Test článek o fotovoltaice",
                    "meta_description": "Test popis článku o fotovoltaice.",
                    "slug": "test-clanek-fotovoltaika"
                },
                "headings": {
                    "h1": "Test článek o fotovoltaice",
                    "h2": ["Úvod", "Hlavní část"],
                    "h3": ["Detail 1", "Detail 2"]
                },
                "keywords": ["fotovoltaika", "test", "článek", "energie", "panely"]
            }),
            "humanizer_assistant_output": """<article>
<h1>Test článek o fotovoltaice</h1>
<p>Toto je testovací článek o fotovoltaických systémech.</p>
<h2>Úvod</h2>
<p>Fotovoltaika je důležitou součástí obnovitelných zdrojů energie.</p>
</article>""",
            "qa_assistant_output": json.dumps([
                {"question": "Co je fotovoltaika?", "answer": "Technologie pro výrobu elektřiny ze slunce."},
                {"question": "Jaké jsou výhody?", "answer": "Čistá energie a úspora nákladů."},
                {"question": "Kolik to stojí?", "answer": "Cena závisí na velikosti systému."}
            ]),
            "multimedia_assistant_output": json.dumps({
                "primary_visuals": [
                    {"type": "image", "prompt": "Fotovoltaické panely", "placement": "top", "alt_text": "Solární panely"},
                    {"type": "image", "prompt": "Instalace FV", "placement": "middle", "alt_text": "Instalace panelů"}
                ]
            }),
            "current_date": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }
        
        print(f"📊 Components připraveny: {list(components.keys())}")
        
        # Import a test transform_to_PublishInput
        from helpers.transformers import transform_to_PublishInput
        from activities.publish_script import publish_script
        
        print("🔧 Transformuji data...")
        publish_input = transform_to_PublishInput(components)
        
        print("🔧 Spouštím publish_script...")
        result = publish_script(publish_input)
        
        print(f"✅ ÚSPĚCH! Výsledek: {result}")
        
        return {
            "status": "success",
            "message": "Test retry publish úspěšný",
            "result": result
        }
        
    except Exception as e:
        print(f"❌ CHYBA: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Test retry error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)