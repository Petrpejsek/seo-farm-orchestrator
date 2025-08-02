from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import re
import json

from ..database import get_prisma_client

router = APIRouter(prefix="/api", tags=["projects"])

# Pydantic modely pro API
class ProjectCreate(BaseModel):
    name: str
    language: str = "cs"
    description: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    language: Optional[str] = None
    description: Optional[str] = None

class AssistantResponse(BaseModel):
    id: str
    projectId: str
    name: str
    functionKey: str
    inputType: str
    outputType: str
    order: int
    timeout: int
    heartbeat: int
    active: bool
    description: Optional[str] = None
    
    # LLM Provider & Model parametry
    model_provider: str
    model: str
    temperature: float
    top_p: float
    max_tokens: int
    system_prompt: Optional[str] = None
    
    # UX metadata pro admina
    use_case: Optional[str] = None
    style_description: Optional[str] = None
    pipeline_stage: Optional[str] = None
    
    createdAt: datetime
    updatedAt: datetime

class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: str
    language: str
    description: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
    assistants: List[AssistantResponse] = []

class ProjectListResponse(BaseModel):
    id: str
    name: str
    slug: str
    language: str
    description: Optional[str] = None
    createdAt: datetime
    assistantCount: int
    workflowRunCount: int

def generate_slug(name: str) -> str:
    """Generuje URL-friendly slug z názvu"""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')
    return slug

@router.get("/projects", response_model=List[ProjectListResponse])
async def get_projects():
    """Získání seznamu všech projektů"""
    try:
        prisma = await get_prisma_client()
        
        # Získání všech projektů s počty asistentů a workflow runs
        projects = await prisma.project.find_many(
            include={
                "assistants": True,
                "workflowRuns": True
            }
        )
        
        result = []
        for project in projects:
            result.append(ProjectListResponse(
                id=project.id,
                name=project.name,
                slug=project.slug,
                language=project.language,
                description=project.description,
                createdAt=project.createdAt,
                assistantCount=len(project.assistants),
                workflowRunCount=len(project.workflowRuns)
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání projektů: {str(e)}")

@router.post("/project", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    """Vytvoření nového projektu"""
    try:
        prisma = await get_prisma_client()
        
        # Generování slug
        base_slug = generate_slug(project.name)
        slug = base_slug
        
        # Kontrola unikátnosti slug
        counter = 1
        while True:
            existing_project = await prisma.project.find_unique(where={"slug": slug})
            if not existing_project:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Vytvoření projektu
        new_project = await prisma.project.create(
            data={
                "name": project.name,
                "slug": slug,
                "language": project.language,
                "description": project.description,
            }
        )
        
        return ProjectResponse(
            id=new_project.id,
            name=new_project.name,
            slug=new_project.slug,
            language=new_project.language,
            description=new_project.description,
            createdAt=new_project.createdAt,
            updatedAt=new_project.updatedAt,
            assistants=[]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při vytváření projektu: {str(e)}")

@router.get("/project/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Získání detailu projektu včetně asistentů"""
    try:
        prisma = await get_prisma_client()
        
        # Najdeme projekt s asistenty
        project = await prisma.project.find_unique(
            where={"id": project_id},
            include={
                "assistants": {
                    "order_by": {"order": "asc"}
                }
            }
        )
        
        if not project:
            raise HTTPException(status_code=404, detail="Projekt nenalezen")
        
        # Převod asistentů na response model s přidáním projectId
        assistants = [
            AssistantResponse(
                id=a.id,
                projectId=a.projectId,  # 🔥 KRITICKÁ OPRAVA: Přidáno projectId
                name=a.name,
                functionKey=a.functionKey,
                inputType=a.inputType,
                outputType=a.outputType,
                order=a.order,
                timeout=a.timeout,
                heartbeat=a.heartbeat,
                active=a.active,
                description=a.description,
                model_provider=a.model_provider,
                model=a.model,
                temperature=a.temperature,
                top_p=a.top_p,
                max_tokens=a.max_tokens,
                system_prompt=a.system_prompt,
                use_case=a.use_case,
                style_description=a.style_description,
                pipeline_stage=a.pipeline_stage,
                createdAt=a.createdAt,
                updatedAt=a.updatedAt
            ) for a in project.assistants
        ]
        
        return ProjectResponse(
            id=project.id,
            name=project.name,
            slug=project.slug,
            language=project.language,
            description=project.description,
            createdAt=project.createdAt,
            updatedAt=project.updatedAt,
            assistants=assistants
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání projektu: {str(e)}")

@router.put("/project/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project_update: ProjectUpdate):
    """Úprava existujícího projektu"""
    try:
        prisma = await get_prisma_client()
        
        # Kontrola existence projektu
        project = await prisma.project.find_unique(where={"id": project_id})
        if not project:
            raise HTTPException(status_code=404, detail="Projekt nenalezen")
        
        # Příprava update dat
        update_data = project_update.dict(exclude_unset=True)
        
        # Aktualizace slug pokud se změnil název
        if "name" in update_data:
            new_slug = generate_slug(update_data["name"])
            if new_slug != project.slug:
                # Kontrola unikátnosti nového slug
                counter = 1
                base_slug = new_slug
                while True:
                    existing_project = await prisma.project.find_unique(where={"slug": new_slug})
                    if not existing_project or existing_project.id == project_id:
                        break
                    new_slug = f"{base_slug}-{counter}"
                    counter += 1
                update_data["slug"] = new_slug
        
        # Aktualizace projektu
        updated_project = await prisma.project.update(
            where={"id": project_id},
            data=update_data,
            include={
                "assistants": {
                    "order_by": {"order": "asc"}
                }
            }
        )
        
        # Převod asistentů na response model
        assistants = [
            AssistantResponse(
                id=a.id,
                name=a.name,
                functionKey=a.functionKey,
                inputType=a.inputType,
                outputType=a.outputType,
                order=a.order,
                timeout=a.timeout,
                heartbeat=a.heartbeat,
                active=a.active,
                description=a.description
            ) for a in updated_project.assistants
        ]
        
        return ProjectResponse(
            id=updated_project.id,
            name=updated_project.name,
            slug=updated_project.slug,
            language=updated_project.language,
            description=updated_project.description,
            createdAt=updated_project.createdAt,
            updatedAt=updated_project.updatedAt,
            assistants=assistants
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při úpravě projektu: {str(e)}")

@router.delete("/project/{project_id}")
async def delete_project(project_id: str):
    """Smazání projektu a všech jeho asistentů"""
    try:
        prisma = await get_prisma_client()
        
        # Kontrola existence projektu
        project = await prisma.project.find_unique(where={"id": project_id})
        if not project:
            raise HTTPException(status_code=404, detail="Projekt nenalezen")
        
        # Smazání projektu (asistenti se smažou automaticky díky onDelete: Cascade)
        await prisma.project.delete(where={"id": project_id})
        
        return {"message": f"Projekt '{project.name}' byl úspěšně smazán"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání projektu: {str(e)}") 