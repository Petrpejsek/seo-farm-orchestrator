import os
import logging
from typing import Optional, Tuple
from temporalio.client import Client
from dotenv import load_dotenv

# Načtení environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def extract_topic_from_workflow_id(workflow_id: str) -> str:
    """
    Extrahuje lidsky čitelné téma z workflow ID.
    
    Převede např.:
    'seo_pipeline_ma_jeste_cenu_si_porizovat_fotovoltaiku?_1753811442'
    na:
    'Má ještě cenu si pořizovat fotovoltaiku?'
    """
    try:
        # Odebereme known prefixy
        topic = workflow_id
        for prefix in ["seo_pipeline_", "assistant_pipeline_"]:
            if topic.startswith(prefix):
                topic = topic[len(prefix):]
                break
        
        # Odebereme timestamp suffix (poslední _číslo)
        import re
        topic = re.sub(r'_\d+$', '', topic)
        
        # Nahradíme podtržítka mezerami
        topic = topic.replace('_', ' ')
        
        # Nahradíme pomlčky mezerami (pro některé workflow ID)
        topic = topic.replace(' - ', ' ')
        
        # Vyčistíme duplicitní mezery
        topic = ' '.join(topic.split())
        
        # Uděláme první písmeno velké
        if topic:
            topic = topic[0].upper() + topic[1:]
        
        # Fallback pokud je prázdné
        if not topic.strip():
            topic = f"Workflow {workflow_id}"
            
        return topic
        
    except Exception as e:
        logger.warning(f"⚠️ Nelze extrahovat topic z workflow_id '{workflow_id}': {str(e)}")
        return f"Workflow {workflow_id}"

