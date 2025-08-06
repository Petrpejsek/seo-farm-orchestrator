#!/usr/bin/env python3
"""
FINÁLNÍ KOMPLETNÍ TEST CELÉHO FLOW
Ověří, že API vrací správná data s COMPLETED stages a bez placeholderů
"""
import requests
import json
import time

# Test parametry
WORKFLOW_ID = "assistant_pipeline_top_10_ai_2025_1754438666"
RUN_ID = "b0b909dc-cfd7-40a4-8425-062d32886f49"
BASE_URL = "http://localhost:8000"

def test_api_health():
    """Test že API je dostupné"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def test_workflow_result():
    """Test API workflow result endpoint"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/workflow-result/{WORKFLOW_ID}/{RUN_ID}",
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ API ERROR: Status {response.status_code}")
            return None
            
        return response.json()
    except Exception as e:
        print(f"❌ REQUEST ERROR: {e}")
        return None

def analyze_api_response(data):
    """Analyzuje API response"""
    print("🔍 FINÁLNÍ API RESPONSE ANALÝZA:")
    print("=" * 60)
    
    if not data:
        print("❌ Žádná data z API")
        return False
    
    # Základní struktura
    print(f"📊 Response keys: {list(data.keys())}")
    
    stages = data.get('stages', [])
    print(f"📊 Celkem stages: {len(stages)}")
    
    # Hledání PublishScript stages
    publish_stages = []
    for i, stage in enumerate(stages):
        stage_name = stage.get('stage', 'NO_STAGE')
        stage_status = stage.get('status', 'NO_STATUS')
        
        if 'publish' in stage_name.lower():
            publish_stages.append(stage)
            print(f"  ✅ PUBLISH STAGE [{i}]: {stage_name} = {stage_status}")
    
    print(f"\n📋 PUBLIKACE STAGES CELKEM: {len(publish_stages)}")
    
    # Analýza statusů
    completed_count = sum(1 for ps in publish_stages if ps.get('status') == 'COMPLETED')
    failed_count = sum(1 for ps in publish_stages if ps.get('status') == 'FAILED')
    
    print(f"\n📊 STAGE STATISTIKY:")
    print(f"  ✅ COMPLETED: {completed_count}")
    print(f"  ❌ FAILED: {failed_count}")
    
    # Test obsahu - kontrola placeholderů
    print(f"\n🔍 KONTROLA OBSAHU:")
    placeholders_found = False
    
    for stage in publish_stages:
        stage_output = stage.get('stage_output', '')
        if isinstance(stage_output, str):
            stage_output_str = stage_output
        else:
            stage_output_str = str(stage_output)
            
        # Hledání placeholderů
        if 'Článek bez názvu' in stage_output_str:
            print("  ❌ PLACEHOLDER: 'Článek bez názvu' nalezen!")
            placeholders_found = True
        if 'Kvalitní obsah pro čtenáře' in stage_output_str:
            print("  ❌ PLACEHOLDER: 'Kvalitní obsah pro čtenáře' nalezen!")
            placeholders_found = True
            
        # Hledání skutečného obsahu
        if 'Generativní AI v roce 2025' in stage_output_str:
            print("  ✅ SPRÁVNÝ OBSAH: 'Generativní AI v roce 2025' nalezen!")
        if '"meta"' in stage_output_str and '"title"' in stage_output_str:
            print("  ✅ METADATA: JSON struktura nalezena!")
    
    if not placeholders_found:
        print("  ✅ ŽÁDNÉ PLACEHOLDERS!")
    
    # Závěr
    success = (completed_count > 0 and failed_count == 0 and not placeholders_found)
    
    print(f"\n🎯 FINÁLNÍ VÝSLEDEK:")
    if success:
        print("  🎉 KOMPLETNÍ ÚSPĚCH! Vše funguje 100%!")
        print("  📋 API vrací COMPLETED stages bez placeholderů")
        print("  🔧 Problém může být pouze ve frontend cache")
    else:
        print("  ❌ PROBLÉMY STÁLE EXISTUJÍ:")
        if completed_count == 0:
            print("    - Žádné COMPLETED stages")
        if failed_count > 0:
            print(f"    - {failed_count} FAILED stages")
        if placeholders_found:
            print("    - Placeholders stále přítomny")
    
    return success

def main():
    print("🚀 SPOUŠTÍM FINÁLNÍ KOMPLETNÍ TEST")
    print("=" * 60)
    
    # Test 1: API health
    print("\n🔍 Test 1: API Health Check")
    if not test_api_health():
        print("❌ API není dostupné na localhost:8000")
        return
    print("✅ API je dostupné")
    
    # Test 2: Workflow result
    print("\n🔍 Test 2: Workflow Result API")
    data = test_workflow_result()
    
    if not data:
        print("❌ Nepodařilo se získat data z API")
        return
    
    # Test 3: Analýza response
    print("\n🔍 Test 3: Response Analysis")
    success = analyze_api_response(data)
    
    # Závěrečné doporučení
    print("\n🎯 DOPORUČENÍ:")
    if success:
        print("  1. Hard refresh frontendu (Ctrl+Shift+R)")
        print("  2. Vyčistit browser cache")
        print("  3. Restartovat frontend server")
        print("  4. Zkontrolovat console logy ve frontend")
    else:
        print("  1. Zkontrolovat backend logy")
        print("  2. Opakovat retry mechanismus")
        print("  3. Zkontrolovat databázový obsah")

if __name__ == '__main__':
    main()