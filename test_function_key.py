#!/usr/bin/env python3

"""
Testuje pouze logiku function_key bez Temporal
"""

def test_function_key():
    """Test pouze function_key logiky"""
    
    # Simulace hodnot z runtime
    function_key = "publish_assistant"
    topic = {
        "draft_assistant": "Test article content", 
        "seo_assistant": "Test SEO metadata"
    }
    
    print(f"🔍 DEBUG: function_key='{function_key}', type={type(function_key)}, len={len(str(function_key))}")
    print(f"🔍 KONTROLA: function_key == 'publish_assistant' ? {function_key == 'publish_assistant'}")
    print(f"🔍 TOPIC: {type(topic)} = {topic}")
    
    # Simulace původní logiky
    if function_key == "publish_assistant":
        # PublishAssistant potřebuje zachovat dictionary format
        if not isinstance(topic, dict):
            print(f"⚠️ PublishAssistant očekává dict, dostal {type(topic).__name__}")
            topic = {"content": str(topic)}
        print(f"🎯 PublishAssistant dostává dictionary s {len(topic)} klíči")
    else:
        # Ostatní asistenti potřebují string
        if isinstance(topic, dict):
            # Pokud je dict, vezmi "output" klíč nebo celý JSON
            import json
            topic = topic.get("output", json.dumps(topic, ensure_ascii=False))
            print(f"🔄 Topic je dict - převádím na string ({len(str(topic))} chars)")
        elif not isinstance(topic, str):
            topic = str(topic)
            print(f"🔄 Topic není string - převádím ({type(topic).__name__} -> str)")
    
    print(f"🎯 FINAL TOPIC: {type(topic)} = {str(topic)[:100]}...")

if __name__ == "__main__":
    test_function_key()