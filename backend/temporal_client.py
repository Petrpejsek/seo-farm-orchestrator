import os
import logging
from datetime import datetime
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
        
        # STRICT MODE - žádné fallbacky
        if not topic.strip():
            raise ValueError("❌ Topic parameter je prázdný - musí být explicitně zadán")
            
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
        # Načtení konfigurace z ENV - STRICT MODE
        temporal_host = os.getenv("TEMPORAL_HOST")
        temporal_namespace = os.getenv("TEMPORAL_NAMESPACE")
        
        if not temporal_host:
            raise Exception("❌ TEMPORAL_HOST environment variable musí být explicitně nastavena")
        if not temporal_namespace:
            raise Exception("❌ TEMPORAL_NAMESPACE environment variable musí být explicitně nastavena")
        
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
        
        # Rozhodnutí o typu workflow na základě existence projektu a asistentů v DB  
        if project_id:
            # 🔍 STRICT PROJECT VALIDATION - ověření existence projektu v databázi
            try:
                import requests
                
                logger.info(f"🔍 Ověřuji projekt {project_id} (STRICT validation)")
                
                # Základní validace project_id
                if not project_id or len(project_id.strip()) == 0:
                    raise Exception("Project ID nesmí být prázdný")
                
                # 🚫 FAIL FAST - přímé ověření v databázi (bez circular dependency)
                from api.database import get_prisma_client
                
                logger.info(f"📡 Validuji projekt přímo v databázi: {project_id}")
                
                # Přímé databázové ověření 
                prisma = await get_prisma_client()
                
                # Kontrola existence projektu
                project = await prisma.project.find_unique(where={"id": project_id})
                if not project:
                    error_msg = f"❌ Projekt {project_id} neexistuje v databázi"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                # Kontrola asistentů
                assistants = await prisma.assistant.find_many(
                    where={"projectId": project_id, "active": True},
                    order={"order": "asc"}
                )
                
                if not assistants or len(assistants) == 0:
                    error_msg = f"❌ Projekt {project.name} nemá žádné aktivní asistenty - vytvořte asistenty přes UI"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                logger.info(f"✅ Projekt {project.name} ověřen - nalezeno {len(assistants)} aktivních asistentů")
                
                workflow_type = "AssistantPipelineWorkflow"
                workflow_id = f"assistant_pipeline_{safe_topic}_{timestamp}"
                logger.info(f"🤖 Používám AssistantPipelineWorkflow s asistenty z databáze (projekt {project_id})")
                
            except Exception as e:
                logger.error(f"❌ Chyba při ověřování projektu {project_id}: {str(e)}")
                raise Exception(f"Workflow nelze spustit: {str(e)}")
                
        else:
            # Žádný project_id - nelze spustit workflow bez konfigurace
            raise Exception("Project ID je povinný - workflow nelze spustit bez specifikace projektu a asistentů")
        
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
        logger.info(f"   📥 Task queue: {os.getenv('TEMPORAL_TASK_QUEUE', 'default')}")
        
        try:
            if project_id and workflow_type == "AssistantPipelineWorkflow":
                # Nový AssistantPipelineWorkflow s project_id
                current_date = __import__('datetime').datetime.now().strftime("%d. %m. %Y")
                logger.info(f"   📋 Arguments: topic='{topic}', project_id='{project_id}', csv_base64={bool(csv_base64)}, date='{current_date}'")
                
                workflow_handle = await client.start_workflow(
                    "AssistantPipelineWorkflow",
                    args=[topic, project_id, csv_base64, current_date],
                    id=workflow_id,
                    task_queue=os.getenv("TEMPORAL_TASK_QUEUE", "default"),  # Explicit env nebo standard
                    run_timeout=__import__('datetime').timedelta(minutes=run_timeout_minutes),
                    task_timeout=__import__('datetime').timedelta(minutes=task_timeout_minutes)
                )
            else:
                # KRITICKÁ CHYBA - tato větev by se nikdy neměla vykonat
                # Pokud neexistuje project_id, funkce by měla vyhodit chybu výše
                error_msg = f"Neplatný stav: workflow_type='{workflow_type}', project_id='{project_id}'"
                logger.error(f"❌ {error_msg}")
                raise Exception(f"Systémová chyba při spouštění workflow: {error_msg}")
            
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
        limit: Maximální počet výsledků
        
    Returns:
        List[dict] s workflow informacemi
        
    Raises:
        ConnectionError: Pokud se nelze připojit k Temporal serveru
        ValueError: Pokud jsou data z Temporal nesprávná
        Exception: Pro ostatní neočekávané chyby
    """
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE")
    if not temporal_namespace:
        raise Exception("❌ TEMPORAL_NAMESPACE environment variable musí být explicitně nastavena")
    
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
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE")
    if not temporal_namespace:
        raise Exception("❌ TEMPORAL_NAMESPACE environment variable musí být explicitně nastavena")
    
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
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE")
    if not temporal_namespace:
        raise Exception("❌ TEMPORAL_NAMESPACE environment variable musí být explicitně nastavena")
    
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
            # 🔧 FIX: Zajistíme kompatibilní timezone formát
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=datetime.timezone.utc)
            elapsed_seconds = (current_time - start_time).total_seconds()
        else:
            elapsed_seconds = 0
            
        # 🚨 ENHANCED MONITORING - detekce problematických workflow
        is_long_running = elapsed_seconds > 600   # 10 minut (zpřísněno z 15 min)
        is_critical = elapsed_seconds > 1200      # 20 minut = kritický stav
        is_stuck = elapsed_seconds > 1800        # 30 minut = zaseklé workflow
        
        result = {
            "workflow_id": workflow_id,
            "run_id": run_id,
            "status": status,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": close_time.isoformat() if close_time else None,
            "elapsed_seconds": int(elapsed_seconds),
            "is_long_running": is_long_running,
            "is_critical": is_critical,
            "is_stuck": is_stuck,
            "warning": is_long_running if status == "RUNNING" else False
        }
        
        # 🔍 DETAILNÍ AUDIT - získáme informace o aktivitách (RUNNING, TIMED_OUT, FAILED)
        if status in ["RUNNING", "TIMED_OUT", "FAILED"]:
            try:
                # Získání pending activity info
                pending_activities = getattr(workflow_description, 'pending_activities', [])
                
                # 🔍 ZÍSKÁNÍ WORKFLOW HISTORIE PRO AUDIT
                workflow_history = []
                try:
                    logger.info(f"🔍 Načítám historii workflow pro audit ({status})...")
                    
                    # Získání event history z workflow
                    history = await workflow_handle.fetch_history()
                    
                    # Zkusíme různé způsoby přístupu k událostem
                    events = []
                    if hasattr(history, 'events'):
                        events = history.events
                    elif hasattr(history, '__iter__'):
                        events = list(history)
                    else:
                        logger.warning(f"⚠️ History object type: {type(history)}, attrs: {dir(history)}")
                        events = []
                    
                    logger.info(f"📋 Nalezeno {len(events)} událostí v historii")
                    
                    for event in events:
                        try:
                            event_type = getattr(event, 'event_type', 'Unknown')
                            event_time = getattr(event, 'event_time', None)
                            
                            # Bezpečné formátování času
                            time_str = None
                            if event_time:
                                try:
                                    time_str = event_time.isoformat() if hasattr(event_time, 'isoformat') else str(event_time)
                                except:
                                    time_str = str(event_time)
                            
                            if hasattr(event, 'activity_task_scheduled_event_attributes'):
                                attrs = event.activity_task_scheduled_event_attributes
                                
                                # Debug informace o attrs
                                logger.debug(f"📋 DEBUG attrs: {dir(attrs) if attrs else 'None'}")
                                
                                activity_id = getattr(attrs, 'activity_id', 'Unknown')
                                activity_type = getattr(attrs, 'activity_type', None)
                                
                                # Debug informace o activity_type
                                if activity_type:
                                    logger.debug(f"📋 DEBUG activity_type: type={type(activity_type)}, attrs={dir(activity_type)}")
                                
                                # Lepší extrakce názvu aktivity
                                activity_name = 'Unknown'
                                if activity_type:
                                    if hasattr(activity_type, 'name'):
                                        activity_name = activity_type.name
                                    elif hasattr(activity_type, '__dict__'):
                                        activity_name = str(activity_type.__dict__.get('name', activity_type))
                                    else:
                                        activity_name = str(activity_type)
                                
                                # Pokud stále nemáme název, zkusíme alternativní přístup  
                                if activity_name in ['Unknown', '', None]:
                                    for attr_name in ['type', 'name', 'activity_type_name']:
                                        if hasattr(attrs, attr_name):
                                            potential_name = getattr(attrs, attr_name)
                                            if potential_name:
                                                activity_name = str(potential_name)
                                                break
                                
                                # Lepší formátování času pokud je v protobuf formátu
                                formatted_time = time_str
                                if hasattr(event_time, 'seconds') and hasattr(event_time, 'nanos'):
                                    try:
                                        import datetime
                                        timestamp = event_time.seconds + event_time.nanos / 1_000_000_000
                                        formatted_time = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).isoformat()
                                    except:
                                        formatted_time = f"seconds:{event_time.seconds}"
                                
                                workflow_history.append({
                                    "event_type": "ActivityTaskScheduled",
                                    "activity_name": activity_name,
                                    "activity_id": activity_id,
                                    "event_time": formatted_time,
                                    "status": "SCHEDULED"
                                })
                            
                            elif hasattr(event, 'activity_task_started_event_attributes'):
                                workflow_history.append({
                                    "event_type": "ActivityTaskStarted", 
                                    "event_time": time_str,
                                    "status": "STARTED"
                                })
                                
                            elif hasattr(event, 'activity_task_completed_event_attributes'):
                                attrs = event.activity_task_completed_event_attributes
                                result = getattr(attrs, 'result', None)
                                
                                workflow_history.append({
                                    "event_type": "ActivityTaskCompleted",
                                    "event_time": time_str,
                                    "status": "COMPLETED",
                                    "result_size": len(str(result)) if result else 0
                                })
                                
                            elif hasattr(event, 'activity_task_failed_event_attributes'):
                                attrs = event.activity_task_failed_event_attributes
                                failure = getattr(attrs, 'failure', None)
                                failure_message = getattr(failure, 'message', 'Unknown') if failure else 'Unknown'
                                
                                workflow_history.append({
                                    "event_type": "ActivityTaskFailed",
                                    "event_time": time_str,
                                    "status": "FAILED",
                                    "error_message": failure_message
                                })
                                
                            elif hasattr(event, 'activity_task_timed_out_event_attributes'):
                                attrs = event.activity_task_timed_out_event_attributes
                                timeout_type = getattr(attrs, 'timeout_type', 'Unknown')
                                
                                workflow_history.append({
                                    "event_type": "ActivityTaskTimedOut",
                                    "event_time": time_str,
                                    "status": "TIMED_OUT",
                                    "timeout_type": str(timeout_type) if timeout_type else 'Unknown'
                                })
                                
                        except Exception as event_error:
                            logger.warning(f"⚠️ Chyba při zpracování události: {event_error}")
                            workflow_history.append({
                                "event_type": "EventProcessingError",
                                "error": str(event_error),
                                "event_time": time_str
                            })
                    
                    logger.info(f"✅ Načteno {len(workflow_history)} událostí z historie workflow")
                    
                except Exception as history_error:
                    logger.warning(f"⚠️ Chyba při načítání workflow historie: {history_error}")
                    workflow_history = [{"error": f"Failed to load history: {str(history_error)}"}]
                
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
                        # 🔧 FIX: Zajistíme kompatibilní timezone formát
                        scheduled_time = activity_info.scheduled_time
                        if scheduled_time.tzinfo is None:
                            scheduled_time = scheduled_time.replace(tzinfo=datetime.timezone.utc)
                        activity_elapsed = (current_time - scheduled_time).total_seconds()
                    
                    result.update({
                        "current_activity_type": activity_name,
                        "current_phase": current_phase,
                        "activity_elapsed_seconds": int(activity_elapsed),
                        "activity_attempt": getattr(activity_info, 'attempt', 1),
                        "last_heartbeat_time": getattr(activity_info, 'last_heartbeat_time', None),
                        "workflow_history": workflow_history  # 🔍 AUDIT: Historie všech aktivit
                    })
                    
                    logger.info(f"🎯 Aktuální fáze: {current_phase} ({activity_name})")
                    
                else:
                    # Pro TIMED_OUT/FAILED workflow často nejsou pending activities
                    if status == "TIMED_OUT":
                        current_phase = "TIMED_OUT - Analýza historie"
                        logger.warning("⏰ TIMED_OUT workflow - analyzuji historii aktivit")
                    elif status == "FAILED": 
                        current_phase = "FAILED - Analýza chyb"
                        logger.error("❌ FAILED workflow - analyzuji chyby")
                    else:
                        current_phase = "Workflow Logic"
                        logger.info("🔄 Žádné pending aktivity - workflow logic")
                    
                    result.update({
                        "current_activity_type": None,
                        "current_phase": current_phase,
                        "activity_elapsed_seconds": 0,
                        "activity_attempt": 0,
                        "workflow_history": workflow_history  # 🔍 AUDIT: Historie i pro non-running workflow
                    })
                    
            except Exception as activity_error:
                logger.warning(f"⚠️ Chyba při načítání activity info: {activity_error}")
                result.update({
                    "current_activity_type": "Unknown", 
                    "current_phase": "Unknown Phase - Chyba načítání",
                    "activity_elapsed_seconds": 0,
                    "activity_attempt": 0,
                    "activity_error": str(activity_error),
                    "workflow_history": []  # 🔍 AUDIT: Prázdná historie při chybě
                })
        
        # 🚨 ENHANCED MONITORING ALERTS
        if status == "RUNNING":
            if is_stuck:
                logger.error(f"🔥 ZASEKLÝ WORKFLOW: {workflow_id} běží {elapsed_seconds/60:.1f} minut - NUTNÉ UKONČIT!")
            elif is_critical:
                logger.warning(f"💥 KRITICKÝ WORKFLOW: {workflow_id} běží {elapsed_seconds/60:.1f} minut - zkontrolovat stav")
            elif is_long_running:
                logger.warning(f"⚠️ DLOUHODOBĚ BĚŽÍCÍ WORKFLOW: {workflow_id} běží {elapsed_seconds/60:.1f} minut")
            
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
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE")
    if not temporal_namespace:
        raise Exception("❌ TEMPORAL_NAMESPACE environment variable musí být explicitně nastavena")
    
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
            "terminated_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
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