import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
import requests
from openai import OpenAI
from temporalio import activity

logger = logging.getLogger(__name__)

# Import centralizovaného OpenAI clienta
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
    from openai_client import get_openai_client, call_openai_chat, call_openai_image
    CENTRALIZED_CLIENT_AVAILABLE = True
    logger.info("✅ Centralizovaný OpenAI client úspěšně importován")
except ImportError as e:
    logger.warning(f"⚠️ Centralizovaný OpenAI client není dostupný: {e}")
    CENTRALIZED_CLIENT_AVAILABLE = False



def get_api_key(service: str) -> str:
    """
    🚫 STRICT API KEY LOADING - žádné fallbacky
    Načte API klíč pro danou službu POUZE z backend API.
    
    Args:
        service: Název služby (např. "openai")
        
    Returns:
        API klíč
        
    Raises:
        Exception: Pokud API klíč není nalezen - pipeline se zastaví
    """
    if not service:
        raise Exception("Service name pro API klíč není specifikován - workflow nelze spustit")
    
    try:
        # POUZE backend API - žádné fallbacky na environment variables
        backend_url = os.getenv("API_BASE_URL")
        if not backend_url:
            raise Exception("API_BASE_URL environment variable není nastavena - workflow nelze spustit")
            
        response = requests.get(f"{backend_url}/api-keys/{service}", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            api_key = data.get("api_key")
            if api_key and api_key != "Not found":
                logger.info(f"✅ API klíč pro {service} načten z backend API")
                return api_key
        
        # Žádný fallback - hard fail
        raise Exception(f"API klíč pro službu {service} není dostupný v backend API (status: {response.status_code}) - workflow nelze spustit")
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Nelze připojit k backend API pro získání API klíče {service}: {e} - workflow nelze spustit")
    except Exception as e:
        raise Exception(f"Kritická chyba při načítání API klíče {service}: {e} - workflow nelze spustit")

@activity.defn
async def load_assistants_from_database(project_id: str) -> list:
    """
    Načte seznam asistentů pro daný projekt z databáze
    Používa SKUTEČNÉ asistenty vytvořené uživatelem v UI!
    """
    try:
        logger.info(f"🔄 Načítám asistenty z databáze pro projekt: {project_id}")
        
        if not project_id:
            error_msg = "❌ Project ID není specifikováno - workflow nelze spustit bez ID projektu"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 🔗 NAČTENÍ Z DATABÁZE přes backend API
        import requests
        import os
        
        # Sestavení URL pro backend API
        api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        url = f"{api_base_url}/api/assistant/{project_id}"
        
        logger.info(f"📡 Volám API: {url}")
        
        try:
            response = requests.get(url, timeout=30)
            
            # 🚫 EXPLICIT HTTP 404 CHECK - okamžité selhání pro neexistující projekt
            if response.status_code == 404:
                error_msg = f"❌ Projekt {project_id} neexistuje v databázi - workflow nelze spustit"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            response.raise_for_status()
            
            db_assistants = response.json()
            logger.info(f"✅ Načteno {len(db_assistants)} asistentů z databáze")
            
            if not db_assistants:
                error_msg = f"❌ Žádní asistenti nenalezeni v databázi pro projekt {project_id} - vytvořte asistenty přes UI"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # 🚫 STRICT CONVERSION - žádné fallbacky v databázových datech
            workflow_assistants = []
            for i, db_assistant in enumerate(db_assistants):
                
                # Strict validace každého asistenta z databáze
                function_key = db_assistant.get("functionKey")
                if not function_key:
                    raise Exception(f"❌ Asistent #{i+1} nemá functionKey - databáze je poškozená, workflow nelze spustit")
                
                name = db_assistant.get("name")
                if not name:
                    raise Exception(f"❌ Asistent {function_key} nemá název - databáze je poškozená, workflow nelze spustit")
                
                model_provider = db_assistant.get("model_provider")
                if not model_provider:
                    raise Exception(f"❌ Asistent {function_key} nemá model_provider - musí být nastaven v UI, workflow nelze spustit")
                
                model = db_assistant.get("model")
                if not model:
                    raise Exception(f"❌ Asistent {function_key} nemá model - musí být nastaven v UI, workflow nelze spustit")
                
                system_prompt = db_assistant.get("system_prompt")
                if not system_prompt:
                    raise Exception(f"❌ Asistent {function_key} nemá system_prompt - musí být nastaven v UI, workflow nelze spustit")
                
                order = db_assistant.get("order")
                if order is None:
                    raise Exception(f"❌ Asistent {function_key} nemá order - musí být nastaven v UI, workflow nelze spustit")
                
                temperature = db_assistant.get("temperature")
                if temperature is None:
                    raise Exception(f"❌ Asistent {function_key} nemá temperature - musí být nastavena v UI, workflow nelze spustit")
                
                max_tokens = db_assistant.get("max_tokens")
                if max_tokens is None:
                    raise Exception(f"❌ Asistent {function_key} nemá max_tokens - musí být nastaveno v UI, workflow nelze spustit")

                workflow_assistant = {
                    "id": function_key,
                    "name": name,
                    "function_key": function_key,
                    "slug": function_key,
                    "system_prompt": system_prompt,
                    "model_provider": model_provider,
                    "model": model,
                    "temperature": temperature,
                    "top_p": db_assistant.get("top_p"),  # Optional
                    "max_tokens": max_tokens,
                    "order": order,
                    "input_keys": ["topic"],  # Zjednodušený input
                    "output_keys": ["output"]  # Zjednodušený output
                }
                workflow_assistants.append(workflow_assistant)
            
            # Seřazení podle order
            workflow_assistants.sort(key=lambda x: x["order"])
            
            logger.info(f"🎯 NAČTENO Z DATABÁZE: {len(workflow_assistants)} asistentů")
            for assistant in workflow_assistants:
                logger.info(f"  {assistant['order']}. {assistant['name']} ({assistant['slug']})")
                
            return workflow_assistants
            
        except requests.exceptions.RequestException as e:
            error_msg = f"❌ Chyba při připojení k backend API: {e} - workflow nelze spustit bez přístupu k databázi"
            logger.error(error_msg)
            raise Exception(error_msg)
            
    except Exception as e:
        logger.error(f"❌ Kritická chyba při načítání asistentů: {str(e)}")
        raise  # Re-raise the exception - žádné fallbacky!

# Fallback funkce odstraněna - používáme STRICT error handling
# Pokud databáze selže, pipeline MUSÍ selhat!

@activity.defn
async def execute_assistant(args: dict) -> dict:
    """
    🚫 STRICT ASSISTANT EXECUTION - žádné fallbacky
    Spustí konkrétního asistenta s danou konfigurací
    
    Args:
        args: Dict obsahující:
            - assistant_config: dict - konfigurace asistenta
            - topic: str - téma pro zpracování
            - current_date: str - aktuální datum (optional)
            - previous_outputs: dict - předchozí výstupy (optional)
    """
    # STRICT INPUT VALIDATION
    if not args:
        raise Exception("❌ Args pro execute_assistant jsou prázdné - pipeline nelze spustit")
        
    assistant_config = args.get("assistant_config")
    if not assistant_config:
        raise Exception("❌ Assistant_config chybí v args - pipeline nelze spustit")
    
    topic = args.get("topic")
    if topic is None:
        raise Exception("❌ Topic chybí v args - pipeline nelze spustit")
    if not topic.strip():
        logger.warning(f"⚠️ Topic je prázdný pro {assistant_config.get('name', 'Unknown')} - pokračuji s prázdným stringem")
        topic = ""
    
    current_date = args.get("current_date")  # Optional
    previous_outputs = args.get("previous_outputs", {})  # Optional
    
    # STRICT ASSISTANT CONFIG VALIDATION
    assistant_name = assistant_config.get("name")
    if not assistant_name:
        raise Exception("❌ Asistent nemá name - konfigurace je neplatná, pipeline nelze spustit")
        
    function_key = assistant_config.get("function_key")
    if not function_key:
        raise Exception("❌ Asistent nemá function_key - konfigurace je neplatná, pipeline nelze spustit")
    
    try:
        logger.info(f"🤖 ======== EXECUTE_ASSISTANT START ========")
        logger.info(f"🤖 Spouštím asistenta: {assistant_name}")
        logger.info(f"📝 Function Key: {function_key}")
        logger.info(f"📅 Current Date: {current_date if current_date else 'Not provided'}")
        logger.info(f"📋 Input Topic: {topic[:500]}...")
        logger.info(f"📋 Input Length: {len(topic)} chars")
        logger.info(f"📋 Previous Outputs Keys: {list(previous_outputs.keys()) if previous_outputs else 'None'}")
        
        # 🚫 STRICT CONFIG VALIDATION - žádné fallbacky
        system_prompt = assistant_config.get("system_prompt")
        if not system_prompt:
            raise Exception(f"❌ Asistent {function_key} nemá system_prompt - musí být nastaven v UI, pipeline nelze spustit")
        
        model = assistant_config.get("model")
        if not model:
            raise Exception(f"❌ Asistent {function_key} nemá model - musí být nastaven v UI, pipeline nelze spustit")
        
        model_provider = assistant_config.get("model_provider")
        if not model_provider:
            raise Exception(f"❌ Asistent {function_key} nemá model_provider - musí být nastaven v UI, pipeline nelze spustit")
        
        temperature = assistant_config.get("temperature")
        if temperature is None:
            raise Exception(f"❌ Asistent {function_key} nemá temperature - musí být nastavena v UI, pipeline nelze spustit")
        
        max_tokens = assistant_config.get("max_tokens")
        if max_tokens is None:
            raise Exception(f"❌ Asistent {function_key} nemá max_tokens - musí být nastaveno v UI, pipeline nelze spustit")
        
        logger.info(f"🤖 ASSISTANT_CONFIG: model={model}, function_key={function_key}")
        logger.info(f"📝 PROMPT_LENGTH: {len(system_prompt)} chars, TOPIC_LENGTH: {len(topic)} chars")
        
        # 🔍 DEBUG: Úplný assistant_config
        logger.info(f"🔍 DEBUG ASSISTANT_CONFIG: {json.dumps(assistant_config, indent=2, default=str)}")
        
        # Inicializace výstupních proměnných
        output = ""
        total_tokens = 0
        
        try:
            # Heartbeat před dlouhým API voláním
            activity.heartbeat()
            
            # 🎨 ImageRendererAssistant používá DALL·E API
            if function_key == "image_renderer_assistant":
                logger.info(f"🎨 EXECUTING ImageRendererAssistant s DALL·E API")
                
                # 🚨 OPRAVA: Parsování JSON z MultimediaAssistant
                import re
                dalle_results = {"images": [], "model": "dall-e-3", "config": {}}
                
                try:
                    # Hledání JSON v markdown bloku nebo přímo v topic
                    json_match = re.search(r'\[(.*?)\]', topic, re.DOTALL)
                    if json_match:
                        json_str = '[' + json_match.group(1) + ']'
                        multimedia_data = json.loads(json_str)
                        logger.info(f"🎨 PARSED {len(multimedia_data)} image requests from MultimediaAssistant")
                        
                        api_key = get_api_key("openai")
                        client = OpenAI(api_key=api_key)
                        
                        # Generování obrázku pro každou image položku
                        for i, item in enumerate(multimedia_data):
                            if item.get('type') == 'image':
                                image_prompt = item.get('image_prompt', f"Professional image for: {topic}")
                                
                                # Limitace délky promptu pro DALL·E (max 1000 chars)
                                if len(image_prompt) > 1000:
                                    image_prompt = image_prompt[:997] + "..."
                                
                                logger.info(f"🎨 GENERATING IMAGE {i+1}: {image_prompt[:80]}...")
                                
                                # DALL·E 3 API volání
                                response = client.images.generate(
                                    model="dall-e-3",
                                    prompt=image_prompt,
                                    n=1,
                                    size="1024x1024",
                                    quality="standard",
                                    style="natural"
                                )
                                
                                # Přidání do výsledků
                                for img in response.data:
                                    dalle_results["images"].append({
                                        "url": img.url,
                                        "revised_prompt": img.revised_prompt if hasattr(img, 'revised_prompt') else image_prompt,
                                        "position": item.get('position', 'unknown'),
                                        "description": item.get('description', ''),
                                        "alt_text": item.get('alt_text', '')
                                    })
                        
                        logger.info(f"✅ Generated {len(dalle_results['images'])} images from JSON")
                        
                    else:
                        raise Exception("No JSON found in topic")
                        
                except Exception as parse_error:
                    logger.warning(f"⚠️ JSON parsing failed, using fallback: {parse_error}")
                    # Fallback na původní logiku
                    image_prompt = f"Create a professional, high-quality image related to: {topic}. Make it suitable for SEO blog article, clean and engaging visual style."
                    
                    if len(image_prompt) > 1000:
                        image_prompt = image_prompt[:997] + "..."
                    
                    logger.info(f"🎨 FALLBACK IMAGE_PROMPT: {image_prompt[:100]}...")
                    
                    api_key = get_api_key("openai")
                    client = OpenAI(api_key=api_key)
                    
                    # DALL·E 3 API volání
                    response = client.images.generate(
                        model="dall-e-3",
                        prompt=image_prompt,
                        n=1,
                        size="1024x1024",
                        quality="standard",
                        style="natural"
                    )
                    
                    # Pro fallback musíme zpracovat response
                    if not response.data:
                        raise Exception(f"❌ DALL-E API nevrátilo žádné obrázky pro {function_key} - pipeline selhal")
                    
                    for img in response.data:
                        if not img.url:
                            raise Exception(f"❌ DALL-E API vrátilo obrázek bez URL pro {function_key} - pipeline selhal")
                        
                        dalle_results["images"].append({
                            "url": img.url,
                            "revised_prompt": img.revised_prompt if hasattr(img, 'revised_prompt') else image_prompt,
                            "position": "main_article_image",
                            "description": f"AI generated image for: {topic}",
                            "alt_text": f"Professional image related to {topic}"
                        })
                
                # Heartbeat po DALL·E volání
                activity.heartbeat()
                
                logger.info(f"✅ DALL·E API response úspěšný!")
                logger.info(f"✅ Generated {len(dalle_results['images'])} images")
                
                # Formátování výstupu pro ImageRendererAssistant
                output = json.dumps({
                    "generated_images": dalle_results["images"],
                    "image_urls": [img["url"] for img in dalle_results["images"]],
                    "image_descriptions": [img.get("description", f"AI generated image for: {topic}") for img in dalle_results["images"]],
                    "alt_texts": [img.get("alt_text", f"Professional image related to {topic}") for img in dalle_results["images"]],
                    "positions": [img.get("position", "unknown") for img in dalle_results["images"]],
                    "prompts_used": [img.get("revised_prompt", "Unknown prompt") for img in dalle_results["images"]],
                    "model_used": dalle_results.get("model", "dall-e-3"),
                    "config": dalle_results.get("config", {})
                }, indent=2)
                
                total_tokens = 0  # DALL·E nepoužívá tokeny
                
            else:
                # 🤖 Multi-provider LLM asistenti (OpenAI, Claude, Gemini)
                # model_provider, temperature, max_tokens už jsou validovány výše
                top_p = assistant_config.get("top_p")  # Optional pro Claude/Gemini
                
                logger.info(f"🤖 EXECUTING {model_provider.upper()} asistent: {assistant_name}")
                logger.info(f"🎯 Provider: {model_provider}, Model: {model}, Temperature: {temperature}")
                
                try:
                    # Import LLM factory
                    import sys
                    import os
                    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
                    
                    from llm_clients.factory import LLMClientFactory
                    
                    # Vytvoření clienta pro daný provider
                    llm_client = LLMClientFactory.create_client(model_provider)
                    
                    # Příprava user_message s aktuálním datem
                    user_message = topic
                    if current_date:
                        user_message = f"📅 Aktuální datum: {current_date}\n\n{topic}"
                    
                    # 🚨 KRITICKÝ DEBUG PRO TOPIC CONTAMINATION
                    logger.info(f"🔍 CONTAMINATION_DEBUG: ===== {function_key} =====")
                    logger.info(f"🔍 RAW_TOPIC_INPUT: '{topic}'")
                    logger.info(f"🔍 FINAL_USER_MESSAGE: '{user_message}'")
                    logger.info(f"🔍 SYSTEM_PROMPT_START: '{system_prompt[:200]}...'")
                    
                    # Volání chat completion s provider-specific parametry
                    # Heartbeat před dlouhým LLM voláním (prevence CancelledError)
                    activity.heartbeat()
                    
                    if model_provider == "openai":
                        llm_result = await llm_client.chat_completion(
                            system_prompt=system_prompt,
                            user_message=user_message,
                            model=model,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            top_p=top_p
                        )
                    elif model_provider == "claude":
                        # Claude nepodporuje top_p
                        llm_result = await llm_client.chat_completion(
                            system_prompt=system_prompt,
                            user_message=user_message,
                            model=model,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                    elif model_provider == "gemini":
                        # Gemini má jiné parametry
                        llm_result = await llm_client.chat_completion(
                            system_prompt=system_prompt,
                            user_message=user_message,
                            model=model,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                    else:
                        raise Exception(f"Nepodporovaný provider: {model_provider}")
                    
                    # Heartbeat po LLM volání
                    activity.heartbeat()
                    
                    logger.info(f"✅ {model_provider.upper()} API response úspěšný!")
                    logger.info(f"✅ Model used: {llm_result['model']}")
                    logger.info(f"✅ Provider: {llm_result['provider']}")
                    logger.info(f"✅ Tokens used: {llm_result['usage']['total_tokens']}")
                    
                    # 🔍 DEBUG LLM RESULT STRUKTURA
                    logger.info(f"🔍 LLM_RESULT KEYS: {list(llm_result.keys())}")
                    logger.info(f"🔍 LLM_RESULT CONTENT: '{llm_result.get('content', 'MISSING_CONTENT')[:200]}...'")
                    
                    output = llm_result["content"]
                    total_tokens = llm_result["usage"]["total_tokens"]
                    
                except ImportError as e:
                    # 🚫 ŽÁDNÝ FALLBACK - pokud LLM Factory není dostupný, pipeline selže
                    raise Exception(f"❌ LLM Factory není dostupný - backend není správně nakonfigurován, pipeline nelze spustit: {e}")
                
                except Exception as e:
                    # 🚫 ŽÁDNÝ FALLBACK - pokud LLM client selže, pipeline selže
                    import traceback
                    logger.error(f"❌ {model_provider.upper()} API volání selhalo: {str(e)}")
                    logger.error(f"❌ FULL TRACEBACK pro {assistant_name}:")
                    logger.error(traceback.format_exc())
                    logger.error(f"❌ INPUT DATA - function_key: {function_key}")
                    logger.error(f"❌ INPUT DATA - topic: {topic[:200]}...")
                    logger.error(f"❌ INPUT DATA - model_provider: {model_provider}")
                    logger.error(f"❌ INPUT DATA - model: {model}")
                    logger.error(f"❌ INPUT DATA - system_prompt: {system_prompt[:200]}...")
                    raise Exception(f"❌ LLM client pro {model_provider} selhal - pipeline nelze spustit: {e}")
                
            logger.info(f"✅ Output délka: {len(output)} znaků")
        
        except Exception as e:
            logger.error(f"❌ OpenAI API volání selhalo!")
            logger.error(f"❌ Exception type: {type(e).__name__}")
            logger.error(f"❌ Exception message: {str(e)}")
            
            # Speciální handling pro různé typy chyb
            if "timeout" in str(e).lower():
                logger.error(f"⏰ TIMEOUT: OpenAI API volání překročilo časový limit")
            elif "connection" in str(e).lower():
                logger.error(f"🌐 CONNECTION: Problém s připojením k OpenAI API")
            elif "api_key" in str(e).lower() or "401" in str(e):
                logger.error(f"🔑 AUTH: Problém s API klíčem")
            elif "rate_limit" in str(e).lower() or "429" in str(e):
                logger.error(f"🚦 RATE_LIMIT: Překročen limit API volání")
            
            logger.error(f"❌ {assistant_name} selhal: {str(e)}")
            error_result = {
                "assistant_name": assistant_name,
                "function_key": function_key,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            raise Exception(f"Asistent {assistant_name} selhal: {str(e)}")
        
        # Příprava výsledku
        result = {
            "assistant_name": assistant_name,
            "function_key": function_key,
            "status": "completed",
            "output": output,
            "model_used": model,
            "tokens_used": total_tokens,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ {assistant_name} dokončen úspěšně")
        logger.info(f"📊 Použito tokenů: {result['tokens_used']}")
        logger.info(f"📄 Výstup délka: {len(output)} znaků")
        
        # 🚨 KRITICKÝ DEBUG LOG - potvrzení, že funkce doběhla až na konec
        logger.info(f"🎯 RETURNING RESULT: {assistant_name} - funkce execute_assistant() dokončena úspěšně, vracím result")
        logger.info(f"🎯 RESULT KEYS: {list(result.keys())}")
        logger.info(f"🎯 RESULT STATUS: {result.get('status', 'UNKNOWN')}")
        
        return result
        
    except Exception as e:
        import traceback
        logger.error(f"❌ ======== EXECUTE_ASSISTANT FAILED ========")
        logger.error(f"❌ {assistant_name} selhal: {str(e)}")
        logger.error(f"❌ FINAL TRACEBACK pro {assistant_name}:")
        logger.error(traceback.format_exc())
        logger.error(f"❌ ASSISTANT CONFIG na čase selhání:")
        logger.error(f"❌   function_key: {function_key}")
        logger.error(f"❌   assistant_name: {assistant_name}")
        logger.error(f"❌   topic_length: {len(topic) if topic else 0}")
        logger.error(f"❌ ======== EXECUTE_ASSISTANT END ========")
        error_result = {
            "assistant_name": assistant_name,
            "function_key": function_key,
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        raise Exception(f"Asistent {assistant_name} selhal v strict mode: {str(e)}")

@activity.defn
async def save_output_to_json(
    outputs: dict,
    topic: str,
    project_id: str
) -> dict:
    """
    Uloží finální výstupy do JSON souboru
    """
    try:
        logger.info(f"💾 Ukládám výstupy pro téma: {topic}")
        
        # Vytvoření výsledného JSON objektu
        result = {
            "topic": topic,
            "project_id": project_id,
            "timestamp": datetime.now().isoformat(),
            "assistants": outputs,
            "status": "completed"
        }
        
        # Pro development jen logujeme, v produkci by se ukládalo do databáze/souboru
        logger.info(f"📋 Finální výstup připraven ({len(str(result))} znaků)")
        logger.info(f"🤖 Počet asistentů: {len(outputs)}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Chyba při ukládání výstupů: {str(e)}")
        raise 