async def start_seo_pipeline(topic: str, project_id: Optional[str] = None, csv_base64: Optional[str] = None) -> Tuple[str, str]:
    """
    Spustí SEO pipeline workflow přes Temporal klienta s podporou asistentů z databáze.
    
    Args:
        topic: Téma pro SEO zpracování
        project_id: ID projektu pro načtení asistentů z databáze
        csv_base64: Volitelný CSV obsah v Base64 formátu
        
    Returns:
        Tuple[workflow_id, run_id]
        
    Raises:
        Exception: Pokud chybí připojení k Temporal serveru
    """
    try:
        # Načtení konfigurace z ENV
        temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
        temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
        
        logger.info(f"🔧 Temporal konfigurace:")
        logger.info(f"   🌐 Host: {temporal_host}")
        logger.info(f"   📂 Namespace: {temporal_namespace}")
        logger.info(f"   📋 Topic: {topic}")
        logger.info(f"   🏗️ Project ID: {project_id}")
        logger.info(f"   📄 CSV: {'✅ Přiložen' if csv_base64 else '❌ Žádný'}")
        
        # Připojení k Temporal serveru
        logger.info("🔌 Navazuji spojení s Temporal serverem...")
        
        try:
            client = await Client.connect(temporal_host, namespace=temporal_namespace)
            logger.info("✅ Temporal client úspěšně připojen")
        except Exception as conn_error:
            logger.error(f"❌ Chyba připojení k Temporal serveru:")
            logger.error(f"   🌐 Host: {temporal_host}")
            logger.error(f"   📂 Namespace: {temporal_namespace}")
            logger.error(f"   🚨 Error: {str(conn_error)}")
            raise Exception(f"Nelze se připojit k Temporal serveru {temporal_host}: {str(conn_error)}")
        
        # Generování workflow ID
        safe_topic = topic.replace(' ', '_').replace('?', '').replace('!', '').lower()
        timestamp = int(__import__('time').time())
        
        # Rozhodnutí o typu workflow na základě dostupnosti project_id
        if project_id:
            workflow_type = "AssistantPipelineWorkflow"
            workflow_id = f"assistant_pipeline_{safe_topic}_{timestamp}"
            logger.info("🤖 Používám AssistantPipelineWorkflow s asistenty z databáze")
        else:
            workflow_type = "SEOWorkflow"
            workflow_id = f"seo_pipeline_{safe_topic}_{timestamp}"
            logger.info("⚙️ Používám fallback SEOWorkflow (bez project_id)")
        
        logger.info(f"🆔 Generuji workflow identifikátory:")
        logger.info(f"   📋 Původní topic: '{topic}'")
        logger.info(f"   🔗 Safe topic: '{safe_topic}'")
        logger.info(f"   ⏰ Timestamp: {timestamp}")
        logger.info(f"   🆔 Workflow ID: {workflow_id}")
        logger.info(f"   🎯 Workflow Type: {workflow_type}")
        
        # Příprava workflow parametrů
        logger.info("⚙️ Připravuji workflow parametry...")
        if csv_base64:
            logger.warning("⚠️ CSV soubor byl nahrán")
            logger.info(f"   📄 CSV délka: {len(csv_base64)} znaků")
        
        # Nastavení timeoutů
        run_timeout_minutes = 30  # Zvýšený timeout pro delší pipeline
        task_timeout_minutes = 5   # Zvýšený timeout pro jednotlivé asistenty
        
        logger.info(f"⏱️ Workflow timeouty:")
        logger.info(f"   🔄 Run timeout: {run_timeout_minutes} minut")
        logger.info(f"   📝 Task timeout: {task_timeout_minutes} minut")
        
        # Spuštění workflow podle typu
        logger.info("🚀 Spouštím workflow...")
        logger.info(f"   🎯 Target: {workflow_type}")
        logger.info(f"   🆔 ID: {workflow_id}")
        logger.info(f"   📥 Task queue: default")
        
        try:
            if project_id and workflow_type == "AssistantPipelineWorkflow":
                # Nový AssistantPipelineWorkflow s project_id
                logger.info(f"   📋 Arguments: topic='{topic}', project_id='{project_id}', csv_base64={bool(csv_base64)}")
                
                workflow_handle = await client.start_workflow(
                    "AssistantPipelineWorkflow",
                    args=[topic, project_id, csv_base64],
                    id=workflow_id,
                    task_queue="default",
                    run_timeout=__import__('datetime').timedelta(minutes=run_timeout_minutes),
                    task_timeout=__import__('datetime').timedelta(minutes=task_timeout_minutes)
                )
            else:
                # Fallback na starý SEOWorkflow
                logger.info(f"   📋 Arguments: topic='{topic}' (fallback)")
                
                workflow_handle = await client.start_workflow(
                    "SEOWorkflow",
                    topic,
                    id=workflow_id,
                    task_queue="default",
                    run_timeout=__import__('datetime').timedelta(minutes=run_timeout_minutes),
                    task_timeout=__import__('datetime').timedelta(minutes=task_timeout_minutes)
                )
            
            workflow_id = workflow_handle.id
            run_id = workflow_handle.result_run_id
            
            logger.info(f"🎉 Workflow úspěšně spuštěn!")
            logger.info(f"   🆔 Workflow ID: {workflow_id}")
            logger.info(f"   🏃 Run ID: {run_id}")
            logger.info(f"   🎯 Type: {workflow_type}")
            logger.info(f"   🔗 Handle type: {type(workflow_handle).__name__}")
            
            # Zkusíme získat základní informace o stavu workflow
            try:
                describe_result = await workflow_handle.describe()
                logger.info(f"📊 Workflow status po spuštění:")
                logger.info(f"   📈 Status: {describe_result.status}")
                logger.info(f"   ⏰ Start time: {describe_result.start_time}")
                logger.info(f"   🔄 Task queue: {describe_result.task_queue}")
            except Exception as describe_error:
                logger.warning(f"⚠️ Nelze získat stav workflow po spuštění: {str(describe_error)}")
            
            logger.info(f"✅ {workflow_type} byla úspěšně spuštěna pro téma: '{topic}'")
            
            return workflow_id, run_id
            
        except Exception as workflow_error:
            logger.error(f"❌ Chyba při spouštění workflow:")
            logger.error(f"   🎯 Workflow: {workflow_type}")
            logger.error(f"   📋 Topic: '{topic}'")
            logger.error(f"   🏗️ Project ID: {project_id}")
            logger.error(f"   🆔 ID: {workflow_id}")
            logger.error(f"   🚨 Error: {str(workflow_error)}")
            logger.error(f"   📝 Error type: {type(workflow_error).__name__}")
            raise Exception(f"Chyba při spuštění workflow {workflow_type}: {str(workflow_error)}")
        
    except Exception as e:
        logger.error(f"❌ Kritická chyba v start_seo_pipeline:")
        logger.error(f"   📋 Topic: '{topic}'")
        logger.error(f"   🏗️ Project ID: {project_id}")
        logger.error(f"   📄 CSV: {'✅ Přiložen' if csv_base64 else '❌ Žádný'}")
        logger.error(f"   🚨 Error: {str(e)}")
        logger.error(f"   📝 Error type: {type(e).__name__}")
        raise Exception(f"Nelze spustit SEO pipeline: {str(e)}")

