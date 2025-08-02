from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator, model_validator, Field, constr
from typing import Optional, Dict, Any, List, Annotated
from datetime import datetime
import uuid
import logging

from ..database import get_prisma_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["assistants"])

# Pydantic modely pro API
class AssistantCreate(BaseModel):
    projectId: str
    name: constr(min_length=1, strip_whitespace=True) = Field(description="Název asistenta nesmí být prázdný")
    functionKey: constr(min_length=1, strip_whitespace=True) = Field(description="Function key asistenta nesmí být prázdný")
    inputType: str = "string"
    outputType: str = "string"
    order: int
    timeout: int = 60
    heartbeat: int = 15
    active: bool = True
    description: Optional[str] = None
    
    # LLM Provider & Model parametry s defaulty
    model_provider: str = "openai"
    model: str = "gpt-4o"
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: Optional[int] = -1  # -1 = neomezeno, jinak kladné číslo
    system_prompt: Optional[str] = None
    
    # UX metadata pro admina
    use_case: Optional[str] = None
    style_description: Optional[str] = None
    pipeline_stage: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """🚫 STRICT NAME VALIDATION - žádné fallbacky, žádné whitespace"""
        if not v:
            raise ValueError("Název asistenta je povinný")
        v_stripped = v.strip()
        if len(v_stripped) == 0:
            raise ValueError("Název asistenta nesmí být prázdný nebo obsahovat pouze mezery")
        if len(v_stripped) < 1:
            raise ValueError("Název asistenta musí mít alespoň 1 znak")
        return v_stripped
    
    @field_validator('functionKey')
    @classmethod
    def validate_function_key(cls, v: str) -> str:
        """🚫 STRICT FUNCTION KEY VALIDATION - žádné fallbacky, žádné whitespace"""
        if not v:
            raise ValueError("Function key asistenta je povinný")
        v_stripped = v.strip()
        if len(v_stripped) == 0:
            raise ValueError("Function key asistenta nesmí být prázdný nebo obsahovat pouze mezery")
        if len(v_stripped) < 1:
            raise ValueError("Function key asistenta musí mít alespoň 1 znak")
        return v_stripped

    @field_validator('model_provider')
    @classmethod
    def validate_model_provider(cls, v: str) -> str:
        """🚫 STRICT MODEL PROVIDER VALIDATION - žádné fallbacky"""
        if not v:
            raise ValueError("Model provider je povinný")
        v_stripped = v.strip()
        if len(v_stripped) == 0:
            raise ValueError("Model provider nesmí být prázdný")
        allowed_providers = ["openai", "claude", "gemini"]
        if v_stripped.lower() not in allowed_providers:
            raise ValueError(f"Model provider musí být jeden z: {', '.join(allowed_providers)}")
        return v_stripped.lower()
    
    @field_validator('model')
    @classmethod
    def validate_model(cls, v: str, info) -> str:
        """🚫 STRICT MODEL VALIDATION - žádné fallbacky"""
        if not v:
            raise ValueError("Model je povinný")
        v_stripped = v.strip()
        if len(v_stripped) == 0:
            raise ValueError("Model nesmí být prázdný nebo obsahovat pouze mezery")
        
        # Import zde aby se předešlo circular imports
        try:
            from llm_clients.factory import LLMClientFactory
            
            # 🚫 STRICT - Provider MUSÍ být specifikován, žádný fallback
            provider = None
            if hasattr(info, 'data') and 'model_provider' in info.data:
                provider = info.data['model_provider']
            
            if not provider:
                raise ValueError("Model provider musí být specifikován před validací modelu")
            
            # Validace modelu pro daný provider
            if not LLMClientFactory.validate_model_for_provider(provider, v_stripped):
                supported_models = LLMClientFactory.get_all_models().get(provider, {})
                all_models = []
                for model_list in supported_models.values():
                    all_models.extend(model_list)
                raise ValueError(f"Model '{v_stripped}' není podporován providerem '{provider}'. Podporované: {all_models}")
        except ImportError as e:
            # 🚫 ŽÁDNÝ FALLBACK - pokud LLMClientFactory není dostupný, API nesmí fungovat
            raise ValueError(f"LLM Client Factory není dostupný - backend není správně nakonfigurován: {e}")
        
        return v_stripped
    
    @model_validator(mode='after')
    def validate_model_provider_compatibility(self) -> 'AssistantCreate':
        """Cross-field validace: model musí odpovídat model_provider"""
        if self.model and self.model_provider:
            try:
                from llm_clients.factory import LLMClientFactory
                
                if not LLMClientFactory.validate_model_for_provider(self.model_provider, self.model):
                    supported_models = LLMClientFactory.get_all_models().get(self.model_provider, {})
                    all_models = []
                    for model_list in supported_models.values():
                        all_models.extend(model_list)
                    
                    raise ValueError(f"Model '{self.model}' není kompatibilní s providerem '{self.model_provider}'. "
                                   f"Podporované modely pro {self.model_provider}: {all_models}")
            except ImportError as e:
                # 🚫 ŽÁDNÝ FALLBACK - pokud LLMClientFactory není dostupný, validace musí selhat
                raise ValueError(f"LLM Client Factory není dostupný pro cross-field validaci - backend není správně nakonfigurován: {e}")
        
        return self
    
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
    def validate_max_tokens(cls, v: Optional[int]) -> Optional[int]:
        """Validace max_tokens parametru - -1 = neomezeno, jinak kladné číslo"""
        if v is not None and v != -1 and v < 1:
            raise ValueError("Max_tokens musí být kladné číslo nebo -1 pro neomezeno")
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
    
    # LLM Provider & Model parametry
    model_provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    
    # UX metadata pro admina
    use_case: Optional[str] = None
    style_description: Optional[str] = None
    pipeline_stage: Optional[str] = None
    
    @field_validator('model_provider')
    @classmethod
    def validate_model_provider(cls, v: Optional[str]) -> Optional[str]:
        """Validace LLM provideru"""
        if v is not None:
            allowed_providers = ["openai", "claude", "gemini"]
            if v.lower() not in allowed_providers:
                raise ValueError(f"Model provider musí být jeden z: {', '.join(allowed_providers)}")
            return v.lower()
        return v

    @field_validator('model')
    @classmethod
    def validate_model(cls, v: Optional[str]) -> Optional[str]:
        """Validace modelu podle provideru (dynamická validace pro UPDATE)"""
        if v is not None:
            if not v or len(v.strip()) == 0:
                raise ValueError("Model nesmí být prázdný")
            
            # Pro UPDATE operace budeme tolerantnější - nemusíme mít přístup k model_provider
            # Základní validace: model musí být v seznamu všech podporovaných modelů
            try:
                from llm_clients.factory import LLMClientFactory
                
                all_models_dict = LLMClientFactory.get_all_models()
                all_models = []
                for provider_models in all_models_dict.values():
                    for model_list in provider_models.values():
                        all_models.extend(model_list)
                
                if v not in all_models:
                    raise ValueError(f"Model '{v}' není podporován žádným providerem. Podporované modely: {sorted(set(all_models))}")
                    
            except ImportError:
                # Fallback validace pokud LLMClientFactory není dostupný
                basic_models = ["gpt-4o", "gpt-4", "gpt-3.5-turbo", "dall-e-3", "dall-e-2", 
                              "claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307",
                              "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"]
                if v not in basic_models:
                    logger.warning(f"⚠️ Používám fallback validaci pro model: {v}")
                    raise ValueError(f"Model '{v}' není v seznamu fallback modelů: {basic_models}")
        
        return v
    
    @model_validator(mode='after')
    def validate_model_provider_compatibility(self) -> 'AssistantUpdate':
        """Cross-field validace: model musí odpovídat model_provider (pokud jsou oba zadané)"""
        if self.model and self.model_provider:
            try:
                from llm_clients.factory import LLMClientFactory
                
                if not LLMClientFactory.validate_model_for_provider(self.model_provider, self.model):
                    supported_models = LLMClientFactory.get_all_models().get(self.model_provider, {})
                    all_models = []
                    for model_list in supported_models.values():
                        all_models.extend(model_list)
                    
                    raise ValueError(f"Model '{self.model}' není kompatibilní s providerem '{self.model_provider}'. "
                                   f"Podporované modely pro {self.model_provider}: {all_models}")
            except ImportError:
                logger.warning("⚠️ LLMClientFactory nedostupný, přeskakuji cross-field validaci pro UPDATE")
        
        return self
    
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
        """Validace max_tokens parametru - -1 = neomezeno, jinak kladné číslo"""
        if v is not None and v != -1 and v < 1:
            raise ValueError("Max_tokens musí být kladné číslo nebo -1 pro neomezeno")
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
            allowed_stages = ["brief", "research", "factvalidation", "draft", "humanizer", "seo", "multimedia", "qa", "image", "publish"]
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

