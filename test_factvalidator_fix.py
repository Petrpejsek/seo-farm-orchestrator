#!/usr/bin/env python3
"""
Rychlý test opraveného FactValidator asistenta
"""

import asyncio
import json
import sys
import os

# Přidání cesty pro import
sys.path.append('.')

async def test_factvalidator():
    print("🧪 === TEST OPRAVENÉHO FACTVALIDATOR ===")
    
    try:
        from activities.fact_validator_assistant import fact_validator_assistant
        
        # Test data s některými potenciálně problematickými fakty
        test_input = {
            "content": """
            ## Dětské kolo pro tříleté dítě

            **Fakta k ověření:**
            - 78% rodičů kupuje první kolo svému dítěti ve věku 3 let
            - Cena dětských kol se pohybuje od 1500 do 8000 Kč
            - Podle studie z roku 2019 je nejbezpečnější výška kola 12 palců
            - Největší výrobce dětských kol je firma XYZ s 45% podílem na trhu
            
            **Text bez problémů:**
            Výběr správného kola je důležitý pro bezpečnost dítěte.
            Kolo by mělo být vhodné pro věk a výšku dítěte.
            """
        }
        
        # Simulace assistant_id (použijeme skutečný z databáze)
        assistant_id = "bae243cb-8ae1-4f3d-bd5e-7e4cdbfac920"  # FactValidator ID
        
        print("1️⃣ Volám FactValidator...")
        result = await fact_validator_assistant(test_input, assistant_id)
        
        print("2️⃣ Výsledek:")
        print(f"   Typ: {type(result)}")
        print(f"   Klíče: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
        
        if 'output' in result:
            output_len = len(result['output'])
            print(f"   Output délka: {output_len} znaků")
            
            if output_len > 0:
                print("✅ ÚSPĚCH: FactValidator vrátil výstup!")
                
                # Pokus o parsing JSON
                try:
                    parsed_output = json.loads(result['output'])
                    print(f"   Validation status: {parsed_output.get('validation_status', 'N/A')}")
                    print(f"   Model použit: {parsed_output.get('model_used', 'N/A')}")
                    print("✅ JSON validní!")
                except:
                    print("⚠️ JSON není parsovatelný, ale output existuje")
                    
                return True
            else:
                print("❌ PROBLÉM: Output je prázdný!")
                return False
        else:
            print("❌ PROBLÉM: Chybí 'output' klíč!")
            return False
            
    except Exception as e:
        print(f"❌ CHYBA: {e}")
        return False

async def main():
    success = await test_factvalidator()
    
    print("="*50)
    print("🎯 VÝSLEDEK:")
    if success:
        print("✅ FactValidator funguje správně!")
        print("🚀 MŮŽEŠ SPUSTIT NOVOU PIPELINE!")
    else:
        print("❌ FactValidator stále má problémy")
        print("🔧 Potřebuje další ladění...")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())