async def list_workflows(limit: int = 30) -> list[dict]:
    """
    Načte seznam workflow executions z Temporal serveru.
    
    Args:
        limit: Maximální počet výsledků (default 30)
        
    Returns:
        List[dict] s workflow informacemi
        
    Raises:
        ConnectionError: Pokud se nelze připojit k Temporal serveru
        ValueError: Pokud jsou data z Temporal nesprávná
        Exception: Pro ostatní neočekávané chyby
    """
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    
    logger.info(f"🔌 Připojuji se k Temporal: {temporal_host}, namespace: {temporal_namespace}")
    
    try:
        # Připojení k Temporal serveru
        client = await Client.connect(temporal_host, namespace=temporal_namespace)
        logger.info("✅ Temporal client připojen")
        
        # Zkusíme nejdřív dotaz bez filtru pro debug
        workflows = []
        workflow_count = 0
        
        logger.info(f"🔍 Spouštím dotaz pro workflows...")
        
        try:
            # Dotaz na workflow executions - zkusíme bez query filtru nejdřív
            async for workflow in client.list_workflows():
                workflow_count += 1
                logger.info(f"📄 Workflow #{workflow_count}: {workflow.workflow_type} | ID: {workflow.id} | Status: {workflow.status}")
                
                # Přidáme do seznamu všechny workflows (ne pouze SEOWorkflow pro debug)
                try:
                    # Extrakce topic z workflow_id
                    topic = extract_topic_from_workflow_id(workflow.id)
                    
                    workflow_data = {
                        "id": workflow.run_id,  # Frontend očekává "id" 
                        "workflow_id": workflow.id,
                        "run_id": workflow.run_id, 
                        "topic": topic,  # ✅ Frontend očekává "topic"
                        "projectName": "Neznámý projekt",  # TODO: Načíst z databáze podle project_id
                        "status": workflow.status.name,
                        "workflow_type": getattr(workflow, 'workflow_type', 'unknown'),
                        "startedAt": workflow.start_time.isoformat() if workflow.start_time else None,  # ✅ Frontend očekává "startedAt"
                        "finishedAt": workflow.close_time.isoformat() if workflow.close_time else None,
                        "start_time": workflow.start_time.isoformat() if workflow.start_time else None,  # Backward compatibility
                        "end_time": workflow.close_time.isoformat() if workflow.close_time else None
                    }
                    workflows.append(workflow_data)
                except Exception as attr_error:
                    logger.warning(f"⚠️ Problém s workflow attributy: {attr_error}")
                    # Pokusíme se zachránit co je možné
                    topic = extract_topic_from_workflow_id(getattr(workflow, 'id', 'unknown'))
                    workflows.append({
                        "id": getattr(workflow, 'run_id', 'unknown'),
                        "workflow_id": getattr(workflow, 'id', 'unknown'),
                        "run_id": getattr(workflow, 'run_id', 'unknown'), 
                        "topic": topic,
                        "projectName": "Neznámý projekt",
                        "status": getattr(workflow, 'status', {}).get('name', 'unknown') if hasattr(workflow, 'status') else 'unknown',
                        "workflow_type": getattr(workflow, 'workflow_type', 'unknown'),
                        "startedAt": None,
                        "finishedAt": None,
                        "start_time": None,
                        "end_time": None
                    })
                
                # Omezení počtu výsledků
                if len(workflows) >= limit:
                    logger.info(f"🛑 Dosažen limit {limit} workflows")
                    break
                    
        except Exception as query_error:
            logger.error(f"❌ Chyba v dotazu na workflows: {query_error}")
            # Zkusíme to bez async iterace
            raise ValueError(f"Chyba při načítání workflow dat: {query_error}")
        
        logger.info(f"✅ Úspěšně načteno {len(workflows)} workflows z celkem {workflow_count} nalezených")
        return workflows
        
    except Exception as connect_error:
        if "connection" in str(connect_error).lower() or "refused" in str(connect_error).lower():
            logger.error(f"❌ Temporal connection error: {connect_error}")
            raise ConnectionError(f"Nelze se připojit k Temporal serveru na {temporal_host}: {connect_error}")
        else:
            logger.error(f"❌ Temporal unexpected error: {connect_error}")
            raise Exception(f"Neočekávaná chyba při práci s Temporal: {connect_error}")

