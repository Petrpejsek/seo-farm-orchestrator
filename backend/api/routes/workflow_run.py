from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import logging

from ..database import get_prisma_client

# Nastavení loggingu
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["workflow-runs"])

# Pydantic modely pro API
class WorkflowRunCreate(BaseModel):
    projectId: str
    topic: str
    runId: str  # Temporal runId
    workflowId: str  # Temporal workflowId

class WorkflowRunUpdate(BaseModel):
    status: Optional[str] = None
    finishedAt: Optional[datetime] = None
    outputPath: Optional[str] = None
    resultJson: Optional[dict] = None
    errorMessage: Optional[str] = None
    elapsedSeconds: Optional[int] = None
    stageCount: Optional[int] = None
    totalStages: Optional[int] = None

class WorkflowRunResponse(BaseModel):
    id: str
    projectId: str
    runId: str
    workflowId: str
    topic: str
    status: str
    startedAt: datetime
    finishedAt: Optional[datetime] = None
    outputPath: Optional[str] = None
    resultJson: Optional[dict] = None
    errorMessage: Optional[str] = None
    elapsedSeconds: Optional[int] = None
    stageCount: Optional[int] = None
    totalStages: Optional[int] = None
    createdAt: datetime
    updatedAt: datetime

class WorkflowRunListResponse(BaseModel):
    id: str
    projectId: str
    projectName: str
    runId: str
    workflowId: str
    topic: str
    status: str
    startedAt: datetime
    finishedAt: Optional[datetime] = None
    elapsedSeconds: Optional[int] = None
    stageCount: Optional[int] = None
    totalStages: Optional[int] = None

def calculate_elapsed_seconds(started_at: datetime, finished_at: Optional[datetime] = None) -> int:
    """Vypočítá uplynulé sekundy mezi startem a koncem (nebo aktuálním časem)"""
    from datetime import timezone
    
    # Zajistíme timezone kompatibilitu
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    
    if finished_at:
        if finished_at.tzinfo is None:
            finished_at = finished_at.replace(tzinfo=timezone.utc)
        end_time = finished_at
    else:
        end_time = datetime.now(timezone.utc)
    
    return int((end_time - started_at).total_seconds())

