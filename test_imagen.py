#!/usr/bin/env python3
"""Quick test for Imagen-4"""

import asyncio
import sys
import os
sys.path.append('.')

async def quick_test():
    from backend.llm_clients.gemini_client import GeminiClient
    
    print("🔧 TESTING IMAGEN-4 DIRECTLY...")
    
    from backend.llm_clients.factory import LLMClientFactory
    client = LLMClientFactory.create_client('gemini')
    
    try:
        result = await client.image_generation(
            prompt="A simple blue circle on white background",
            model="imagen-4"
        )
        
        print("✅ IMAGEN-4 WORKS!")
        print(f"Result type: {type(result)}")
        print(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not dict'}")
        
    except Exception as e:
        print(f"❌ IMAGEN-4 FAILED: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(quick_test())