async def get_available_function_keys():
    """Získání seznam funkčních klíčů ze všech asistentů v databázi"""
    try:
        prisma = await get_prisma_client()
        
        # Získání unikátních function keys ze všech asistentů
        assistants = await prisma.assistant.find_many(
            distinct=['functionKey']
        )
        
        # Vytvoření formátu kompatibilního s frontend
        functions = {}
        for assistant in assistants:
            functions[assistant.functionKey] = {
                "name": assistant.name,
                "description": assistant.description or f"AI asistent typu {assistant.name}",
                "inputType": assistant.inputType,
                "outputType": assistant.outputType,
                "defaultTimeout": assistant.timeout or 60,
                "defaultHeartbeat": assistant.heartbeat or 15
            }
        
        return functions
        
    except Exception as e:
        # Fallback v případě chyby databáze - vrátí prázdný seznam
        logger.error(f"❌ Chyba při načítání function keys z databáze: {str(e)}")
        return {}

@router.get("/assistant-functions")
async def get_available_functions():
    """Získání seznamu dostupných funkcí pro asistenty z databáze"""
    functions = await get_available_function_keys()
    return {"functions": functions}

@router.get("/llm-providers")
async def get_llm_providers():
    """Získání seznamu podporovaných LLM providerů"""
    try:
        from llm_clients.factory import LLMClientFactory
        
        providers = LLMClientFactory.get_supported_providers()
        all_models = LLMClientFactory.get_all_models()
        
        # Vytvoří strukturu pro frontend
        provider_data = {}
        for provider in providers:
            provider_data[provider] = {
                "name": provider.title(),
                "models": all_models.get(provider, {"text": [], "image": []}),
                "supported_parameters": LLMClientFactory.get_provider_parameters(provider)
            }
        
        return {
            "providers": provider_data,
            "default_provider": "openai"
        }
        
    except Exception as e:
        logger.error(f"❌ Chyba při načítání LLM providerů: {str(e)}")
        # Fallback data
        return {
            "providers": {
                "openai": {
                    "name": "OpenAI",
                    "models": {
                        "text": ["gpt-4o", "gpt-4", "gpt-3.5-turbo"],
                        "image": ["dall-e-3", "dall-e-2"]
                    },
                    "supported_parameters": ["temperature", "max_tokens", "top_p", "system_prompt"]
                }
            },
            "default_provider": "openai"
        }