@router.post("/workflow-run", response_model=WorkflowRunResponse)
async def create_workflow_run(workflow_run: WorkflowRunCreate):
    """Vytvoření nového záznamu o workflow běhu v databázi"""
    try:
        logger.info(f"🏃 Vytvářím workflow run v databázi:")
        logger.info(f"   📋 Topic: {workflow_run.topic}")
        logger.info(f"   🏗️ Project ID: {workflow_run.projectId}")
        logger.info(f"   🆔 Workflow ID: {workflow_run.workflowId}")
        logger.info(f"   🏃 Run ID: {workflow_run.runId}")
        
        prisma = await get_prisma_client()
        
        # Kontrola existence projektu
        project = await prisma.project.find_unique(where={"id": workflow_run.projectId})
        if not project:
            logger.error(f"❌ Projekt {workflow_run.projectId} neexistuje")
            raise HTTPException(status_code=404, detail="Projekt nenalezen")
        
        # Kontrola unikátnosti Temporal identifikátorů
        existing_run = await prisma.workflowrun.find_unique(
            where={
                "workflowId_runId": {
                    "workflowId": workflow_run.workflowId,
                    "runId": workflow_run.runId
                }
            }
        )
        if existing_run:
            logger.error(f"❌ Workflow run s identifikátory už existuje")
            raise HTTPException(status_code=400, detail="Workflow run s těmito identifikátory už existuje")
        
        # Vytvoření nového workflow run záznamu v databázi
        new_run = await prisma.workflowrun.create(
            data={
                "projectId": workflow_run.projectId,
                "runId": workflow_run.runId,
                "workflowId": workflow_run.workflowId,
                "topic": workflow_run.topic,
                "status": "CREATED"
            }
        )
        
        logger.info(f"✅ Workflow run vytvořen v databázi s ID: {new_run.id}")
        
        return WorkflowRunResponse(
            id=new_run.id,
            projectId=new_run.projectId,
            runId=new_run.runId,
            workflowId=new_run.workflowId,
            topic=new_run.topic,
            status=new_run.status,
            startedAt=new_run.startedAt,
            finishedAt=new_run.finishedAt,
            outputPath=new_run.outputPath,
            resultJson=new_run.resultJson,
            errorMessage=new_run.errorMessage,
            elapsedSeconds=new_run.elapsedSeconds,
            stageCount=new_run.stageCount,
            totalStages=new_run.totalStages,
            createdAt=new_run.createdAt,
            updatedAt=new_run.updatedAt
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chyba při vytváření workflow run v databázi: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chyba při vytváření workflow run: {str(e)}")

@router.get("/workflow-runs", response_model=List[WorkflowRunListResponse])
async def get_workflow_runs(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """Získání seznamu workflow běhů z databáze s možností filtrování"""
    try:
        logger.info(f"📋 Načítám workflow runs z databáze:")
        logger.info(f"   🏗️ Project filter: {project_id}")
        logger.info(f"   📊 Status filter: {status}")
        logger.info(f"   📏 Limit: {limit}")
        
        prisma = await get_prisma_client()
        
        # Sestavení WHERE podmínky pro filtrování
        where_conditions = {}
        if project_id:
            where_conditions["projectId"] = project_id
        if status:
            where_conditions["status"] = status
        
        # FALLBACK: RAW SQL pro správné ordering - Prisma nefunguje
        if project_id and status:
            sql_where = f'WHERE "projectId" = \'{project_id}\' AND status = \'{status}\''
        elif project_id:
            sql_where = f'WHERE "projectId" = \'{project_id}\''
        elif status:
            sql_where = f'WHERE status = \'{status}\''
        else:
            sql_where = ''
            
        workflow_runs_raw = await prisma.query_raw(
            f'''
            SELECT wr.*, p.name as project_name
            FROM workflow_runs wr
            LEFT JOIN projects p ON wr."projectId" = p.id
            {sql_where}
            ORDER BY wr."startedAt" DESC
            LIMIT {limit}
            '''
        )
        
        # Konverze raw results na Prisma objekty
        workflow_runs = []
        for raw_run in workflow_runs_raw:
            # Vytvoření mock Prisma objektu pro kompatibilitu
            mock_run = type('MockRun', (), {
                'id': raw_run['id'],
                'projectId': raw_run['projectId'],
                'runId': raw_run['runId'],
                'workflowId': raw_run['workflowId'],
                'topic': raw_run['topic'],
                'status': raw_run['status'],
                'startedAt': raw_run['startedAt'],
                'finishedAt': raw_run['finishedAt'],
                'elapsedSeconds': raw_run['elapsedSeconds'],
                'stageCount': raw_run['stageCount'],
                'totalStages': raw_run['totalStages'],
                'project': type('MockProject', (), {'name': raw_run['project_name']})()
            })()
            workflow_runs.append(mock_run)
        
        logger.info(f"✅ Načteno {len(workflow_runs)} workflow runs z databáze")
        
        # Sestavení response s vypočítanými elapsed seconds
        result = []
        for run in workflow_runs:
            # Výpočet elapsed seconds pro běžící workflow
            elapsed_seconds = run.elapsedSeconds
            if run.status in ["RUNNING", "CREATED"] and run.finishedAt is None:
                elapsed_seconds = calculate_elapsed_seconds(run.startedAt)
            
            result.append(WorkflowRunListResponse(
                id=run.id,
                projectId=run.projectId,
                projectName=run.project.name,
                runId=run.runId,
                workflowId=run.workflowId,
                topic=run.topic,
                status=run.status,
                startedAt=run.startedAt,
                finishedAt=run.finishedAt,
                elapsedSeconds=elapsed_seconds,
                stageCount=run.stageCount,
                totalStages=run.totalStages
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Chyba při načítání workflow runs z databáze: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chyba při načítání workflow běhů: {str(e)}")

@router.get("/workflow-run/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(run_id: str):
    """Získání detailu workflow běhu podle ID z databáze"""
    try:
        logger.info(f"🔍 Hledám workflow run v databázi: {run_id}")
        
        prisma = await get_prisma_client()
        run = await prisma.workflowrun.find_unique(where={"id": run_id})
        
        if not run:
            logger.warning(f"⚠️ Workflow run {run_id} nenalezen v databázi")
            raise HTTPException(status_code=404, detail="Workflow run nenalezen")
        
        logger.info(f"✅ Workflow run nalezen: {run.topic}")
        
        return WorkflowRunResponse(
            id=run.id,
            projectId=run.projectId,
            runId=run.runId,
            workflowId=run.workflowId,
            topic=run.topic,
            status=run.status,
            startedAt=run.startedAt,
            finishedAt=run.finishedAt,
            outputPath=run.outputPath,
            resultJson=run.resultJson,
            errorMessage=run.errorMessage,
            elapsedSeconds=run.elapsedSeconds,
            stageCount=run.stageCount,
            totalStages=run.totalStages,
            createdAt=run.createdAt,
            updatedAt=run.updatedAt
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chyba při načítání workflow run {run_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chyba při načítání workflow běhu: {str(e)}")

@router.put("/workflow-run/{run_id}", response_model=WorkflowRunResponse)
async def update_workflow_run(run_id: str, update_data: WorkflowRunUpdate):
    """Aktualizace workflow běhu v databázi"""
    try:
        logger.info(f"📝 Aktualizuji workflow run v databázi: {run_id}")
        
        prisma = await get_prisma_client()
        
        # Kontrola existence
        existing_run = await prisma.workflowrun.find_unique(where={"id": run_id})
        if not existing_run:
            logger.warning(f"⚠️ Workflow run {run_id} nenalezen pro update")
            raise HTTPException(status_code=404, detail="Workflow run nenalezen")
        
        # Příprava dat pro update (pouze fields které nejsou None)
        update_fields = {}
        if update_data.status is not None:
            update_fields["status"] = update_data.status
        if update_data.finishedAt is not None:
            update_fields["finishedAt"] = update_data.finishedAt
        if update_data.outputPath is not None:
            update_fields["outputPath"] = update_data.outputPath
        if update_data.resultJson is not None:
            update_fields["resultJson"] = str(update_data.resultJson) if update_data.resultJson else None
        if update_data.errorMessage is not None:
            update_fields["errorMessage"] = update_data.errorMessage
        if update_data.elapsedSeconds is not None:
            update_fields["elapsedSeconds"] = update_data.elapsedSeconds
        if update_data.stageCount is not None:
            update_fields["stageCount"] = update_data.stageCount
        if update_data.totalStages is not None:
            update_fields["totalStages"] = update_data.totalStages
        
        # Update v databázi
        updated_run = await prisma.workflowrun.update(
            where={"id": run_id},
            data=update_fields
        )
        
        logger.info(f"✅ Workflow run aktualizován: {updated_run.status}")
        
        return WorkflowRunResponse(
            id=updated_run.id,
            projectId=updated_run.projectId,
            runId=updated_run.runId,
            workflowId=updated_run.workflowId,
            topic=updated_run.topic,
            status=updated_run.status,
            startedAt=updated_run.startedAt,
            finishedAt=updated_run.finishedAt,
            outputPath=updated_run.outputPath,
            resultJson=updated_run.resultJson,
            errorMessage=updated_run.errorMessage,
            elapsedSeconds=updated_run.elapsedSeconds,
            stageCount=updated_run.stageCount,
            totalStages=updated_run.totalStages,
            createdAt=updated_run.createdAt,
            updatedAt=updated_run.updatedAt
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chyba při aktualizaci workflow run {run_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chyba při aktualizaci workflow běhu: {str(e)}")

@router.delete("/workflow-run/{run_id}")
async def delete_workflow_run(run_id: str):
    """Smazání workflow běhu z databáze"""
    try:
        logger.info(f"🗑️ Mažu workflow run z databáze: {run_id}")
        
        prisma = await get_prisma_client()
        
        # Kontrola existence
        existing_run = await prisma.workflowrun.find_unique(where={"id": run_id})
        if not existing_run:
            logger.warning(f"⚠️ Workflow run {run_id} nenalezen pro smazání")
            raise HTTPException(status_code=404, detail="Workflow run nenalezen")
        
        # Smazání z databáze
        await prisma.workflowrun.delete(where={"id": run_id})
        
        logger.info(f"✅ Workflow run {run_id} smazán z databáze")
        
        return {"message": "Workflow run byl úspěšně smazán", "id": run_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chyba při mazání workflow run {run_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chyba při mazání workflow běhu: {str(e)}")

@router.get("/projects/{project_id}/workflow-runs", response_model=List[WorkflowRunListResponse])
async def get_project_workflow_runs(project_id: str, limit: int = 50):
    """Získání workflow běhů pro konkrétní projekt z databáze"""
    try:
        logger.info(f"📋 Načítám workflow runs pro projekt {project_id} z databáze")
        
        prisma = await get_prisma_client()
        
        # Kontrola existence projektu
        project = await prisma.project.find_unique(where={"id": project_id})
        if not project:
            logger.warning(f"⚠️ Projekt {project_id} nenalezen")
            raise HTTPException(status_code=404, detail="Projekt nenalezen")
        
        # Načtení workflow runs pro projekt - ORDER BY startedAt DESC
        workflow_runs = await prisma.workflowrun.find_many(
            where={"projectId": project_id},
            include={"project": True},
            take=limit,
            order={"startedAt": "Desc"}
        )
        
        logger.info(f"✅ Načteno {len(workflow_runs)} workflow runs pro projekt {project.name}")
        
        # Sestavení response s vypočítanými elapsed seconds
        result = []
        for run in workflow_runs:
            elapsed_seconds = run.elapsedSeconds
            if run.status in ["RUNNING", "CREATED"] and run.finishedAt is None:
                elapsed_seconds = calculate_elapsed_seconds(run.startedAt)
            
            result.append(WorkflowRunListResponse(
                id=run.id,
                projectId=run.projectId,
                projectName=run.project.name,
                runId=run.runId,
                workflowId=run.workflowId,
                topic=run.topic,
                status=run.status,
                startedAt=run.startedAt,
                finishedAt=run.finishedAt,
                elapsedSeconds=elapsed_seconds,
                stageCount=run.stageCount,
                totalStages=run.totalStages
            ))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chyba při načítání workflow runs pro projekt {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chyba při načítání workflow běhů: {str(e)}") 