import requests
import os
import logging

logger = logging.getLogger(__name__)

def get_api_key(service: str) -> str:
    """
    Načte API klíč pro danou službu POUZE z backendu - STRICT MODE, žádné fallbacky.
    
    Args:
        service: Název služby (např. "openai")
        
    Returns:
        API klíč z databáze
        
    Raises:
        Exception: Pokud API klíč není nalezen v databázi
    """
    try:
        # Pokus o načtení z backendu
        backend_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        response = requests.get(f"{backend_url}/api-keys/{service}", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            api_key = data.get("api_key")
            if api_key and api_key != "Not found":
                logger.info(f"✅ API klíč pro {service} načten z databáze")
                return api_key
        
        # STRICT MODE - žádné fallbacky na environment variables
        raise Exception(f"❌ API klíč pro {service} nenalezen v databázi (HTTP {response.status_code})")
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"❌ Chyba při komunikaci s backendem pro API klíč {service}: {str(e)}")
    except Exception as e:
        if "API klíč" in str(e):
            raise  # Re-raise našich custom výjimek
        raise Exception(f"❌ Neočekávaná chyba při načítání API klíče {service}: {str(e)}") 