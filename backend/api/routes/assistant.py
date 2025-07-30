from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from ..database import get_prisma_client

router = APIRouter(prefix="/api", tags=["assistants"])

# Pydantic modely pro API
class AssistantCreate(BaseModel):
    projectId: str
    name: str
    functionKey: str
    inputType: str = "string"
    outputType: str = "string"
    order: int
    timeout: int = 60
    heartbeat: int = 15
    active: bool = True
    description: Optional[str] = None
    
    # OpenAI parametry s defaulty
    model: str = "gpt-4o"
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 800
    system_prompt: Optional[str] = None
    
    # UX metadata pro admina
    use_case: Optional[str] = None
    style_description: Optional[str] = None
    pipeline_stage: Optional[str] = None
    
    @field_validator('model')
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validace OpenAI modelu"""
        allowed_models = ["gpt-4o", "gpt-4", "gpt-3.5-turbo"]
        if v not in allowed_models:
            raise ValueError(f"Model musí být jeden z: {', '.join(allowed_models)}")
        return v
    
    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validace temperature parametru"""
        if not 0.1 <= v <= 2.0:
            raise ValueError("Temperature musí být mezi 0.1 a 2.0")
        return round(v, 2)  # Zaokrouhlení na 2 desetinná místa
    
    @field_validator('top_p')
    @classmethod
    def validate_top_p(cls, v: float) -> float:
        """Validace top_p parametru"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Top_p musí být mezi 0.0 a 1.0")
        return round(v, 2)
    
    @field_validator('max_tokens')
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        """Validace max_tokens parametru"""
        if not 100 <= v <= 4000:
            raise ValueError("Max_tokens musí být mezi 100 a 4000")
        return v
    
    @field_validator('system_prompt')
    @classmethod
    def validate_system_prompt(cls, v: Optional[str]) -> Optional[str]:
        """Validace system_prompt parametru"""
        if v is not None:
            if len(v.strip()) == 0:
                return None  # Prázdný string převést na None
            if len(v) > 10000:
                raise ValueError("System prompt může mít maximálně 10000 znaků")
        return v
    
    @field_validator('style_description')
    @classmethod
    def validate_style_description(cls, v: Optional[str]) -> Optional[str]:
        """Validace style_description parametru"""
        if v is not None:
            if len(v.strip()) == 0:
                return None  # Prázdný string převést na None
            if len(v) > 1000:
                raise ValueError("Popis stylu může mít maximálně 1000 znaků")
        return v
    
    @field_validator('pipeline_stage')
    @classmethod
    def validate_pipeline_stage(cls, v: Optional[str]) -> Optional[str]:
        """Validace pipeline_stage parametru"""
        if v is not None:
            if len(v.strip()) == 0:
                return None  # Prázdný string převést na None
            allowed_stages = ["brief", "research", "factvalidation", "draft", "humanizer", "seo", "multimedia", "qa", "publish"]
            if v not in allowed_stages:
                raise ValueError(f"Pipeline stage musí být jeden z: {', '.join(allowed_stages)}")
        return v

class AssistantUpdate(BaseModel):
    name: Optional[str] = None
    functionKey: Optional[str] = None
    inputType: Optional[str] = None
    outputType: Optional[str] = None
    order: Optional[int] = None
    timeout: Optional[int] = None
    heartbeat: Optional[int] = None
    active: Optional[bool] = None
    description: Optional[str] = None
    
    # OpenAI parametry
    model: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    
    # UX metadata pro admina
    use_case: Optional[str] = None
    style_description: Optional[str] = None
    pipeline_stage: Optional[str] = None
    
    @field_validator('model')
    @classmethod
    def validate_model(cls, v: Optional[str]) -> Optional[str]:
        """Validace OpenAI modelu"""
        if v is not None:
            allowed_models = ["gpt-4o", "gpt-4", "gpt-3.5-turbo"]
            if v not in allowed_models:
                raise ValueError(f"Model musí být jeden z: {', '.join(allowed_models)}")
        return v
    
    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v: Optional[float]) -> Optional[float]:
        """Validace temperature parametru"""
        if v is not None:
            if not 0.1 <= v <= 2.0:
                raise ValueError("Temperature musí být mezi 0.1 a 2.0")
            return round(v, 2)
        return v
    
    @field_validator('top_p')
    @classmethod
    def validate_top_p(cls, v: Optional[float]) -> Optional[float]:
        """Validace top_p parametru"""
        if v is not None:
            if not 0.0 <= v <= 1.0:
                raise ValueError("Top_p musí být mezi 0.0 a 1.0")
            return round(v, 2)
        return v
    
    @field_validator('max_tokens')
    @classmethod
    def validate_max_tokens(cls, v: Optional[int]) -> Optional[int]:
        """Validace max_tokens parametru"""
        if v is not None:
            if not 100 <= v <= 4000:
                raise ValueError("Max_tokens musí být mezi 100 a 4000")
        return v
    
    @field_validator('system_prompt')
    @classmethod
    def validate_system_prompt(cls, v: Optional[str]) -> Optional[str]:
        """Validace system_prompt parametru"""
        if v is not None:
            if len(v.strip()) == 0:
                return None  # Prázdný string převést na None
            if len(v) > 10000:
                raise ValueError("System prompt může mít maximálně 10000 znaků")
        return v
    
    @field_validator('style_description')
    @classmethod
    def validate_style_description(cls, v: Optional[str]) -> Optional[str]:
        """Validace style_description parametru"""
        if v is not None:
            if len(v.strip()) == 0:
                return None  # Prázdný string převést na None
            if len(v) > 1000:
                raise ValueError("Popis stylu může mít maximálně 1000 znaků")
        return v
    
    @field_validator('pipeline_stage')
    @classmethod
    def validate_pipeline_stage(cls, v: Optional[str]) -> Optional[str]:
        """Validace pipeline_stage parametru"""
        if v is not None:
            if len(v.strip()) == 0:
                return None  # Prázdný string převést na None
            allowed_stages = ["brief", "research", "factvalidation", "draft", "humanizer", "seo", "multimedia", "qa", "publish"]
            if v not in allowed_stages:
                raise ValueError(f"Pipeline stage musí být jeden z: {', '.join(allowed_stages)}")
        return v

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
    
    # OpenAI parametry
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

# Předkonfigurované funkce dostupné pro asistenty
AVAILABLE_FUNCTIONS = {
    "brief_assistant": {
        "name": "BriefAssistant",
        "description": "Transformuje volně zadané téma na SEO-ready zadání s metadaty",
        "inputType": "string",
        "outputType": "dict",
        "defaultTimeout": 60,
        "defaultHeartbeat": 15
    },
    "research_assistant": {
        "name": "ResearchAssistant",
        "description": "Provádí online research a shromažďuje podklady k zadanému tématu",
        "inputType": "string",
        "outputType": "dict",
        "defaultTimeout": 120,
        "defaultHeartbeat": 30
    },
    "fact_validator_assistant": {
        "name": "FactValidatorAssistant",
        "description": "Validuje fakta a kontroluje přesnost informací v contentu",
        "inputType": "dict",
        "outputType": "dict",
        "defaultTimeout": 90,
        "defaultHeartbeat": 20
    },
    "draft_assistant": {
        "name": "DraftAssistant",
        "description": "Vytváří první draft článku na základě research dat a briefu",
        "inputType": "dict",
        "outputType": "string",
        "defaultTimeout": 180,
        "defaultHeartbeat": 45
    },
    "humanizer_assistant": {
        "name": "HumanizerAssistant",
        "description": "Humanizuje AI-generovaný content pro přirozenější čtení",
        "inputType": "string",
        "outputType": "string",
        "defaultTimeout": 120,
        "defaultHeartbeat": 30
    },
    "seo_assistant": {
        "name": "SEOAssistant",
        "description": "Optimalizuje content pro vyhledávače (meta tagy, klíčová slova, struktura)",
        "inputType": "string",
        "outputType": "string",
        "defaultTimeout": 90,
        "defaultHeartbeat": 20
    },
    "multimedia_assistant": {
        "name": "MultimediaAssistant",
        "description": "Generuje multimedia elementy (obrazky, video nápady, infografiky)",
        "inputType": "string",
        "outputType": "dict",
        "defaultTimeout": 150,
        "defaultHeartbeat": 35
    },
    "qa_assistant": {
        "name": "QAAssistant",
        "description": "Kontroluje kvalitu, gramatiku a konzistenci finálního obsahu",
        "inputType": "string",
        "outputType": "dict",
        "defaultTimeout": 90,
        "defaultHeartbeat": 20
    },
    "publish_assistant": {
        "name": "PublishAssistant",
        "description": "Připravuje content pro publikaci a zajišťuje finální formátování",
        "inputType": "dict",
        "outputType": "string",
        "defaultTimeout": 60,
        "defaultHeartbeat": 15
    },
    "generate_llm_friendly_content": {
        "name": "Content Generator",
        "description": "Generuje AI-friendly SEO obsah pomocí OpenAI Assistant",
        "inputType": "string",
        "outputType": "string",
        "defaultTimeout": 120,
        "defaultHeartbeat": 30
    },
    "inject_structured_markup": {
        "name": "Structured Markup",
        "description": "Přidávává JSON-LD schema markup",
        "inputType": "string",
        "outputType": "string",
        "defaultTimeout": 60,
        "defaultHeartbeat": 15
    },
    "enrich_with_entities": {
        "name": "Entity Enrichment",
        "description": "Obohacuje obsah o entity linking",
        "inputType": "string",
        "outputType": "string",
        "defaultTimeout": 60,
        "defaultHeartbeat": 15
    },
    "add_conversational_faq": {
        "name": "FAQ Generator",
        "description": "Přidává konverzační FAQ sekce",
        "inputType": "string",
        "outputType": "string",
        "defaultTimeout": 60,
        "defaultHeartbeat": 15
    },
    "save_output_to_json": {
        "name": "JSON Output Saver",
        "description": "Ukládá finální výstup do JSON souboru",
        "inputType": "dict",
        "outputType": "string",
        "defaultTimeout": 30,
        "defaultHeartbeat": 10
    }
}

@router.get("/assistant-functions")
async def get_available_functions():
    """Získání seznamu dostupných funkcí pro asistenty"""
    return {"functions": AVAILABLE_FUNCTIONS}

@router.post("/assistant", response_model=AssistantResponse)
async def create_assistant(assistant: AssistantCreate):
    """Vytvoření nového asistenta"""
    try:
        prisma = await get_prisma_client()
        
        # Kontrola existence projektu
        project = await prisma.project.find_unique(where={"id": assistant.projectId})
        if not project:
            raise HTTPException(status_code=404, detail="Projekt nenalezen")
        
        # Kontrola unikátnosti pořadí v rámci projektu
        existing_assistant = await prisma.assistant.find_first(
            where={
                "projectId": assistant.projectId,
                "order": assistant.order
            }
        )
        if existing_assistant:
            raise HTTPException(status_code=400, detail=f"Pořadí {assistant.order} už existuje v tomto projektu")
        
        # Kontrola validity funkce
        if assistant.functionKey not in AVAILABLE_FUNCTIONS:
            raise HTTPException(status_code=400, detail=f"Neznámá funkce: {assistant.functionKey}")
        
        # Vytvoření nového asistenta
        new_assistant = await prisma.assistant.create(
            data={
                "projectId": assistant.projectId,
                "name": assistant.name,
                "functionKey": assistant.functionKey,
                "inputType": assistant.inputType,
                "outputType": assistant.outputType,
                "order": assistant.order,
                "timeout": assistant.timeout,
                "heartbeat": assistant.heartbeat,
                "active": assistant.active,
                "description": assistant.description,
                
                # OpenAI parametry
                "model": assistant.model,
                "temperature": assistant.temperature,
                "top_p": assistant.top_p,
                "max_tokens": assistant.max_tokens,
                "system_prompt": assistant.system_prompt,
                
                # UX metadata
                "use_case": assistant.use_case,
                "style_description": assistant.style_description,
                "pipeline_stage": assistant.pipeline_stage,
            }
        )
        
        return AssistantResponse(**new_assistant.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při vytváření asistenta: {str(e)}")

@router.get("/assistant/{project_id}", response_model=List[AssistantResponse])
async def get_project_assistants(project_id: str):
    """Získání všech asistentů pro projekt"""
    try:
        prisma = await get_prisma_client()
        
        # Kontrola existence projektu
        project = await prisma.project.find_unique(where={"id": project_id})
        if not project:
            raise HTTPException(status_code=404, detail="Projekt nenalezen")
        
        # Získání asistentů seřazených podle pořadí
        assistants = await prisma.assistant.find_many(
            where={"projectId": project_id},
            order_by={"order": "asc"}
        )
        
        return [AssistantResponse(**assistant.dict()) for assistant in assistants]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání asistentů: {str(e)}")

@router.get("/assistant/detail/{assistant_id}", response_model=AssistantResponse)
async def get_assistant(assistant_id: str):
    """Získání detailu asistenta"""
    try:
        prisma = await get_prisma_client()
        
        assistant = await prisma.assistant.find_unique(where={"id": assistant_id})
        if not assistant:
            raise HTTPException(status_code=404, detail="Asistent nenalezen")
        
        return AssistantResponse(**assistant.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání asistenta: {str(e)}")

@router.put("/assistant/{assistant_id}", response_model=AssistantResponse)
async def update_assistant(assistant_id: str, assistant_update: AssistantUpdate):
    """Úprava existujícího asistenta"""
    try:
        prisma = await get_prisma_client()
        
        # Najdeme asistenta
        assistant = await prisma.assistant.find_unique(where={"id": assistant_id})
        if not assistant:
            raise HTTPException(status_code=404, detail="Asistent nenalezen")
        
        # Kontrola unikátnosti pořadí při změně
        if assistant_update.order is not None and assistant_update.order != assistant.order:
            existing_assistant = await prisma.assistant.find_first(
                where={
                    "projectId": assistant.projectId,
                    "order": assistant_update.order,
                    "id": {"not": assistant_id}
                }
            )
            if existing_assistant:
                raise HTTPException(status_code=400, detail=f"Pořadí {assistant_update.order} už existuje v tomto projektu")
        
        # Kontrola validity funkce
        if assistant_update.functionKey is not None and assistant_update.functionKey not in AVAILABLE_FUNCTIONS:
            raise HTTPException(status_code=400, detail=f"Neznámá funkce: {assistant_update.functionKey}")
        
        # Aktualizace asistenta
        update_data = assistant_update.dict(exclude_unset=True)
        updated_assistant = await prisma.assistant.update(
            where={"id": assistant_id},
            data=update_data
        )
        
        return AssistantResponse(**updated_assistant.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při úpravě asistenta: {str(e)}")

@router.delete("/assistant/{assistant_id}")
async def delete_assistant(assistant_id: str):
    """Smazání asistenta"""
    try:
        prisma = await get_prisma_client()
        
        # Najdeme asistenta
        assistant = await prisma.assistant.find_unique(where={"id": assistant_id})
        if not assistant:
            raise HTTPException(status_code=404, detail="Asistent nenalezen")
        
        # Smazání asistenta
        await prisma.assistant.delete(where={"id": assistant_id})
        
        return {"message": f"Asistent '{assistant.name}' byl úspěšně smazán"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání asistenta: {str(e)}")

@router.post("/assistant/reorder")
async def reorder_assistants(project_id: str, new_order: List[dict]):
    """Přeřazení pořadí asistentů v projektu
    
    Očekává: [{"assistantId": "uuid", "order": 1}, {"assistantId": "uuid", "order": 2}, ...]
    """
    try:
        prisma = await get_prisma_client()
        
        # Kontrola existence projektu
        project = await prisma.project.find_unique(where={"id": project_id})
        if not project:
            raise HTTPException(status_code=404, detail="Projekt nenalezen")
        
        # Validace dat
        assistant_ids = [item["assistantId"] for item in new_order]
        if len(assistant_ids) != len(set(assistant_ids)):
            raise HTTPException(status_code=400, detail="Duplicitní ID asistentů")
        
        orders = [item["order"] for item in new_order]
        if len(orders) != len(set(orders)):
            raise HTTPException(status_code=400, detail="Duplicitní pořadí")
        
        # Aktualizace pořadí
        for item in new_order:
            await prisma.assistant.update(
                where={"id": item["assistantId"]},
                data={"order": item["order"]}
            )
        
        return {"message": f"Pořadí asistentů bylo úspěšně aktualizováno"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při přeřazování asistentů: {str(e)}")

@router.post("/assistant/bulk-create/{project_id}")
async def bulk_create_assistants(project_id: str):
    """Vytvoření výchozích asistentů pro projekt"""
    try:
        prisma = await get_prisma_client()
        
        # Kontrola existence projektu
        project = await prisma.project.find_unique(where={"id": project_id})
        if not project:
            raise HTTPException(status_code=404, detail="Projekt nenalezen")
        
        # Kontrola, zda už nejsou asistenti vytvořeni
        existing_assistants = await prisma.assistant.find_many(
            where={"projectId": project_id}
        )
        if existing_assistants:
            return {"message": "Asistenti už existují", "count": len(existing_assistants)}
        
        # Definice výchozích asistentů
        default_assistants = [
            {
                "name": "BriefAssistant",
                "functionKey": "brief_assistant",
                "inputType": "string",
                "outputType": "dict",
                "order": 1,
                "timeout": 60,
                "heartbeat": 15,
                "active": True,
                "description": "Transformuje volně zadané téma na SEO-ready zadání s metadaty",
                "model": "gpt-4o",
                "temperature": 0.8,
                "top_p": 0.9,
                "max_tokens": 800,
                "system_prompt": "Jsi expert na SEO a content marketing. Tvým úkolem je transformovat volně zadaná témata na precizní SEO zadání s jasně definovanými metadaty. Zaměř se na search intent, target audience a keyword strategy."
            },
            {
                "name": "Content Generator",
                "functionKey": "generate_llm_friendly_content",
                "inputType": "string",
                "outputType": "string",
                "order": 2,
                "timeout": 120,
                "heartbeat": 30,
                "active": True,
                "description": "Generuje AI-friendly SEO obsah",
                "model": "gpt-4o",
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 2000,
                "system_prompt": "Jsi profesionální SEO copywriter. Vytváříš kvalitní, SEO-optimalizovaný obsah který je zároveň přirozeně čitelný pro uživatele. Dodržuj SEO best practices a E-A-T principy."
            },
            {
                "name": "Structured Markup",
                "functionKey": "inject_structured_markup",
                "inputType": "string",
                "outputType": "string",
                "order": 3,
                "timeout": 60,
                "heartbeat": 15,
                "active": True,
                "description": "Přidává JSON-LD schema",
                "model": "gpt-4o",
                "temperature": 0.3,
                "top_p": 0.8,
                "max_tokens": 1000,
                "system_prompt": "Jsi expert na strukturovaná data a JSON-LD schema markup. Tvým úkolem je přidat správné Schema.org markup do obsahu pro lepší SEO výsledky."
            },
            {
                "name": "JSON Output",
                "functionKey": "save_output_to_json",
                "inputType": "dict",
                "outputType": "string",
                "order": 4,
                "timeout": 30,
                "heartbeat": 10,
                "active": True,
                "description": "Ukládá finální výstup",
                "model": "gpt-4o",
                "temperature": 0.1,
                "top_p": 0.7,
                "max_tokens": 500,
                "system_prompt": "Jsi technický specialist pro export dat. Tvým úkolem je správně formátovat a uložit finální výstup do JSON struktury."
            }
        ]
        
        # Vytvoření asistentů
        created_assistants = []
        for assistant_data in default_assistants:
            assistant = await prisma.assistant.create(
                data={
                    **assistant_data,
                    "projectId": project_id
                }
            )
            created_assistants.append(assistant)
        
        return {
            "message": f"Vytvořeno {len(created_assistants)} výchozích asistentů",
            "count": len(created_assistants)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při vytváření výchozích asistentů: {str(e)}") 