async def get_workflow_result(workflow_id: str, run_id: str) -> dict:
    """
    Získá výsledek dokončeného workflow z Temporal serveru.
    
    Args:
        workflow_id: ID workflow
        run_id: Run ID workflow
        
    Returns:
        dict s workflow výsledkem a metadata
        
    Raises:
        ConnectionError: Pokud se nelze připojit k Temporal serveru
        ValueError: Pokud workflow není dokončen nebo neexistuje
        Exception: Pro ostatní neočekávané chyby
    """
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    
    logger.info(f"🔍 Načítám výsledek workflow: {workflow_id} (run: {run_id})")
    
    try:
        # Připojení k Temporal serveru
        client = await Client.connect(temporal_host, namespace=temporal_namespace)
        logger.info("✅ Temporal client připojen")
        
        # Získání workflow handle
        workflow_handle = client.get_workflow_handle(workflow_id=workflow_id, run_id=run_id)
        
        # Získání informací o workflow
        workflow_description = await workflow_handle.describe()
        status = workflow_description.status
        
        logger.info(f"📊 Workflow status: {status.name}")
        
        # Kontrola stavu workflow
        if status.name == "RUNNING":
            logger.info("⏳ Workflow stále běží - výsledek není dostupný")
            return {
                "status": "RUNNING",
                "message": "Workflow je stále spuštěn, výsledek ještě není k dispozici",
                "start_time": workflow_description.start_time.isoformat() if workflow_description.start_time else None,
                "end_time": None
            }
        elif status.name == "COMPLETED":
            try:
                result = await workflow_handle.result()
                logger.info(f"✅ Workflow výsledek načten: {type(result)}")
                
                # Extrakce stage_logs z výsledku pokud existují
                stage_logs = []
                if isinstance(result, dict) and "stage_logs" in result:
                    stage_logs = result["stage_logs"]
                    logger.info(f"📊 Stage logs nalezeny: {len(stage_logs)} záznamů")
                
                return {
                    "status": "COMPLETED",
                    "result": result,
                    "stage_logs": stage_logs,
                    "start_time": workflow_description.start_time.isoformat() if workflow_description.start_time else None,
                    "end_time": workflow_description.close_time.isoformat() if workflow_description.close_time else None
                }
            except Exception as result_error:
                logger.error(f"❌ Chyba při načítání výsledku: {result_error}")
                return {
                    "status": "COMPLETED",
                    "error": "Chyba při načítání výsledku workflow",
                    "details": str(result_error),
                    "stage_logs": [],
                    "start_time": workflow_description.start_time.isoformat() if workflow_description.start_time else None,
                    "end_time": workflow_description.close_time.isoformat() if workflow_description.close_time else None
                }
        elif status.name == "FAILED":
            logger.info("❌ Workflow selhal")
            
            # Pokusíme se získat detailní informace o chybě
            failure_info = None
            try:
                # Přístup k failure informacím
                if hasattr(workflow_description, 'failure') and workflow_description.failure:
                    failure = workflow_description.failure
                    failure_info = {
                        "message": getattr(failure, 'message', 'Unknown failure'),
                        "type": getattr(failure, 'failure_info', {}).get('type', 'Unknown'),
                        "stack_trace": getattr(failure, 'stack_trace', None)
                    }
                    logger.error(f"💥 Failure details: {failure_info['message']}")
            except Exception as failure_error:
                logger.warning(f"⚠️ Nelze získat detaily chyby: {failure_error}")
            
            return {
                "status": "FAILED",
                "message": "Workflow skončil chybou",
                "failure_details": failure_info,
                "start_time": workflow_description.start_time.isoformat() if workflow_description.start_time else None,
                "end_time": workflow_description.close_time.isoformat() if workflow_description.close_time else None
            }
        else:
            logger.info(f"⚠️ Neočekávaný status: {status.name}")
            return {
                "status": status.name,
                "message": f"Workflow je ve stavu {status.name}",
                "start_time": workflow_description.start_time.isoformat() if workflow_description.start_time else None,
                "end_time": workflow_description.close_time.isoformat() if workflow_description.close_time else None
            }
            
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            logger.error(f"❌ Workflow nenalezen: {error_msg}")
            raise ValueError(f"Workflow {workflow_id} s run_id {run_id} neexistuje")
        elif "connection" in error_msg.lower() or "refused" in error_msg.lower():
            logger.error(f"❌ Temporal connection error: {error_msg}")
            raise ConnectionError(f"Nelze se připojit k Temporal serveru: {error_msg}")
        else:
            logger.error(f"❌ Neočekávaná chyba: {error_msg}")
            raise Exception(f"Chyba při získávání výsledku workflow: {error_msg}")

