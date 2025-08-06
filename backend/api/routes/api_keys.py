import json
import logging
import os
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from cryptography.fernet import Fernet
import base64

router = APIRouter()
logger = logging.getLogger(__name__)

# JSON file path for persistent storage
API_KEYS_FILE = os.path.join(os.getcwd(), "api_keys.json")
ENCRYPTION_KEY_FILE = os.path.join(os.getcwd(), "encryption_key.txt")

# Pydantic models
class ApiKeyCreate(BaseModel):
    service: str
    api_key: str

class ApiKeyUpdate(BaseModel):
    api_key: str

class ApiKeyResponse(BaseModel):
    service: str
    masked_key: str
    created_at: str
    updated_at: str

class ApiKeysListResponse(BaseModel):
    api_keys: Dict[str, str]  # service -> masked_key
    total_count: int

def get_encryption_key() -> bytes:
    """
    Získá nebo vytvoří encryption key pro šifrování API klíčů.
    """
    key_env = os.getenv("API_KEYS_ENCRYPTION_KEY")
    
    if key_env:
        try:
            return base64.urlsafe_b64decode(key_env.encode())
        except Exception as e:
            logger.warning(f"⚠️ Neplatný encryption key v prostředí: {e}")
    
    # Pokus o načtení z persistent souboru
    try:
        if os.path.exists(ENCRYPTION_KEY_FILE):
            with open(ENCRYPTION_KEY_FILE, 'r', encoding='utf-8') as f:
                key_str = f.read().strip()
                if key_str:
                    logger.info("🔑 Encryption key načten z persistent souboru")
                    return base64.urlsafe_b64decode(key_str.encode())
    except Exception as e:
        logger.warning(f"⚠️ Chyba při načítání encryption key ze souboru: {e}")
    
    # Pro development generujeme nový klíč a uložíme ho
    key = Fernet.generate_key()
    key_str = base64.urlsafe_b64encode(key).decode()
    
    # Uložení do souboru pro persistent použití
    try:
        with open(ENCRYPTION_KEY_FILE, 'w', encoding='utf-8') as f:
            f.write(key_str)
        logger.info(f"🔑 Nový encryption key uložen do {ENCRYPTION_KEY_FILE}")
    except Exception as e:
        logger.error(f"❌ Chyba při ukládání encryption key: {e}")
    
    logger.warning("🔑 API_KEYS_ENCRYPTION_KEY není nastaveno - generuji nový klíč pro development")
    logger.warning(f"🔑 Development encryption key: {key_str}")
    logger.warning("⚠️ Pro produkci nastavte API_KEYS_ENCRYPTION_KEY v environment variables!")
    
    return key

def encrypt_api_key(api_key: str) -> str:
    """
    Zašifruje API klíč pomocí Fernet.
    """
    key = get_encryption_key()
    fernet = Fernet(key)
    encrypted = fernet.encrypt(api_key.encode())
    return base64.urlsafe_b64encode(encrypted).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """
    Dešifruje API klíč pomocí Fernet.
    """
    try:
        key = get_encryption_key()
        fernet = Fernet(key)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_key.encode())
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception as e:
        logger.error(f"❌ Chyba při dešifrování API klíče: {e}")
        raise

def mask_api_key(api_key: str) -> str:
    """
    Maskuje API klíč pro bezpečné zobrazení.
    """
    if len(api_key) <= 8:
        return "*" * len(api_key)
    
    # Pro velmi dlouhé klíče (> 100 znaků) zkrátíme výstup
    if len(api_key) > 100:
        return f"{api_key[:4]}{'*' * 20}...{api_key[-4:]}"
    
    # Standardní maskování pro normální klíče
    return f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"

