#!/usr/bin/env python3

"""
Debug script pro testování LLM coroutine problému
"""

import asyncio
import sys
import os

# Přidáme root do sys.path
sys.path.insert(0, os.path.abspath('.'))

from backend.llm_clients.factory import LLMClientFactory

async def test_llm_coroutine_problem():
    """Test problému s coroutine v LLM volání"""
    
    # Nastavíme API_BASE_URL
    os.environ['API_BASE_URL'] = 'http://localhost:8000'
    
    try:
        print("🔧 Test 1: Vytvoření LLM client")
        llm_client = LLMClientFactory.create_client("openai")
        print(f"✅ LLM client vytvořen: {type(llm_client)}")
        
        print("🔧 Test 2: Získání chat_completion funkce")
        llm_func = llm_client.chat_completion
        print(f"✅ chat_completion func: {type(llm_func)}, {llm_func}")
        
        print("🔧 Test 3: Volání chat_completion s await")
        result = await llm_func(
            system_prompt="Jsi pomocník",
            user_message="Říkej ahoj",
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=50
        )
        
        print(f"✅ Výsledek typu: {type(result)}")
        
        print("🔧 Test 4: Kontrola 'content' in result")
        if "content" in result:
            print(f"✅ 'content' nalezen v result: {result['content'][:50]}...")
        else:
            print(f"❌ 'content' NENALEZEN v result: {result}")
            
    except Exception as e:
        print(f"❌ CHYBA: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm_coroutine_problem())