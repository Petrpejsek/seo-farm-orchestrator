import logging
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from temporal_client import start_seo_pipeline, list_workflows, get_workflow_result, describe_workflow_execution, terminate_workflow

# Import nových API routerů
from api.routes.project import router as project_router
from api.routes.assistant import router as assistant_router
from api.routes.workflow_run import router as workflow_run_router
from api.routes.api_keys import router as api_keys_router

# Import databázového připojení
from api.database import connect_database, disconnect_database

# Import databázového připojení a workflow run API
from api.database import get_prisma_client

# Nastavení loggingu
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan context manager pro startup/shutdown události
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_database()
    logger.info("✅ Databáze připojena při startu")
    yield
    # Shutdown
    await disconnect_database()
    logger.info("🔄 Databáze odpojená při ukončení")

# FastAPI instance s lifespan
app = FastAPI(
    title="SEO Farm Orchestrator Backend",
    description="FastAPI backend s Temporal.io integrací pro SEO content generation",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware - povolení přístupu z frontendu
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",  # Frontend development server (primary port)
        "http://127.0.0.1:3001",  # Alternative localhost format
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Pydantic modely pro validaci
class CSVData(BaseModel):
    name: str = Field(..., description="Název CSV souboru")
    content: str = Field(..., description="Base64 encoded obsah CSV souboru")

class PipelineRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Téma pro SEO zpracování")
    project_id: Optional[str] = Field(None, description="ID projektu pro propojení workflow")
    csv: Optional[CSVData] = Field(None, description="Volitelný CSV soubor")

class PipelineResponse(BaseModel):
    status: str = Field(..., description="Status spuštění workflow")
    workflow_id: str = Field(..., description="ID Temporal workflow")
    run_id: str = Field(..., description="Run ID Temporal workflow")
    project_id: Optional[str] = Field(None, description="ID projektu")
    database_id: Optional[str] = Field(None, description="ID záznamu v databázi")

class TerminateWorkflowRequest(BaseModel):
    reason: str = Field(default="Manually terminated by user", description="Důvod ukončení workflow")

# Registrace routerů
app.include_router(project_router)
app.include_router(assistant_router)
app.include_router(workflow_run_router)
app.include_router(api_keys_router)

# Databázové připojení je nyní spravováno přes lifespan context manager

@app.get("/")
async def root():
    """Health check endpoint pro ověření stavu API"""
    return {"message": "SEO Farm Orchestrator Backend API", "status": "running"}

@app.post("/api/pipeline-run", response_model=PipelineResponse)
async def pipeline_run(request: PipelineRequest):
    """
    Spustí SEO pipeline workflow přes Temporal a vytvoří záznam v databázi.
    
    Args:
        request: Pipeline request s tématem, project_id a volitelným CSV
        
    Returns:
        Response s workflow ID, run ID a databázovým ID
        
    Raises:
        HTTPException: 400 pokud projekt neexistuje, 500 pokud chybí připojení k Temporal
    """
    try:
        logger.info(f"🚀 Spouštím SEO pipeline:")
        logger.info(f"   📋 Téma: {request.topic}")
        logger.info(f"   🏗️ Project ID: {request.project_id}")
        logger.info(f"   📄 CSV: {'✅ Přiložen' if request.csv else '❌ Žádný'}")
        
        # Ověření existence projektu pokud je zadán project_id
        database_id = None
        if request.project_id:
            try:
                prisma = await get_prisma_client()
                project = await prisma.project.find_unique(where={"id": request.project_id})
                if not project:
                    logger.error(f"❌ Projekt s ID {request.project_id} nenalezen")
                    raise HTTPException(status_code=400, detail=f"Projekt s ID {request.project_id} neexistuje")
                logger.info(f"✅ Projekt ověřen: {project.name}")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"❌ Chyba při ověřování projektu: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Chyba při ověřování projektu: {str(e)}")
        
        # Extrakce CSV obsahu pokud existuje
        csv_base64 = None
        if request.csv:
            csv_base64 = request.csv.content
            logger.info(f"📄 CSV soubor přiložen: {request.csv.name}")
        
        # Spuštění Temporal workflow
        logger.info("🔌 Připojuji se k Temporal serveru...")
        workflow_id, run_id = await start_seo_pipeline(
            topic=request.topic,
            project_id=request.project_id,
            csv_base64=csv_base64
        )
        
        logger.info(f"✅ Temporal workflow úspěšně spuštěn:")
        logger.info(f"   🆔 Workflow ID: {workflow_id}")
        logger.info(f"   🏃 Run ID: {run_id}")
        
        # Vytvoření záznamu v databázi pokud je zadán project_id
        if request.project_id:
            try:
                # Import WorkflowRunCreate modelu a create_workflow_run funkce
                from api.routes.workflow_run import WorkflowRunCreate, create_workflow_run
                
                # Vytvoření záznamu workflow run v databázi
                workflow_run_data = WorkflowRunCreate(
                    projectId=request.project_id,
                    topic=request.topic,
                    runId=run_id,
                    workflowId=workflow_id
                )
                
                logger.info(f"💾 Ukládám workflow do databáze:")
                logger.info(f"   📝 Topic: {request.topic}")
                logger.info(f"   🏗️ Project ID: {request.project_id}")
                logger.info(f"   🆔 Workflow ID: {workflow_id}")
                logger.info(f"   🏃 Run ID: {run_id}")
                
                # Skutečné volání API endpointu pro vytvoření databázového záznamu
                workflow_response = await create_workflow_run(workflow_run_data)
                database_id = workflow_response.id
                
                logger.info(f"✅ Workflow run skutečně vytvořen v databázi s ID: {database_id}")
                
            except Exception as e:
                logger.error(f"⚠️ Chyba při vytváření databázového záznamu: {str(e)}")
                logger.info("ℹ️ Workflow pokračuje, ale bez databázového záznamu")
        
        logger.info(f"🎉 Pipeline úspěšně spuštěna pro téma: '{request.topic}'")
        
        return PipelineResponse(
            status="started",
            workflow_id=workflow_id,
            run_id=run_id,
            project_id=request.project_id,
            database_id=database_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Kritická chyba při spuštění pipeline:")
        logger.error(f"   📋 Téma: {request.topic}")
        logger.error(f"   🏗️ Project ID: {request.project_id}")
        logger.error(f"   🚨 Chyba: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Chyba při spuštění workflow: {str(e)}"
        )

@app.get("/api/workflows")
async def get_workflows(limit: int = Query(30, description="Maximální počet výsledků")):
    """
    Načte seznam workflow executions z Temporal serveru.
    
    Args:
        limit: Maximální počet výsledků (default 30)
        
    Returns:
        JSON s workflows seznamem
        
    Raises:
        HTTPException: Appropriate HTTP status based on error type
    """
    logger.info(f"🧠 Dotaz na Temporal: načítám {limit} workflows...")
    
    try:
        # Volání funkce pro načtení workflows
        workflows = await list_workflows(limit=limit)
        
        if not workflows:
            logger.info("📭 Žádné workflows nenalezeny - vrácím prázdné pole")
            return {"workflows": []}
        
        logger.info(f"✅ Vráceno {len(workflows)} workflowů")
        return {"workflows": workflows}
        
    except ConnectionError as e:
        logger.error(f"❌ Temporal server nedostupný: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Temporal server je momentálně nedostupný. Zkuste to znovu později."
        )
    except ValueError as e:
        logger.error(f"❌ Neplatná data z Temporal: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail=f"Chyba zpracování dat: {str(e)}"
        )
    except Exception as e:
        # Loguj celý stacktrace pro debug
        import traceback
        logger.error(f"❌ Neočekáváná chyba při načítání workflows:")
        logger.error(f"   Typ: {type(e).__name__}")
        logger.error(f"   Zpráva: {str(e)}")
        logger.error(f"   Stacktrace: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Chyba při načítání workflows: {str(e)}"
        )

@app.get("/api/workflow-result/{workflow_id}/{run_id}")
async def get_workflow_result_endpoint(
    workflow_id: str = Path(..., description="ID workflow"),
    run_id: str = Path(..., description="Run ID workflow")
):
    """
    Získá výsledek dokončeného workflow z Temporal serveru s diagnostickými informacemi.
    
    Args:
        workflow_id: ID workflow
        run_id: Run ID workflow
        
    Returns:
        JSON s workflow výsledkem, metadata a diagnostickými informacemi
        
    Raises:
        HTTPException: 404 pokud workflow neexistuje, 503 pokud Temporal není dostupný
    """
    logger.info(f"📤 Fetch result: workflow_id={workflow_id}, run_id={run_id}")
    
    try:
        # 🔧 OPRAVA: Nejdřív zkusíme načíst aktualizovaná data z databáze
        from api.database import get_prisma_client
        prisma = await get_prisma_client()
        
        # Hledáme workflow v databázi
        db_run = await prisma.workflowrun.find_unique(
            where={
                "workflowId_runId": {
                    "workflowId": workflow_id,
                    "runId": run_id
                }
            }
        )
        

        
        # Pokud máme uložená aktualizovaná data z retry, použijeme je
        if db_run and db_run.resultJson:
            try:
                import json
                result_data = json.loads(db_run.resultJson)

                logger.info("✅ Načtena aktualizovaná data z databáze (včetně retry změn)")
            except Exception as e:
                # Fallback na Temporal pokud JSON parsing selže
                result_data = await get_workflow_result(workflow_id=workflow_id, run_id=run_id)
                logger.warning(f"JSON parsing failed, using Temporal data: {e}")
        else:
            # Načteme z Temporal a aktualizujeme databázi
            logger.info("No database data found, loading from Temporal")
            result_data = await get_workflow_result(workflow_id=workflow_id, run_id=run_id)
            await update_workflow_status_in_database(workflow_id=workflow_id, run_id=run_id, result_data=result_data)
            logger.info("✅ Načtena fresh data z Temporal")
        
        # Přidáme diagnostické informace pro RUNNING i TIMED_OUT workflow  
        if result_data.get("status") in ["RUNNING", "TIMED_OUT", "FAILED"]:
            try:
                diagnostic_info = await describe_workflow_execution(workflow_id=workflow_id, run_id=run_id)
                
                # Sloučíme diagnostické informace s výsledkem
                result_data.update({
                    "current_phase": diagnostic_info.get("current_phase", "Unknown"),
                    "current_activity_type": diagnostic_info.get("current_activity_type"),
                    "elapsed_seconds": diagnostic_info.get("elapsed_seconds", 0),
                    "activity_elapsed_seconds": diagnostic_info.get("activity_elapsed_seconds", 0),
                    "activity_attempt": diagnostic_info.get("activity_attempt", 0),
                    "is_long_running": diagnostic_info.get("is_long_running", False),
                    "warning": diagnostic_info.get("warning", False),
                    "workflow_history": diagnostic_info.get("workflow_history", [])  # 🔍 AUDIT: Historie aktivit
                })
                
                logger.info(f"🎯 Current phase: {diagnostic_info.get('current_phase')} ({diagnostic_info.get('elapsed_seconds', 0)/60:.1f} min)")
                
            except Exception as diag_error:
                logger.warning(f"⚠️ Diagnostika selhala: {str(diag_error)}")
                # Přidáme alespoň basic info
                result_data.update({
                    "current_phase": "Unknown (diagnostic failed)",
                    "warning": False,
                    "diagnostic_error": str(diag_error)
                })
        
        logger.info(f"✅ Result loaded: status={result_data.get('status')}")
        return result_data
        
    except ValueError as e:
        # Workflow neexistuje nebo není dokončen
        logger.warning(f"⚠️ Workflow nenalezen: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Workflow nenalezen nebo výstup není k dispozici",
                "message": str(e)
            }
        )
    except ConnectionError as e:
        # Temporal server není dostupný
        logger.error(f"❌ Temporal connection error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Temporal server není dostupný",
                "message": "Zkuste to později nebo kontaktujte administrátora"
            }
        )
    except Exception as e:
        # Ostatní chyby
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Nastala chyba při načítání výstupu",
                "message": str(e)
            }
        )