async def describe_workflow_execution(workflow_id: str, run_id: str) -> dict:
    """
    Získá detailní diagnostické informace o workflow execution.
    
    Args:
        workflow_id: ID workflow
        run_id: Run ID workflow
        
    Returns:
        dict s detailními informacemi včetně pending aktivit
        
    Raises:
        ConnectionError: Pokud se nelze připojit k Temporal serveru
        ValueError: Pokud workflow neexistuje
        Exception: Pro ostatní neočekávané chyby
    """
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    
    logger.info(f"🔍 Načítám detailní diagnostiku workflow: {workflow_id} (run: {run_id})")
    
    try:
        # Připojení k Temporal serveru
        client = await Client.connect(temporal_host, namespace=temporal_namespace)
        logger.info("✅ Temporal client připojen")
        
        # Získání workflow handle
        workflow_handle = client.get_workflow_handle(workflow_id=workflow_id, run_id=run_id)
        
        # Získání detailních informací o workflow
        workflow_description = await workflow_handle.describe()
        
        # Základní informace
        status = workflow_description.status.name
        start_time = workflow_description.start_time
        close_time = workflow_description.close_time
        
        # Výpočet elapsed time
        import datetime
        current_time = datetime.datetime.now(datetime.timezone.utc)
        if start_time:
            elapsed_seconds = (current_time - start_time).total_seconds()
        else:
            elapsed_seconds = 0
            
        # Detekce long-running workflow (více než 15 minut)
        is_long_running = elapsed_seconds > 900  # 15 minut
        
        result = {
            "workflow_id": workflow_id,
            "run_id": run_id,
            "status": status,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": close_time.isoformat() if close_time else None,
            "elapsed_seconds": int(elapsed_seconds),
            "is_long_running": is_long_running,
            "warning": is_long_running if status == "RUNNING" else False
        }
        
        # Pokud workflow běží, získáme informace o pending aktivitách
        if status == "RUNNING":
            try:
                # Získání pending activity info
                pending_activities = getattr(workflow_description, 'pending_activities', [])
                
                # Pokusíme se získat stage_logs i z běžícího workflow (pokud jsou dostupné)
                stage_logs = []
                try:
                    # Pro běžící workflow můžeme zkusit získat mezivýsledky (obvykle nedostupné)
                    logger.info("🔍 Pokouším se získat stage logs z běžícího workflow...")
                    # Stage logs nejsou obvykle dostupné u RUNNING workflow, ale můžeme to zkusit
                except Exception as logs_error:
                    logger.debug(f"Stage logs nedostupné pro RUNNING workflow: {logs_error}")
                
                if pending_activities:
                    # Vezmeme první pending aktivitu (obvykle je jen jedna)
                    activity_info = pending_activities[0]
                    
                    activity_type = getattr(activity_info, 'activity_type', {})
                    activity_name = getattr(activity_type, 'name', 'Unknown')
                    
                    # Mapování activity names na fáze
                    phase_mapping = {
                        'generate_llm_friendly_content': 'Brief Generation',
                        'inject_structured_markup': 'Research & Analysis', 
                        'enrich_with_entities': 'Content Drafting',
                        'add_conversational_faq': 'Content Review',
                        'save_output_to_json': 'Publishing'
                    }
                    
                    current_phase = phase_mapping.get(activity_name, activity_name)
                    
                    # Informace o aktivitě
                    activity_elapsed = 0
                    if hasattr(activity_info, 'scheduled_time') and activity_info.scheduled_time:
                        activity_elapsed = (current_time - activity_info.scheduled_time).total_seconds()
                    
                    result.update({
                        "current_activity_type": activity_name,
                        "current_phase": current_phase,
                        "activity_elapsed_seconds": int(activity_elapsed),
                        "activity_attempt": getattr(activity_info, 'attempt', 1),
                        "last_heartbeat_time": getattr(activity_info, 'last_heartbeat_time', None),
                        "stage_logs": stage_logs  # Přidáme stage logs (obvykle prázdné pro RUNNING)
                    })
                    
                    logger.info(f"🎯 Aktuální fáze: {current_phase} ({activity_name})")
                    
                else:
                    result.update({
                        "current_activity_type": None,
                        "current_phase": "Workflow Logic",
                        "activity_elapsed_seconds": 0,
                        "activity_attempt": 0,
                        "stage_logs": stage_logs
                    })
                    logger.info("🔄 Žádné pending aktivity - workflow logic")
                    
            except Exception as activity_error:
                logger.warning(f"⚠️ Chyba při načítání activity info: {activity_error}")
                result.update({
                    "current_activity_type": "Unknown", 
                    "current_phase": "Unknown Phase",
                    "activity_elapsed_seconds": 0,
                    "activity_attempt": 0,
                    "activity_error": str(activity_error),
                    "stage_logs": []
                })
        
        if is_long_running and status == "RUNNING":
            logger.warning(f"⚠️ Long-running workflow detected: {elapsed_seconds/60:.1f} minutes")
            
        return result
        
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            logger.error(f"❌ Workflow nenalezen: {error_msg}")
            raise ValueError(f"Workflow {workflow_id} s run_id {run_id} neexistuje")
        elif "connection" in error_msg.lower() or "refused" in error_msg.lower():
            logger.error(f"❌ Temporal connection error: {error_msg}")
            raise ConnectionError(f"Nelze se připojit k Temporal serveru: {error_msg}")
        else:
            logger.error(f"❌ Neočekávaná chyba: {error_msg}")
            raise Exception(f"Chyba při diagnostice workflow: {error_msg}")

