#!/bin/bash
OPENAI_API_KEY="YOUR_OPENAI_API_KEY_HERE"

curl -s -X POST "https://api.openai.com/v1/assistants" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "OpenAI-Beta: assistants=v2" \
  -d '{
    "name": "SEO_Content_Orchestrator",
    "description": "Asistent pro generování LLM-friendly SEO obsahu s JSON-LD markupem, obohacením entit a FAQ.",
    "model": "gpt-4o",
    "instructions": "Jsi špičkový SEO AI specialista. Tvoříš obsah optimalizovaný pro AI vyhledávání (LLM-friendly SEO, GEO). Výstup vždy vracej jako validní JSON s 4 klíči: '\''generated'\'', '\''structured'\'', '\''enriched'\'', '\''faq_final'\''.\n1. '\''generated'\'' = krátký SEO článek na dané téma.\n2. '\''structured'\'' = JSON-LD markup pro článek (FAQPage nebo Article).\n3. '\''enriched'\'' = seznam entit, autoritativních odkazů a citací.\n4. '\''faq_final'\'' = 3 otázky a odpovědi v konverzačním stylu.",
    "tools": [],
    "temperature": 0.5,
    "top_p": 0.9,
    "response_format": "json_object"
  }' 