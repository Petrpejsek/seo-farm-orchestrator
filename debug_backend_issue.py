#!/usr/bin/env python3
"""
HLOUBKOVÁ DIAGNOSTIKA BACKEND API vs DATABASE PROBLÉMU
Tento script reprodukuje problém kde backend API vrací stará data
zatímco databáze má nejnovější data.
"""

import asyncio
import os
import sys
from datetime import datetime
import json

# Add backend to path
sys.path.append('./backend')

async def test_backend_vs_database():
    """Test Backend API vs Direct Database comparison"""
    
    print("🔍 HLOUBKOVÁ DIAGNOSTIKA BACKEND PROBLÉMU")
    print("=" * 60)
    
    # Test 1: Import backend modules
    print("\n1. 📦 IMPORT BACKEND MODULES:")
    try:
        from backend.api.database import get_prisma_client
        print("✅ Backend database module imported")
        
        from backend.api.routes.workflow_run import get_workflow_runs
        print("✅ Workflow run routes imported")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return
    
    # Test 2: Database connection
    print("\n2. 🔌 DATABÁZE CONNECTION TEST:")
    try:
        prisma = await get_prisma_client()
        print("✅ Prisma client connected")
        
        # Test raw query
        raw_result = await prisma.query_raw(
            'SELECT COUNT(*) as count FROM workflow_runs'
        )
        total_count = raw_result[0]['count'] if raw_result else 0
        print(f"✅ Total workflows in DB: {total_count}")
        
        # Test nejnovější workflow
        latest_raw = await prisma.query_raw(
            'SELECT topic, "startedAt" FROM workflow_runs ORDER BY "startedAt" DESC LIMIT 1'
        )
        if latest_raw:
            latest = latest_raw[0]
            print(f"✅ Nejnovější workflow: {latest['topic'][:50]}... ({latest['startedAt']})")
        
        await prisma.disconnect()
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return
    
    # Test 3: Backend API simulation
    print("\n3. 🔌 BACKEND API SIMULATION:")
    try:
        # Simulate API call using the same code as backend
        prisma = await get_prisma_client()
        
        # Test 1: Prisma find_many (původní problémová metoda)
        print("\n   a) Prisma find_many test:")
        workflows_prisma = await prisma.workflowrun.find_many(
            take=3,
            order={"startedAt": "desc"},
            include={"project": True}
        )
        print(f"      Prisma find_many vrací: {len(workflows_prisma)} workflows")
        if workflows_prisma:
            latest_prisma = workflows_prisma[0]
            print(f"      Nejnovější z Prisma: {latest_prisma.topic[:50]}... ({latest_prisma.startedAt})")
        
        # Test 2: Raw SQL (naše oprava)
        print("\n   b) Raw SQL test:")
        workflows_raw = await prisma.query_raw(
            '''
            SELECT wr.*, p.name as project_name
            FROM workflow_runs wr
            LEFT JOIN projects p ON wr."projectId" = p.id
            ORDER BY wr."startedAt" DESC
            LIMIT 3
            '''
        )
        print(f"      Raw SQL vrací: {len(workflows_raw)} workflows")
        if workflows_raw:
            latest_raw = workflows_raw[0]
            print(f"      Nejnovější z Raw SQL: {latest_raw['topic'][:50]}... ({latest_raw['startedAt']})")
        
        await prisma.disconnect()
        
    except Exception as e:
        print(f"❌ Backend API simulation error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Comparison
    print("\n4. 📊 POROVNÁNÍ VÝSLEDKŮ:")
    print("-" * 40)
    
    if 'latest_prisma' in locals() and 'latest_raw' in locals():
        prisma_date = latest_prisma.startedAt if hasattr(latest_prisma, 'startedAt') else 'N/A'
        raw_date = latest_raw['startedAt'] if 'startedAt' in latest_raw else 'N/A'
        
        print(f"Prisma find_many: {prisma_date}")
        print(f"Raw SQL:          {raw_date}")
        
        if str(prisma_date) != str(raw_date):
            print("🚨 ROZDÍL NALEZEN! Prisma find_many vrací jiná data než Raw SQL")
            print("🎯 PŘÍČINA PROBLÉMU: Prisma find_many má problém s ordering nebo cache")
        else:
            print("✅ Oba přístupy vrací stejná data")
    
    print("\n" + "=" * 60)
    print("🔍 DIAGNOSTIKA DOKONČENA")

if __name__ == "__main__":
    # Set environment for local testing
    os.environ['DATABASE_URL'] = 'postgresql://postgres:@localhost:5432/seo_farm'
    
    try:
        asyncio.run(test_backend_vs_database())
    except KeyboardInterrupt:
        print("\n❌ Test přerušen uživatelem")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