def validate_api_key_format(service: str, api_key: str) -> bool:
    """
    Základní validace formátu API klíče podle služby.
    """
    if service.lower() == "openai":
        return api_key.startswith("sk-") and len(api_key) > 20
    elif service.lower() == "elevenlabs":
        return len(api_key) > 10  # ElevenLabs má různé formáty
    elif service.lower() == "heygen":
        return len(api_key) > 10
    elif service.lower() == "fal":
        # FAL.AI má dva formáty: fal-xxx nebo uuid:hash
        import re
        is_new_format = api_key.startswith("fal-")
        is_old_format = re.match(r"^[a-f0-9-]{36}:[a-f0-9]{32}$", api_key)
        return is_new_format or bool(is_old_format)
    else:
        return len(api_key) > 5  # Obecná validace

def load_api_keys_from_file() -> Dict[str, Any]:
    """
    Načte API klíče z JSON souboru.
    """
    try:
        if os.path.exists(API_KEYS_FILE):
            with open(API_KEYS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"❌ Chyba při načítání API klíčů ze souboru: {e}")
        return {}

def save_api_keys_to_file(api_keys_data: Dict[str, Any]) -> None:
    """
    Uloží API klíče do JSON souboru.
    """
    try:
        with open(API_KEYS_FILE, 'w', encoding='utf-8') as f:
            json.dump(api_keys_data, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 API klíče uloženy do souboru: {API_KEYS_FILE}")
    except Exception as e:
        logger.error(f"❌ Chyba při ukládání API klíčů do souboru: {e}")
        raise

# API Endpoints

@router.get("/api-keys", response_model=ApiKeysListResponse)
async def get_api_keys():
    """
    Vrátí seznam všech uložených API klíčů (s maskovanými hodnotami).
    """
    try:
        logger.info("🔑 Načítám seznam API klíčů...")
        
        # Načtení z JSON souboru
        stored_keys = load_api_keys_from_file()
        
        # Převedení na maskované klíče pro response
        masked_keys = {}
        for service, key_data in stored_keys.items():
            if isinstance(key_data, dict) and 'encrypted_key' in key_data:
                try:
                    # Dešifrování a maskování pro zobrazení
                    decrypted_key = decrypt_api_key(key_data['encrypted_key'])
                    masked_keys[service] = mask_api_key(decrypted_key)
                except Exception as e:
                    logger.warning(f"⚠️ Nelze dešifrovat klíč pro {service}: {e}")
                    masked_keys[service] = "CHYBA_DEŠIFROVÁNÍ"
        
        logger.info(f"✅ Načteno {len(masked_keys)} API klíčů")
        
        return ApiKeysListResponse(
            api_keys=masked_keys,
            total_count=len(masked_keys)
        )
        
    except Exception as e:
        logger.error(f"❌ Chyba při načítání API klíčů: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Chyba při načítání API klíčů: {str(e)}"
        )

@router.post("/api-keys")
async def create_or_update_api_key(api_key_data: ApiKeyCreate):
    """
    Vytvoří nebo aktualizuje API klíč pro zadanou službu.
    """
    try:
        service = api_key_data.service.lower()
        api_key = api_key_data.api_key.strip()
        
        logger.info(f"🔑 Ukládám API klíč pro službu: {service}")
        
        # Validace formátu klíče
        if not validate_api_key_format(service, api_key):
            logger.warning(f"⚠️ Neplatný formát API klíče pro službu {service}")
            raise HTTPException(
                status_code=400,
                detail=f"Neplatný formát API klíče pro službu {service}"
            )
        
        # Validace délky klíče
        if len(api_key) > 200:
            logger.warning(f"⚠️ API klíč pro službu {service} je příliš dlouhý ({len(api_key)} znaků)")
            raise HTTPException(
                status_code=400,
                detail=f"API klíč je příliš dlouhý (maximum 200 znaků, zadáno {len(api_key)})"
            )
        
        if len(api_key) < 10:
            logger.warning(f"⚠️ API klíč pro službu {service} je příliš krátký ({len(api_key)} znaků)")
            raise HTTPException(
                status_code=400,
                detail=f"API klíč je příliš krátký (minimum 10 znaků, zadáno {len(api_key)})"
            )
        
        # Šifrování klíče
        encrypted_key = encrypt_api_key(api_key)
        masked_key = mask_api_key(api_key)
        
        logger.info(f"🔐 API klíč zašifrován: {masked_key}")
        
        # Načtení existujících klíčů
        stored_keys = load_api_keys_from_file()
        
        # Přidání/aktualizace nového klíče
        now = datetime.now().isoformat()
        stored_keys[service] = {
            "encrypted_key": encrypted_key,
            "masked_key": masked_key,
            "created_at": stored_keys.get(service, {}).get("created_at", now),
            "updated_at": now
        }
        
        # Uložení do souboru
        save_api_keys_to_file(stored_keys)
        
        # TAKÉ uložení do environment variable pro okamžité použití
        env_var_name = f"{service.upper()}_API_KEY"
        os.environ[env_var_name] = api_key
        
        logger.info(f"✅ API klíč pro {service} uložen perzistentně i do environment jako {env_var_name}")
        
        return {
            "status": "success",
            "message": f"API klíč pro službu {service} byl úspěšně uložen",
            "service": service,
            "masked_key": masked_key,
            "env_var": env_var_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chyba při ukládání API klíče pro {api_key_data.service}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Chyba při ukládání API klíče: {str(e)}"
        )

@router.delete("/api-keys/{service}")
async def delete_api_key(service: str):
    """
    Smaže API klíč pro zadanou službu.
    """
    try:
        service = service.lower()
        logger.info(f"🗑️ Mažu API klíč pro službu: {service}")
        
        # Načtení existujících klíčů
        stored_keys = load_api_keys_from_file()
        
        if service not in stored_keys:
            raise HTTPException(
                status_code=404,
                detail=f"API klíč pro službu {service} nebyl nalezen"
            )
        
        # Smazání z uložených klíčů
        del stored_keys[service]
        
        # Uložení aktualizovaných dat
        save_api_keys_to_file(stored_keys)
        
        # Smazání z environment variables
        env_var_name = f"{service.upper()}_API_KEY"
        if env_var_name in os.environ:
            del os.environ[env_var_name]
        
        logger.info(f"✅ API klíč pro {service} byl smazán")
        
        return {
            "status": "success",
            "message": f"API klíč pro službu {service} byl úspěšně smazán"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chyba při mazání API klíče pro {service}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Chyba při mazání API klíče: {str(e)}"
        )

@router.get("/api-keys/{service}")
async def get_api_key(service: str):
    """
    Vrátí konkrétní API klíč pro službu (pouze pro interní použití worker).
    """
    try:
        service = service.lower()
        logger.info(f"🔍 Načítám API klíč pro službu: {service}")
        
        # Načtení z JSON souboru
        stored_keys = load_api_keys_from_file()
        
        if service not in stored_keys:
            logger.warning(f"⚠️ API klíč pro službu {service} nebyl nalezen v souboru")
            
            # Fallback na environment variable
            env_var_name = f"{service.upper()}_API_KEY"
            env_key = os.getenv(env_var_name)
            if env_key and env_key != "your-openai-api-key-here":
                logger.info(f"✅ API klíč pro {service} načten z environment variables")
                return {"api_key": env_key}
            
            return {"api_key": "Not found"}
        
        # Dešifrování klíče
        key_data = stored_keys[service]
        decrypted_key = decrypt_api_key(key_data['encrypted_key'])
        
        # Také nastavení do environment variable pro okamžité použití
        env_var_name = f"{service.upper()}_API_KEY"
        os.environ[env_var_name] = decrypted_key
        
        logger.info(f"✅ API klíč pro {service} načten z persistent storage")
        
        return {"api_key": decrypted_key}
        
    except Exception as e:
        logger.error(f"❌ Chyba při načítání API klíče pro {service}: {str(e)}")
        return {"api_key": "Not found"} 