@router.get("/llm-providers/{provider}/models")
async def get_provider_models(provider: str):
    """Získání modelů pro konkrétní provider"""
    try:
        from llm_clients.factory import LLMClientFactory
        
        provider = provider.lower()
        if provider not in LLMClientFactory.get_supported_providers():
            raise HTTPException(
                status_code=404, 
                detail=f"Provider '{provider}' není podporován"
            )
        
        all_models = LLMClientFactory.get_all_models()
        models = all_models.get(provider, {"text": [], "image": []})
        parameters = LLMClientFactory.get_provider_parameters(provider)
        
        return {
            "provider": provider,
            "models": models,
            "supported_parameters": parameters
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chyba při načítání modelů pro {provider}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Chyba při načítání modelů: {str(e)}"
        )

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
        
        # 🚫 STRICT VALIDACE - žádné fallbacky pro kritická pole
        # Pydantic constr validace už kontroluje prázdné stringy, ale ponecháváme explicitní kontroly pro jistotu
        
        if not assistant.functionKey or len(assistant.functionKey.strip()) == 0:
            raise HTTPException(status_code=400, detail="Function key asistenta je povinný a nesmí být prázdný")
        
        if not assistant.model_provider or len(assistant.model_provider.strip()) == 0:
            raise HTTPException(status_code=400, detail="Model provider je povinný a nesmí být prázdný")
        
        if not assistant.model or len(assistant.model.strip()) == 0:
            raise HTTPException(status_code=400, detail="Model je povinný a nesmí být prázdný")
        
        # 🔧 SPECIÁLNÍ HANDLING PRO max_tokens při vytváření:
        # Pokud frontend nepošle max_tokens (prázdné pole), použijeme -1 pro "neomezeno"
        max_tokens_value = assistant.max_tokens if assistant.max_tokens is not None else -1
        
        # Vytvoření nového asistenta s trimovanými hodnotami
        new_assistant = await prisma.assistant.create(
            data={
                "projectId": assistant.projectId,
                "name": assistant.name.strip(),
                "functionKey": assistant.functionKey.strip(),
                "inputType": assistant.inputType,
                "outputType": assistant.outputType,
                "order": assistant.order,
                "timeout": assistant.timeout,
                "heartbeat": assistant.heartbeat,
                "active": assistant.active,
                "description": assistant.description,
                
                # LLM Provider & Model parametry
                "model_provider": assistant.model_provider.strip(),
                "model": assistant.model.strip(),
                "temperature": assistant.temperature,
                "top_p": assistant.top_p,
                "max_tokens": max_tokens_value,  # NULL pokud nebyl poslán nebo je None
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
            order={"order": "asc"}
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
        
        # 🚫 STRICT VALIDACE pro update - žádné fallbacky pro kritická pole
        if assistant_update.name is not None and (not assistant_update.name or len(assistant_update.name.strip()) == 0):
            raise HTTPException(status_code=400, detail="Název asistenta nesmí být prázdný")
        
        if assistant_update.functionKey is not None and (not assistant_update.functionKey or len(assistant_update.functionKey.strip()) == 0):
            raise HTTPException(status_code=400, detail="Function key asistenta nesmí být prázdný")
        
        if assistant_update.model_provider is not None and (not assistant_update.model_provider or len(assistant_update.model_provider.strip()) == 0):
            raise HTTPException(status_code=400, detail="Model provider nesmí být prázdný")
        
        if assistant_update.model is not None and (not assistant_update.model or len(assistant_update.model.strip()) == 0):
            raise HTTPException(status_code=400, detail="Model nesmí být prázdný")
        
        # Aktualizace asistenta
        update_data = assistant_update.dict(exclude_unset=True)
        
        # 🔧 SPECIÁLNÍ HANDLING PRO max_tokens: 
        # Pokud frontend nepošle max_tokens (prázdné pole), nastavíme explicitně -1 pro "neomezeno"
        if 'max_tokens' not in update_data:  # frontend neposlal max_tokens vůbec
            update_data['max_tokens'] = -1  # explicitně nastavíme -1 = neomezeno
        
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
        
        # STRIKTNÍ PŘÍSTUP: Žádné hardcoded výchozí asistenti
        # Uživatel musí explicitně vytvořit asistenty podle své konfigurace
        raise HTTPException(
            status_code=400, 
            detail="Automatické vytváření výchozích asistentů není podporováno. "
                   "Prosím, vytvořte asistenty manuálně podle vaší konfigurace projektu. "
                   "Tím zajistíte přesnou shodu mezi UI a workflow konfigurací."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při vytváření výchozích asistentů: {str(e)}") 