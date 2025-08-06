#!/usr/bin/env python3
"""
KRITICKÝ DEBUG - Najít proč retry je successful ale API vrací FAILED
"""
import asyncio
import sys
import os
import json
import time

# Nastavení environment pro databázi
os.environ['DATABASE_URL'] = 'postgresql://seo_user:silne-heslo@91.99.210.104:5432/seo_farm'
sys.path.append('/Users/petrliesner/Farm new new new/backend')

async def critical_debug():
    from api.database import get_prisma_client
    
    print('🚨 KRITICKÝ DEBUG: Retry vs API inconsistency')
    print('=' * 70)
    
    try:
        prisma = await get_prisma_client()
        
        # Workflow info
        workflow_id = 'assistant_pipeline_top_10_ai_2025_1754438666'
        run_id = 'b0b909dc-cfd7-40a4-8425-062d32886f49'
        
        print(f'🔍 Hledám workflow: {workflow_id}')
        print(f'🔍 Run ID: {run_id}')
        
        # Najdi workflow v databázi
        workflow = await prisma.workflowrun.find_unique(
            where={
                'workflowId_runId': {
                    'workflowId': workflow_id,
                    'runId': run_id
                }
            }
        )
        
        if not workflow:
            print('❌ Workflow nenalezen v databázi!')
            return
            
        print(f'\n✅ Workflow nalezen v DB:')
        print(f'   ID: {workflow.id}')
        print(f'   Status: {workflow.status}')
        print(f'   resultJson exists: {bool(workflow.resultJson)}')
        
        if workflow.resultJson:
            print(f'   resultJson length: {len(workflow.resultJson)} chars')
            
            # Parse JSON
            try:
                data = json.loads(workflow.resultJson)
                
                print(f'\n📊 JSON STRUKTURA:')
                print(f'   Keys: {list(data.keys())}')
                
                stages = data.get('stages', [])
                print(f'   Stages count: {len(stages)}')
                
                # Najdi PublishScript stages
                publish_stages = []
                for i, stage in enumerate(stages):
                    stage_name = stage.get('stage', 'NO_STAGE')
                    stage_status = stage.get('status', 'NO_STATUS')
                    
                    if 'publish' in stage_name.lower():
                        publish_stages.append((i, stage_name, stage_status))
                        print(f'   📋 Stage [{i}]: {stage_name} = {stage_status}')
                
                print(f'\n🎯 PUBLISH STAGES CELKEM: {len(publish_stages)}')
                
                # Analýza statusů
                completed_count = sum(1 for _, _, status in publish_stages if status == 'COMPLETED')
                failed_count = sum(1 for _, _, status in publish_stages if status == 'FAILED')
                started_count = sum(1 for _, _, status in publish_stages if status == 'STARTED')
                
                print(f'   ✅ COMPLETED: {completed_count}')
                print(f'   🔄 STARTED: {started_count}')
                print(f'   ❌ FAILED: {failed_count}')
                
                # Časové razítko posledního update
                if hasattr(workflow, 'updatedAt'):
                    print(f'\n⏰ Last updated: {workflow.updatedAt}')
                
                # Test API consistency
                print(f'\n🌐 TEST API KONZISTENCE:')
                import requests
                api_url = f'http://localhost:8000/api/workflow-result/{workflow_id}/{run_id}'
                
                try:
                    response = requests.get(api_url, timeout=10)
                    if response.status_code == 200:
                        api_data = response.json()
                        api_stages = api_data.get('stages', [])
                        api_publish_stages = [s for s in api_stages if 'publish' in s.get('stage', '').lower()]
                        
                        print(f'   API stages count: {len(api_stages)}')
                        print(f'   API publish stages: {len(api_publish_stages)}')
                        
                        for i, ps in enumerate(api_publish_stages):
                            print(f'   API Stage [{i}]: {ps.get("stage")} = {ps.get("status")}')
                        
                        # Porovnání
                        if len(publish_stages) == len(api_publish_stages):
                            db_statuses = [status for _, _, status in publish_stages]
                            api_statuses = [ps.get('status') for ps in api_publish_stages]
                            
                            if db_statuses == api_statuses:
                                print('   ✅ DB a API jsou SYNCHRONNÍ')
                            else:
                                print('   🚨 DB a API NEJSOU SYNCHRONNÍ!')
                                print(f'      DB statuses: {db_statuses}')
                                print(f'      API statuses: {api_statuses}')
                        else:
                            print('   🚨 RŮZNÝ POČET STAGES mezi DB a API!')
                    else:
                        print(f'   ❌ API ERROR: {response.status_code}')
                except Exception as e:
                    print(f'   ❌ API REQUEST FAILED: {e}')
                
                # Závěr
                print(f'\n🎯 ZÁVĚR:')
                if completed_count > 0 and failed_count == 0:
                    print('   🎉 DATABASE obsahuje COMPLETED stages!')
                    print('   🔧 Problém je pravděpodobně v API čtení nebo cache')
                elif failed_count > 0:
                    print('   ❌ DATABASE obsahuje FAILED stages')
                    print('   🔧 Retry neukládá správně nebo se rollbackuje')
                else:
                    print('   🤔 Nejasný stav - žádné publish stages?')
                    
            except json.JSONDecodeError as e:
                print(f'❌ JSON parsing error: {e}')
        else:
            print('❌ resultJson is NULL nebo empty')
            
    except Exception as e:
        print(f'❌ Critical error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(critical_debug())