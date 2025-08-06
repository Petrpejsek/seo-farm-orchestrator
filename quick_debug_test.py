#!/usr/bin/env python3
"""
🚀 QUICK DEBUG TEST
===================

Rychlý test pro diagnostiku problémů před spuštěním workflow:
- Database connectivity
- Service health
- Basic functionality
"""

import os
import sys
import time
import asyncio
from debug_test_runner import run_quick_database_check
from helpers.db_connection_audit import get_connection_stats
from helpers.db_activity_monitor import create_monitored_connection

print("🔍 === QUICK DEBUGGING TEST ===")
print()

# 1. Basic database test
print("1️⃣ Testing database connectivity...")
try:
    conn = create_monitored_connection()
    cursor = conn.execute("SELECT COUNT(*) as count FROM assistants")
    result = cursor.fetchone()
    assistants_count = result[0] if result else 0
    conn.close()
    
    print(f"✅ Database OK: {assistants_count} assistants found")
except Exception as e:
    print(f"❌ Database ERROR: {e}")
    sys.exit(1)

# 2. Check ImageRenderer config
print("\n2️⃣ Checking ImageRenderer configuration...")
try:
    conn = create_monitored_connection()
    cursor = conn.execute("SELECT name, model_provider, model FROM assistants WHERE functionKey='image_renderer_assistant'")
    result = cursor.fetchone()
    conn.close()
    
    if result:
        name, provider, model = result
        print(f"✅ ImageRenderer OK: {name} using {provider}/{model}")
    else:
        print("❌ ImageRenderer NOT FOUND in database")
except Exception as e:
    print(f"❌ ImageRenderer check ERROR: {e}")

# 3. Check Temporal connection
print("\n3️⃣ Testing Temporal connectivity...")
try:
    import subprocess
    result = subprocess.run(["curl", "-s", "http://localhost:7233/health"], 
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print("✅ Temporal server OK")
    else:
        print("❌ Temporal server NOT RESPONDING")
except Exception as e:
    print(f"⚠️ Temporal check WARNING: {e}")

# 4. Check backend API
print("\n4️⃣ Testing backend API...")
try:
    import subprocess
    result = subprocess.run(["curl", "-s", "http://localhost:8000/health"], 
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0 and "healthy" in result.stdout:
        print("✅ Backend API OK")
    else:
        print("❌ Backend API NOT RESPONDING")
except Exception as e:
    print(f"❌ Backend API ERROR: {e}")

# 5. Quick database health check
print("\n5️⃣ Running database health check...")
try:
    async def health_check():
        return await run_quick_database_check()
    
    health_report = asyncio.run(health_check())
    health_status = health_report.get("overall_health", "UNKNOWN")
    
    if health_status == "HEALTHY":
        print("✅ Database health OK")
    elif health_status == "WARNING":
        print("⚠️ Database health WARNING - check connection audit")
    else:
        print("❌ Database health ERROR")
        
except Exception as e:
    print(f"❌ Health check ERROR: {e}")

print("\n" + "="*50)
print("🎯 QUICK TEST SUMMARY:")
print("- Run this script before starting workflows")
print("- All checks should show ✅ for best results")
print("- For detailed debugging, use: python debug_test_runner.py --test all")
print("="*50)