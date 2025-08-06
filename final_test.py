#!/usr/bin/env python3

print("=== FINÁLNÍ TEST VŠECH OPRAV ===")

from helpers.transformers import parse_seo_metadata, parse_qa_faq, parse_multimedia_primary_visuals

# Test SEO parser
seo_test = '''1. 🏷️ SEO Metadata

```plaintext
title: Test title
meta_description: Test description  
slug: test-slug
```

3. 🔑 Klíčová slova

- keyword1
- keyword2 
- keyword3
- keyword4
- keyword5'''

try:
    seo_result = parse_seo_metadata(seo_test)
    print(f'✅ SEO: title={bool(seo_result["title"])}, desc={bool(seo_result["description"])}, canonical={bool(seo_result["canonical"])}, keywords={len(seo_result["keywords"])}')
except Exception as e:
    print(f'❌ SEO: {e}')

# Test QA parser
qa_test = '''```json
{"faq": [{"question": "Q1?", "answer": "A1"}, {"question": "Q2?", "answer": "A2"}, {"question": "Q3?", "answer": "A3"}]}
```'''

try:
    qa_result = parse_qa_faq(qa_test)
    print(f'✅ QA: {len(qa_result)} FAQ items')
except Exception as e:
    print(f'❌ QA: {e}')

# Test Multimedia parser
mm_test = '''```json
{"primary_visuals": [{"type": "img1"}, {"type": "img2"}]}
```'''

try:
    mm_result = parse_multimedia_primary_visuals(mm_test)
    print(f'✅ Multimedia: {len(mm_result)} visuals')
except Exception as e:
    print(f'❌ Multimedia: {e}')

print("\n🏁 PARSERY KOMPLETNÍ!")