@app.post("/api/workflow-terminate/{workflow_id}/{run_id}")
async def terminate_workflow_endpoint(
    workflow_id: str = Path(..., description="ID workflow"),
    run_id: str = Path(..., description="Run ID workflow"),
    request: TerminateWorkflowRequest = None
):
    """
    Ukončí běžící workflow execution.
    
    Args:
        workflow_id: ID workflow
        run_id: Run ID workflow  
        request: Požadavek s důvodem ukončení
        
    Returns:
        JSON s potvrzením ukončení
        
    Raises:
        HTTPException: 404 pokud workflow neexistuje nebo není RUNNING, 503 pokud Temporal není dostupný
    """
    reason = request.reason if request else "Manually terminated by user"
    logger.info(f"⛔ Terminate request: workflow_id={workflow_id}, run_id={run_id}, reason={reason}")
    
    try:
        result = await terminate_workflow(workflow_id=workflow_id, run_id=run_id, reason=reason)
        logger.info(f"✅ Workflow terminated successfully: {workflow_id}")
        return result
        
    except ValueError as e:
        # Workflow neexistuje nebo není RUNNING
        logger.warning(f"⚠️ Cannot terminate workflow: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Workflow nelze ukončit",
                "message": str(e)
            }
        )
    except ConnectionError as e:
        # Temporal server není dostupný
        logger.error(f"❌ Temporal connection error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Temporal server není dostupný",
                "message": "Zkuste to později nebo kontaktujte administrátora"
            }
        )
    except Exception as e:
        # Ostatní chyby
        logger.error(f"❌ Error terminating workflow: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Nastala chyba při ukončování workflow",
                "message": str(e)
            }
        )

