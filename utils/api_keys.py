import requests
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def get_api_key(service: str) -> Optional[str]:
    """
    Načte API klíč pro danou službu z backendu nebo environment variables jako fallback.
    
    Args:
        service: Název služby (např. "openai")
        
    Returns:
        API klíč nebo None pokud není nalezen
    """
    try:
        # Pokus o načtení z backendu
        backend_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        response = requests.get(f"{backend_url}/api/api-keys/{service}", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            api_key = data.get("api_key")
            if api_key and api_key != "Not found":
                logger.info(f"✅ API klíč pro {service} načten z databáze")
                return api_key
        
        logger.warning(f"⚠️ API klíč pro {service} nenalezen v databázi, používám environment variable")
        
    except Exception as e:
        logger.warning(f"⚠️ Chyba při načítání API klíče z backendu: {str(e)}")
    
    # Fallback na environment variables
    env_key_name = f"{service.upper()}_API_KEY"
    env_key = os.getenv(env_key_name)
    
    if env_key:
        logger.info(f"✅ API klíč pro {service} načten z environment variable")
        return env_key
    
    logger.error(f"❌ API klíč pro {service} nenalezen ani v databázi ani v environment variables")
    return None 