async def terminate_workflow(workflow_id: str, run_id: str, reason: str = "Manually terminated") -> dict:
    """
    Ukončí běžící workflow execution.
    
    Args:
        workflow_id: ID workflow
        run_id: Run ID workflow
        reason: Důvod ukončení
        
    Returns:
        dict s potvrzením akce
        
    Raises:
        ConnectionError: Pokud se nelze připojit k Temporal serveru
        ValueError: Pokud workflow neexistuje nebo není RUNNING
        Exception: Pro ostatní neočekávané chyby
    """
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    
    logger.info(f"⛔ Ukončuji workflow: {workflow_id} (run: {run_id}) - důvod: {reason}")
    
    try:
        # Připojení k Temporal serveru
        client = await Client.connect(temporal_host, namespace=temporal_namespace)
        logger.info("✅ Temporal client připojen")
        
        # Získání workflow handle
        workflow_handle = client.get_workflow_handle(workflow_id=workflow_id, run_id=run_id)
        
        # Ověření, že workflow existuje a je RUNNING
        workflow_description = await workflow_handle.describe()
        status = workflow_description.status.name
        
        if status != "RUNNING":
            logger.warning(f"⚠️ Workflow není RUNNING (status: {status})")
            raise ValueError(f"Workflow není možné ukončit - status: {status}")
        
        # Ukončení workflow
        await workflow_handle.terminate(reason=reason)
        
        logger.info(f"✅ Workflow {workflow_id} byl úspěšně ukončen")
        
        return {
            "success": True,
            "message": f"Workflow {workflow_id} byl úspěšně ukončen",
            "workflow_id": workflow_id,
            "run_id": run_id,
            "reason": reason,
            "terminated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            logger.error(f"❌ Workflow nenalezen: {error_msg}")
            raise ValueError(f"Workflow {workflow_id} s run_id {run_id} neexistuje")
        elif "connection" in error_msg.lower() or "refused" in error_msg.lower():
            logger.error(f"❌ Temporal connection error: {error_msg}")
            raise ConnectionError(f"Nelze se připojit k Temporal serveru: {error_msg}")
        else:
            logger.error(f"❌ Neočekávaná chyba: {error_msg}")
            raise Exception(f"Chyba při ukončování workflow: {error_msg}") 