async def update_workflow_status_in_database(workflow_id: str, run_id: str, result_data: dict):
    """
    Aktualizuje status workflow v databázi na základě informací z Temporal serveru.
    
    Args:
        workflow_id: ID workflow z Temporal
        run_id: Run ID workflow z Temporal 
        result_data: Výsledek z get_workflow_result
    """
    try:
        from api.routes.workflow_run import get_prisma_client
        from datetime import datetime
        

        
        prisma = await get_prisma_client()

        
        # Najdeme workflow run podle workflowId a runId
        existing_run = await prisma.workflowrun.find_unique(
            where={
                "workflowId_runId": {
                    "workflowId": workflow_id,
                    "runId": run_id
                }
            }
        )
        
        if not existing_run:
            logger.warning(f"⚠️ Workflow run {workflow_id}/{run_id} nenalezen v databázi pro aktualizaci")
            return
        
        # Připravíme data pro aktualizaci
        update_fields = {}
        temporal_status = result_data.get("status")
        
        # Mapování Temporal statusů na naše databázové statusy
        if temporal_status == "COMPLETED":
            update_fields["status"] = "COMPLETED"
            if result_data.get("end_time"):
                update_fields["finishedAt"] = datetime.fromisoformat(result_data["end_time"].replace('Z', '+00:00'))
        elif temporal_status == "FAILED":
            update_fields["status"] = "FAILED"
            if result_data.get("end_time"):
                update_fields["finishedAt"] = datetime.fromisoformat(result_data["end_time"].replace('Z', '+00:00'))
        elif temporal_status == "TIMED_OUT":
            update_fields["status"] = "TIMED_OUT"
            if result_data.get("end_time"):
                update_fields["finishedAt"] = datetime.fromisoformat(result_data["end_time"].replace('Z', '+00:00'))
        elif temporal_status == "RUNNING":
            update_fields["status"] = "RUNNING"
        else:
            update_fields["status"] = temporal_status or "UNKNOWN"
        
        # Přidáme výsledek jako JSON pokud existuje
        if result_data.get("result"):
            import json
            update_fields["resultJson"] = json.dumps(result_data["result"], ensure_ascii=False)
        
        # Přidáme stage informace pokud existují
        if result_data.get("stage_logs"):
            completed_stages = len([log for log in result_data["stage_logs"] if log.get("status") == "COMPLETED"])
            total_stages = len(result_data["stage_logs"])
            update_fields["stageCount"] = completed_stages
            update_fields["totalStages"] = total_stages
        
        # 🔧 KRITICKÉ: Uložíme celou aktualizovanou strukturu do databáze
        # Frontend potřebuje přístup k aktualizovaným stages po retry
        # Používáme existující pole resultJson místo vytváření nového
        update_fields["resultJson"] = json.dumps(result_data, ensure_ascii=False)
        logger.info(f"💾 Ukládám celou workflow strukturu do databáze (včetně stages)")
        

        
        # Aktualizace v databázi
        updated_run = await prisma.workflowrun.update(
            where={"id": existing_run.id},
            data=update_fields
        )
        
        logger.info(f"✅ Database updated: {updated_run.status} ({updated_run.stageCount}/{updated_run.totalStages} stages)")
        
    except Exception as e:
        logger.error(f"❌ Database update failed: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Nebudeme hadit exception, aby to nerozhodilo hlavní flow


@app.post("/api/retry-publish-script")
async def retry_publish_script(request: dict):
    """
    Spustí pouze PublishScript bez celé pipeline pro úsporu AI kreditů
    """
    try:
        workflow_id = request.get("workflow_id")
        run_id = request.get("run_id")
        stage = request.get("stage")
        
        if not workflow_id or not run_id:
            raise HTTPException(status_code=400, detail="workflow_id a run_id jsou povinné")
        
        logger.info(f"🔧 Retry PublishScript:")
        logger.info(f"   🆔 URL Workflow ID: {workflow_id}")
        logger.info(f"   🏃 URL Run ID: {run_id}")
        logger.info(f"   📋 Stage: {stage}")
        
        # 🔍 OPRAVA: Nejdřív resolvujeme správné Temporal IDs z databáze
        from api.database import get_prisma_client
        
        try:
            prisma = await get_prisma_client()
            
            # Hledáme workflow v databázi podle URL parametrů
            # URL parametry mohou být část názvu workflow_id, takže hledáme přes LIKE
            workflow_records = await prisma.workflowrun.find_many(
                where={
                    "OR": [
                        {"workflowId": {"contains": workflow_id}},
                        {"runId": run_id},
                        {"id": run_id}  # možná run_id je database ID
                    ]
                }
            )
            
            if not workflow_records:
                logger.error(f"❌ Nenašel jsem workflow v databázi pro URL parametry")
                raise HTTPException(status_code=404, detail=f"Workflow nenalezen v databázi pro zadané parametry")
            
            # Bereme první (a pravděpodobně jediný) záznam
            workflow_record = workflow_records[0]
            actual_workflow_id = workflow_record.workflowId
            actual_run_id = workflow_record.runId
            
            logger.info(f"✅ Resolvovány správné Temporal IDs:")
            logger.info(f"   🎯 Skutečný Workflow ID: {actual_workflow_id}")
            logger.info(f"   🎯 Skutečný Run ID: {actual_run_id}")
            
        except Exception as db_error:
            logger.error(f"❌ Chyba při hledání workflow v databázi: {db_error}")
            raise HTTPException(status_code=500, detail=f"Chyba při hledání workflow: {str(db_error)}")
        
        # Načteme workflow výsledek pro získání pipeline dat
        from temporal_client import get_workflow_result
        
        workflow_result = await get_workflow_result(actual_workflow_id, actual_run_id)
        
        if not workflow_result or not workflow_result.get("result"):
            raise HTTPException(status_code=404, detail="Workflow data nenalezena")
        
        pipeline_data = workflow_result["result"]
        
        # Spustíme pouze publish_activity s aktuálními daty
        from temporalio.client import Client
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from workflows.assistant_pipeline_workflow import AssistantPipelineWorkflow
        
        # Připojení k Temporal
        client = await Client.connect("localhost:7233")
        
        # DIAGNOSTIKA: Zkontrolujme strukturu dat
        logger.info(f"🔍 Pipeline data keys: {list(pipeline_data.keys())}")
        logger.info(f"🔍 Pipeline final_output sample: {str(pipeline_data.get('final_output', 'MISSING'))[:300]}...")
        
        # Pipeline data obsahuje stage_logs, ale potřebujeme finální výstup
        final_output = pipeline_data.get("final_output", "")
        
        if isinstance(final_output, str) and final_output.strip().startswith('{'):
            # Pokud je final_output JSON string, parsujeme ho
            try:
                import json
                final_output = json.loads(final_output)
                logger.info("✅ Final output úspěšně parsován jako JSON")
            except:
                logger.warning("⚠️ Nelze parsovat final output jako JSON")
        
        # SPRÁVNÁ EXTRAKCE DAT ze stage_logs
        stage_logs = pipeline_data.get("stage_logs", [])
        logger.info(f"📊 Nalezeno {len(stage_logs)} stage logs")
        
        # CHRONOLOGICKÁ DIAGNOSTIKA PIPELINE
        logger.info("🔍 CHRONOLOGIE PIPELINE:")
        for i, log in enumerate(stage_logs):
            stage = log.get("stage", "UNKNOWN")
            status = log.get("status", "UNKNOWN")
            output_preview = str(log.get("output", ""))[:100] + "..." if log.get("output") else "NO OUTPUT"
            logger.info(f"  {i+1:2d}. {stage} - {status} - {output_preview}")
        
        # Extrakce výstupů asistentů ze stage_logs
        components = {
            "draft_assistant_output": "",
            "seo_assistant_output": "",
            "humanizer_assistant_output": "",
            "humanizer_output_after_fact_validation": "",  # ✅ PŘIDÁNO
            "multimedia_assistant_output": "",
            "image_renderer_assistant_output": "",
            "qa_assistant_output": "",
            "fact_validator_assistant_output": "",
            "brief_assistant_output": ""
        }
        
        # Projdeme stage_logs a najdeme výstupy jednotlivých asistentů
        for log in stage_logs:
            stage_name = log.get("stage", "")
            output = log.get("output", "")
            
            if stage_name and output:
                # 🔍 DETAILNÍ DEBUG MAPPING
                logger.info(f"🔍 Zpracovávám stage: '{stage_name}' -> output length: {len(str(output))}")
                
                # Mapování stage names na component keys
                if "seo" in stage_name.lower():
                    components["seo_assistant_output"] = output
                    logger.info(f"✅ SEO output ÚSPĚŠNĚ namapován: {len(str(output))} znaků")
                    logger.info(f"🔍 SEO output preview: {str(output)[:200]}...")
                elif "draft" in stage_name.lower():
                    components["draft_assistant_output"] = output
                    logger.info(f"✅ Draft output nalezen: {len(str(output))} znaků")
                elif "humanizer" in stage_name.lower():
                    components["humanizer_assistant_output"] = output
                    components["humanizer_output_after_fact_validation"] = output  # ✅ PŘIDÁNO - same jako humanizer
                    logger.info(f"✅ Humanizer output nalezen: {len(str(output))} znaků")
                    logger.info(f"✅ Humanizer také namapován jako humanizer_output_after_fact_validation")
                elif "multimedia" in stage_name.lower():
                    components["multimedia_assistant_output"] = output
                    logger.info(f"✅ Multimedia output nalezen: {len(str(output))} znaků")
                elif "image" in stage_name.lower():
                    components["image_renderer_assistant_output"] = output
                    logger.info(f"✅ Image output nalezen: {len(str(output))} znaků")
                elif "qa" in stage_name.lower():
                    components["qa_assistant_output"] = output
                    logger.info(f"✅ QA output nalezen: {len(str(output))} znaků")
                elif "fact" in stage_name.lower() or "validator" in stage_name.lower():
                    components["fact_validator_assistant_output"] = output
                    logger.info(f"✅ FactValidator output nalezen: {len(str(output))} znaků")
                elif "brief" in stage_name.lower():
                    components["brief_assistant_output"] = output
                    logger.info(f"✅ Brief output nalezen: {len(str(output))} znaků")
        
        logger.info(f"📊 Extrakce dokončena: {sum(1 for v in components.values() if v)} neprázdných výstupů")
        
        # DIRECT SCRIPT CALL - spustíme publish_script přímo bez Temporal
        try:
            from datetime import datetime
            import sys
            import os
            import json
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from helpers.transformers import transform_to_PublishInput
            from activities.publish_script import publish_script
            
            logger.info("🔧 Spouštím PublishScript přímo jako Python funkci...")
            logger.info(f"📊 Components keys: {list(components.keys())}")
            logger.info(f"📊 SEO output sample: {components.get('seo_assistant_output', 'MISSING')[:300]}...")
            logger.info(f"📊 Draft output sample: {components.get('draft_assistant_output', 'MISSING')[:200]}...")
            
            # Debug SEO parsování
            try:
                from helpers.transformers import parse_seo_metadata, parse_qa_faq
                seo_data = parse_seo_metadata(components.get('seo_assistant_output', ''))
                logger.info(f"🔍 SEO parsováno: title={seo_data.get('title', 'MISSING')}")
                logger.info(f"🔍 SEO keywords: {seo_data.get('keywords', [])} (count: {len(seo_data.get('keywords', []))})")
                
                # Debug QA parsování
                qa_data = parse_qa_faq(components.get('qa_assistant_output', ''))
                logger.info(f"🔍 QA parsováno: {len(qa_data)} FAQ položek")
                logger.info(f"🔍 QA sample: {components.get('qa_assistant_output', 'MISSING')[:500]}...")
            except Exception as e:
                logger.error(f"❌ Chyba při parsování: {e}")
            
            # Transform pipeline data na PublishInput format - PŘED transformací převeď dict na string
            logger.info("🔧 Převádím dict objekty na stringy před transformací...")
            for key, value in components.items():
                if isinstance(value, dict):
                    components[key] = json.dumps(value, ensure_ascii=False)
                    logger.info(f"✅ {key}: dict převeden na JSON string")
                elif not isinstance(value, str):
                    components[key] = str(value)
                    logger.info(f"✅ {key}: {type(value)} převeden na string")
            
            # Přidáme current_date pro správný ISO 8601 formát
            components["current_date"] = components.get("current_date") or __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat().replace('+00:00', 'Z')
            logger.info(f"✅ current_date nastaven: {components['current_date']}")
            
            publish_input = transform_to_PublishInput(components)
            logger.info(f"📊 Transformace dokončena: {len(publish_input)} položek")
            
            # PŘÍMO SPUSTÍME PUBLISH_SCRIPT
            result = publish_script(publish_input)
            
            # DEBUG: Co publish script vrací?
            logger.info(f"🔍 DEBUG: publish_script vrátil typ: {type(result)}")
            logger.info(f"🔍 DEBUG: publish_script keys: {list(result.keys()) if isinstance(result, dict) else 'NOT_DICT'}")
            logger.info(f"🔍 DEBUG: success klíč: {result.get('success', 'MISSING_KEY') if isinstance(result, dict) else 'NOT_DICT'}")
            logger.info(f"🔍 DEBUG: celý result (první 500 znaků): {str(result)[:500]}")
            
            retry_id = f"retry_publish_direct_{workflow_id}_{int(__import__('datetime').datetime.now().timestamp())}"
            logger.info(f"✅ PublishScript retry dokončen: {retry_id}")
            logger.info(f"📊 Výsledek: {result.get('success', False)}")
            
            # 🔧 KRITICKÁ OPRAVA: Aktualizuj databázi s novými regenerovanými daty
            logger.info(f"🔍 DEBUG: result.get('success') = {result.get('success')}")
            logger.info(f"🔍 DEBUG: actual_workflow_id = {actual_workflow_id}")
            logger.info(f"🔍 DEBUG: actual_run_id = {actual_run_id}")
            
            if result.get('success'):
                try:
                    logger.info("🔄 Aktualizuji databázi s novými regenerovanými daty...")
                    
                    # Načti aktuální workflow data
                    from temporal_client import get_workflow_result
                    logger.info("🔍 Volám get_workflow_result...")
                    current_workflow_data = await get_workflow_result(actual_workflow_id, actual_run_id)
                    logger.info(f"🔍 Workflow data loaded: {bool(current_workflow_data)}")
                    
                    # Debug workflow data structure
                    logger.info(f"🔍 Workflow data type: {type(current_workflow_data)}")
                    logger.info(f"🔍 Workflow data keys: {list(current_workflow_data.keys()) if isinstance(current_workflow_data, dict) else 'NOT_DICT'}")
                    logger.info(f"🔍 Has 'stages' key: {'stages' in current_workflow_data if isinstance(current_workflow_data, dict) else False}")
                    
                    # 🔧 OPRAVA: Stages jsou v 'stage_logs', ne 'stages'
                    stages_key = "stage_logs" if "stage_logs" in current_workflow_data else "stages" 
                    
                    # Najdi PublishScript stage a updatuj jeho output
                    if current_workflow_data and stages_key in current_workflow_data:
                        stages = current_workflow_data[stages_key]
                        logger.info(f"🔍 Počet {stages_key}: {len(stages)}")
                        
                        # Potřebujeme převést stage_logs na strukturu kompatibilní s frontend
                        # Frontend očekává 'stages' s 'stage_name' a 'stage_output'
                        updated_stages = []
                        
                        for i, stage_log in enumerate(stages):
                            stage_name = stage_log.get("stage", "")
                            logger.info(f"🔍 Stage {i}: {stage_name}")
                            
                            # Převod stage_log na frontend formát
                            stage_frontend = {
                                "stage": stage_name,  # ✅ OPRAVENO: "stage" místo "stage_name"
                                "stage_output": stage_log.get("output", ""),
                                "status": stage_log.get("status", ""),
                                "start_time": stage_log.get("start_time", ""),
                                "end_time": stage_log.get("end_time", "")
                            }
                            
                            if "publish" in stage_name.lower():
                                # Aktualizuj PublishScript output s novými daty
                                logger.info(f"🎯 Našel jsem PublishScript stage: {stage_name}")
                                stage_frontend["stage_output"] = result
                                stage_frontend["output"] = result  # 🔧 OPRAVA: Přidat také 'output' field pro frontend tlačítka
                                # ✅ KRITICKÁ OPRAVA: Změní status na COMPLETED
                                if result.get('success'):
                                    stage_frontend["status"] = "COMPLETED"
                                    logger.info("✅ PublishScript stage status změněn na COMPLETED")
                                else:
                                    stage_frontend["status"] = "FAILED"
                                    logger.info("❌ PublishScript stage status zůstává FAILED")
                                logger.info("✅ PublishScript stage output aktualizován")
                            
                            updated_stages.append(stage_frontend)
                        
                        # Aktualizuj strukturu pro frontend kompatibilitu
                        current_workflow_data["stages"] = updated_stages
                        logger.info(f"✅ Převedeno {len(updated_stages)} stages do frontend formátu")
                        
                        # 🔧 KRITICKÁ OPRAVA: Synchronizuj stage_logs se stages pro frontend kompatibilitu
                        # Frontend čte z stage_logs, ale retry aktualizuje stages
                        if "stage_logs" in current_workflow_data:
                            current_workflow_data["stage_logs"] = updated_stages.copy()
                            logger.info(f"✅ Synchronizovány stage_logs se stages pro frontend")
                        
                        # Ulož zpět do databáze
                        await update_workflow_status_in_database(actual_workflow_id, actual_run_id, current_workflow_data)
                    else:
                        if not current_workflow_data:
                            logger.warning("⚠️ current_workflow_data je falsy")
                        elif "stages" not in current_workflow_data:
                            logger.warning("⚠️ 'stages' klíč není v current_workflow_data")
                            logger.warning(f"⚠️ Dostupné klíče: {list(current_workflow_data.keys())}")
                        else:
                            logger.warning("⚠️ Neznámý problém s workflow data")
                        
                except Exception as e:
                    logger.error(f"❌ Chyba při aktualizaci databáze: {e}")
                    import traceback
                    logger.error(f"❌ Traceback: {traceback.format_exc()}")
                    # Pokračujeme i při chybě - hlavní věc je že retry proběhl
            else:
                logger.warning(f"⚠️ Retry result success={result.get('success')} - přeskakuji update databáze")
            
            return {
                "status": "completed" if result.get('success') else "failed",
                "retry_id": retry_id,
                "original_workflow_id": workflow_id,
                "result": result,
                "message": "PublishScript byl dokončen" if result.get('success') else "PublishScript selhal"
            }
            
        except Exception as e:
            logger.error(f"❌ Chyba při spuštění PublishScript retry: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Chyba při spuštění retry: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chyba v retry_publish_script: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Neočekávaná chyba: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint pro monitoring"""
    return {"status": "healthy", "service": "seo-farm-backend"} 