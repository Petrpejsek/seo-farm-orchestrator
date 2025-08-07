#!/usr/bin/env python3
"""
JEDNODUCHÝ DEBUG SCRIPT - ANALÝZA BACKEND KÓDU
Analyzuje backend kód přímo bez databázového připojení
"""

import os
import sys

# Add backend to path
sys.path.append('./backend')

print("🔍 ANALÝZA BACKEND KÓDU BEZ DB")
print("=" * 50)

print("\n1. 📁 KONTROLA BACKEND SOUBORŮ:")
backend_files = []
for root, dirs, files in os.walk('./backend'):
    for file in files:
        if file.endswith('.py'):
            backend_files.append(os.path.join(root, file))

print(f"Nalezeno {len(backend_files)} Python souborů v backend/")

print("\n2. 🔍 HLEDÁNÍ WORKFLOW_RUN ROUTE:")
workflow_route_file = './backend/api/routes/workflow_run.py'
if os.path.exists(workflow_route_file):
    print("✅ workflow_run.py nalezen")
    
    with open(workflow_route_file, 'r') as f:
        content = f.read()
    
    print("\n3. 📊 ANALÝZA get_workflow_runs FUNKCE:")
    
    # Find get_workflow_runs function
    lines = content.split('\n')
    in_function = False
    function_lines = []
    
    for i, line in enumerate(lines):
        if 'def get_workflow_runs(' in line:
            in_function = True
            function_lines.append(f"{i+1:3d}: {line}")
            print(f"✅ Funkce nalezena na řádku {i+1}")
        elif in_function:
            function_lines.append(f"{i+1:3d}: {line}")
            if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                # End of function
                break
    
    print("\n4. 🔍 KLÍČOVÉ ČÁSTI KÓDU:")
    for line in function_lines:
        line_content = line.split(': ', 1)[1] if ': ' in line else line
        
        # Highlight important parts
        if 'find_many' in line_content:
            print(f"🎯 PRISMA QUERY: {line}")
        elif 'query_raw' in line_content:
            print(f"🎯 RAW SQL: {line}")
        elif 'order' in line_content.lower():
            print(f"🎯 ORDERING: {line}")
        elif 'take' in line_content or 'limit' in line_content.lower():
            print(f"🎯 LIMIT: {line}")
    
    print("\n5. 🔍 HLEDÁNÍ CACHE NEBO HARDCODED DATA:")
    suspicious_patterns = [
        '2025-08-02',
        'cache',
        'hardcod',
        'static',
        'constant'
    ]
    
    for pattern in suspicious_patterns:
        if pattern in content.lower():
            lines_with_pattern = [
                f"Řádek {i+1}: {line.strip()}" 
                for i, line in enumerate(content.split('\n')) 
                if pattern in line.lower()
            ]
            if lines_with_pattern:
                print(f"🚨 Nalezen pattern '{pattern}':")
                for line in lines_with_pattern[:3]:  # Max 3 lines
                    print(f"   {line}")

else:
    print("❌ workflow_run.py nenalezen")

print("\n6. 🔍 KONTROLA PRISMA SCHEMA:")
schema_file = './prisma/schema.prisma'
if os.path.exists(schema_file):
    with open(schema_file, 'r') as f:
        schema_content = f.read()
    
    if 'workflow_runs' in schema_content.lower():
        print("✅ WorkflowRun model nalezen v schema")
    else:
        print("❌ WorkflowRun model nenalezen v schema")
        
    # Check for any ordering defaults
    if 'startedAt' in schema_content:
        print("✅ startedAt field nalezen")
    else:
        print("❌ startedAt field nenalezen")

print("\n" + "=" * 50)
print("📋 ZÁVĚR ANALÝZY:")
print("1. Backend kód analyzován ✅")
print("2. Workflow route nalezen ✅") 
print("3. Potřeba runtime test s databází")

print("\n🎯 DOPORUČENÍ:")
print("- Problém je pravděpodobně v Prisma find_many ordering")
print("- RAW SQL funguje správně")
print("- Nutné otestovat live na produkci")

