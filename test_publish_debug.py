#!/usr/bin/env python3

"""
Testuje PublishAssistant s debug logy
"""

import asyncio
import sys
import os

# Přidáme root do sys.path
sys.path.insert(0, os.path.abspath('.'))

from activities.safe_assistant_activities import execute_assistant

async def test_publish_assistant():
    """Test PublishAssistant s debug informacemi"""
    
    # Mock assistant config pro PublishAssistant
    assistant_config = {
        "name": "PublishAssistant",
        "function_key": "publish_assistant",
        "model_provider": "openai", 
        "model": "gpt-4o",
        "temperature": 0.3,
        "top_p": 0.9,
        "max_tokens": -1,
        "system_prompt": "Test system prompt"
    }
    
    # Mock topic jako dictionary (jak by to mělo být z workflow)
    topic = {
        "draft_assistant": "Test article content",
        "seo_assistant": "Test SEO metadata",
        "humanizer_assistant": "Test humanized content"
    }
    
    # Mock args
    args = {
        "assistant_config": assistant_config,
        "topic": topic,
        "current_date": "03. 08. 2025",
        "previous_outputs": {}
    }
    
    print("🔍 DIRECT TEST: PublishAssistant debug")
    print(f"Assistant config: {assistant_config}")
    print(f"Topic type: {type(topic)}")
    print(f"Topic: {topic}")
    
    try:
        result = await execute_assistant(args)
        print(f"✅ Result: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_publish_assistant())