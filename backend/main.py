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
        "http://localhost:3000",  # Frontend development server (primary)
        "http://localhost:3001",  # Frontend development server (fallback)
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
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
        # Nejdřív získáme základní výsledek workflow
        result_data = await get_workflow_result(workflow_id=workflow_id, run_id=run_id)
        
        # Aktualizace statusu v databázi na základě Temporal výsledku
        await update_workflow_status_in_database(workflow_id=workflow_id, run_id=run_id, result_data=result_data)
        
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
        
        logger.info(f"🔄 Aktualizuji status workflow v databázi: {workflow_id}")
        
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
        
        # Aktualizace v databázi
        updated_run = await prisma.workflowrun.update(
            where={"id": existing_run.id},
            data=update_fields
        )
        
        logger.info(f"✅ Workflow run aktualizován: {updated_run.status} ({updated_run.stageCount}/{updated_run.totalStages} stages)")
        
    except Exception as e:
        logger.error(f"⚠️ Chyba při aktualizaci workflow statusu v databázi: {str(e)}")
        # Nebudeme hadit exception, aby to nerozhodilo hlavní flow


@app.get("/health")
async def health_check():
    """Health check endpoint pro monitoring"""
    return {"status": "healthy", "service": "seo-farm-backend"} 