import json
import logging
import os
from datetime import datetime
from typing import Dict, Any
import requests
from openai import OpenAI
from temporalio import activity

logger = logging.getLogger(__name__)

def get_api_key(service: str) -> str:
    """
    Načte API klíč pro danou službu z backend API nebo environment variables jako fallback.
    
    Args:
        service: Název služby (např. "openai")
        
    Returns:
        API klíč
        
    Raises:
        Exception: Pokud API klíč není nalezen
    """
    try:
        # Pokus o načtení z backend API
        backend_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        response = requests.get(f"{backend_url}/api-keys/{service}", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            api_key = data.get("api_key")
            if api_key and api_key != "Not found":
                logger.info(f"✅ API klíč pro {service} načten z backend API")
                return api_key
        
        logger.warning(f"⚠️ Backend API nevrátilo platný klíč pro {service}, zkouším environment variables")
    except Exception as e:
        logger.warning(f"⚠️ Chyba při načítání API klíče z backend: {e}, zkouším environment variables")
    
    # Fallback na environment variables
    env_key_map = {
        "openai": "OPENAI_API_KEY"
    }
    
    env_var = env_key_map.get(service)
    if env_var:
        api_key = os.getenv(env_var)
        if api_key and api_key != "your-openai-api-key-here":
            logger.info(f"✅ API klíč pro {service} načten z environment variables")
            return api_key
    
    # Žádný platný klíč nenalezen
    raise Exception(f"API klíč pro službu {service} nebyl nalezen ani v backend API ani v environment variables")

@activity.defn
async def load_assistants_from_database(project_id: str) -> list:
    """
    Načte seznam asistentů pro daný projekt z databáze
    POUZE finální 9 asistentů v přesném pořadí - žádné testovací nebo legacy varianty!
    """
    try:
        logger.info(f"🔄 Načítám FINÁLNÍ asistenty pro projekt: {project_id}")
        
        # ✅ FINÁLNÍ SEO Pipeline - přesně 9 asistentů v daném pořadí
        final_assistants = [
            {
                "id": "brief_assistant",
                "name": "BriefAssistant", 
                "function_key": "brief_assistant",
                "slug": "brief_assistant",
                "system_prompt": "Jsi expert na vytváření briefů pro SEO obsah. Tvým úkolem je vytvořit strukturovaný brief na základě zadaného tématu. Zaměř se na cílovou skupinu, klíčové body, které má obsah pokrýt, hlavní cíle textu a očekávaný rozsah obsahu.",
                "model": "gpt-4",
                "max_tokens": 2000,
                "order": 1,
                "input_keys": ["topic"],
                "output_keys": ["brief", "target_audience", "content_goals"]
            },
            {
                "id": "research_assistant",
                "name": "ResearchAssistant",
                "function_key": "research_assistant",
                "slug": "research_assistant", 
                "system_prompt": "Jsi research specialista. Analyzuješ zadané téma podle briefu a vytváříš detailní výzkumné podklady. Hledáš relevantní informace, aktuální trendy, statistiky, expert názory a konkurenční analýzu k danému tématu.",
                "model": "gpt-4",
                "max_tokens": 3000,
                "order": 2,
                "input_keys": ["brief", "topic"],
                "output_keys": ["research_data", "statistics", "trends", "expert_opinions"]
            },
            {
                "id": "fact_validator_assistant",
                "name": "FactValidatorAssistant",
                "function_key": "fact_validator_assistant",
                "slug": "fact_validator_assistant",
                "system_prompt": "Jsi fact-checking specialista. Kontroluješ a ověřuješ faktickou správnost informací z research dat. Identifikuješ potenciálně nepřesné nebo zastaralé informace a navrhneš jejich opravu nebo odstranění.",
                "model": "gpt-4",
                "max_tokens": 2500,
                "order": 3,
                "input_keys": ["research_data", "brief"],
                "output_keys": ["validated_facts", "fact_corrections", "reliability_score"]
            },
            {
                "id": "draft_assistant",
                "name": "DraftAssistant",
                "function_key": "draft_assistant",
                "slug": "draft_assistant",
                "system_prompt": "Jsi copywriter specialista na tvorbu prvního návrhu obsahu. Na základě briefu a ověřených faktů vytváříš strukturovaný draft článku s logickým průtokem informací a základní SEO optimalizací.",
                "model": "gpt-4",
                "max_tokens": 4000,
                "order": 4,
                "input_keys": ["brief", "validated_facts", "research_data"],
                "output_keys": ["content_draft", "article_structure", "key_points"]
            },
            {
                "id": "humanizer_assistant",
                "name": "HumanizerAssistant",
                "function_key": "humanizer_assistant",
                "slug": "humanizer_assistant",
                "system_prompt": "Jsi specialista na humanizaci obsahu. Bereš technický nebo suchý draft a přepisuješ ho do přirozené, čtivé formy. Dbáš na osobní tón, storytelling prvky, engagement a čitelnost pro cílovou skupinu.",
                "model": "gpt-4",
                "max_tokens": 4000,
                "order": 5,
                "input_keys": ["content_draft", "target_audience", "brief"],
                "output_keys": ["humanized_content", "engagement_elements", "readability_score"]
            },
            {
                "id": "seo_assistant",
                "name": "SEOAssistant",
                "function_key": "seo_assistant",
                "slug": "seo_assistant",
                "system_prompt": "Jsi SEO optimalizační expert. Berší humanizovaný obsah a optimalizuješ ho pro vyhledávače - keyword density, internal linking, meta tagy, heading struktura, schema markup a technical SEO best practices.",
                "model": "gpt-4",
                "max_tokens": 3000,
                "order": 6,
                "input_keys": ["humanized_content", "brief", "target_audience"],
                "output_keys": ["seo_optimized_content", "keywords", "meta_tags", "internal_links"]
            },
            {
                "id": "multimedia_assistant",
                "name": "MultimediaAssistant", 
                "function_key": "multimedia_assistant",
                "slug": "multimedia_assistant",
                "system_prompt": "Jsi multimedia content specialist. Analyzuješ SEO optimalizovaný obsah a navrhneš multimedia prvky - obrázky, videa, infografiky, interaktivní prvky. Vytváříš detailní popisy a alt texty pro lepší SEO a user experience.",
                "model": "gpt-4",
                "max_tokens": 2500,
                "order": 7,
                "input_keys": ["seo_optimized_content", "brief"],
                "output_keys": ["multimedia_suggestions", "image_descriptions", "alt_texts", "video_concepts"]
            },
            {
                "id": "qa_assistant",
                "name": "QAAssistant",
                "function_key": "qa_assistant",
                "slug": "qa_assistant",
                "system_prompt": "Jsi quality assurance specialista. Provádíš finální kontrolu kvality - gramatiku, stylistiku, faktickou správnost, SEO compliance, multimedia integrace a celkovou konzistenci obsahu před publikováním.",
                "model": "gpt-4",
                "max_tokens": 2500,
                "order": 8,
                "input_keys": ["seo_optimized_content", "multimedia_suggestions", "brief"],
                "output_keys": ["qa_report", "final_corrections", "quality_score", "publication_ready"]
            },
            {
                "id": "publish_assistant",
                "name": "PublishAssistant",
                "function_key": "publish_assistant",
                "slug": "publish_assistant", 
                "system_prompt": "Jsi publishing specialist. Připravuješ finální obsah pro publikování - CMS formátování, HTML markup, optimalizace pro rychlost načítání, finální SEO kontrola a technické aspekty publikace.",
                "model": "gpt-4",
                "max_tokens": 2000,
                "order": 9,
                "input_keys": ["publication_ready", "multimedia_suggestions", "qa_report"],
                "output_keys": ["published_content", "cms_ready_html", "publication_metadata", "performance_optimized"]
            }
        ]
        
        # 🔍 STRIKTNÍ VALIDACE - kontrola pouze finálních asistentů
        expected_count = 9
        actual_count = len(final_assistants)
        
        # Kontrola počtu asistentů
        if actual_count != expected_count:
            error_msg = f"❌ KRITICKÁ CHYBA: Očekáváno {expected_count} finálních asistentů, ale definováno {actual_count}!"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Kontrola správného pořadí (1-9)
        orders = [assistant["order"] for assistant in final_assistants]
        expected_orders = list(range(1, 10))  # [1, 2, 3, 4, 5, 6, 7, 8, 9]
        
        if orders != expected_orders:
            error_msg = f"❌ CHYBNÉ POŘADÍ: Očekáváno {expected_orders}, ale máme {orders}!"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 🚫 VALIDACE PROTI LEGACY/TESTOVACÍM ASISTENTŮM
        forbidden_slugs = [
            "keyword_assistant", "structure_assistant", "content_assistant", 
            "review_assistant", "meta_assistant",  # Legacy/testovací názvy
            "test_assistant", "demo_assistant", "sample_assistant"  # Testovací varianty
        ]
        
        detected_forbidden = []
        for assistant in final_assistants:
            slug = assistant.get("slug", assistant.get("function_key", ""))
            if slug in forbidden_slugs:
                detected_forbidden.append(slug)
                logger.warning(f"⚠️ Detected invalid assistant in config: {slug}")
        
        if detected_forbidden:
            error_msg = f"❌ NEPLATNÍ ASISTENTI DETECTOVÁNI: {detected_forbidden}. Použijte pouze finální asistenty!"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Kontrola unikátních slugů
        slugs = [assistant["slug"] for assistant in final_assistants]
        if len(slugs) != len(set(slugs)):
            error_msg = f"❌ DUPLICITNÍ SLUGS DETECTED: {slugs}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Seřazení podle order ASC (pro jistotu)
        final_assistants.sort(key=lambda x: x["order"])
        
        # ✅ ÚSPĚŠNÁ VALIDACE - detailní logy
        logger.info(f"✅ NAČTENO {actual_count}/{expected_count} FINÁLNÍCH ASISTENTŮ PRO PROJEKT {project_id}")
        logger.info("📋 FINÁLNÍ ASISTENTI V POŘADÍ:")
        for assistant in final_assistants:
            logger.info(f"  {assistant['order']}. {assistant['name']} ({assistant['slug']})")
        
        logger.info(f"🎯 FINÁLNÍ PIPELINE PŘIPRAVENA: {final_assistants[0]['name']} → ... → {final_assistants[-1]['name']}")
        logger.info("🚫 ŽÁDNÍ legacy/testovací asistenti NEBYLI DETECTOVÁNI ✅")
        
        return final_assistants
        
    except Exception as e:
        logger.error(f"❌ Chyba při načítání finálních asistentů: {str(e)}")
        raise

@activity.defn
async def execute_assistant(args: dict) -> dict:
    """
    Spustí konkrétního asistenta s danou konfigurací
    
    Args:
        args: Dict obsahující:
            - assistant_config: dict - konfigurace asistenta
            - topic: str - téma pro zpracování
            - previous_outputs: dict - předchozí výstupy (optional)
    """
    assistant_config = args.get("assistant_config", {})
    topic = args.get("topic", "")
    previous_outputs = args.get("previous_outputs", {})
    
    assistant_name = assistant_config.get("name", "Unknown")
    function_key = assistant_config.get("function_key", "unknown")
    
    try:
        logger.info(f"🤖 Spouštím asistenta: {assistant_name}")
        logger.info(f"📝 Function Key: {function_key}")
        logger.info(f"📋 Input Length: {len(topic)} chars")
        
        # Získání API klíče z backend
        api_key = get_api_key("openai")
        
        # 🔍 DEBUG LOGY PRO API KLÍČ AUDIT
        logger.info(f"🔑 DEBUG: API key načten: {'✅ Ano' if api_key else '❌ Ne'}")
        logger.info(f"🔑 DEBUG: API key prefix: {api_key[:10] if api_key else 'None'}...")
        logger.info(f"🔑 DEBUG: API key délka: {len(api_key) if api_key else 0} znaků")
        
        if not api_key:
            error_msg = "❌ CRITICAL: OpenAI API klíč není dostupný!"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Inicializace OpenAI klienta
        client = OpenAI(api_key=api_key)
        
        # Získání konfigurace asistenta
        system_prompt = assistant_config.get("system_prompt", "Jsi pomocný AI asistent.")
        model = assistant_config.get("model", "gpt-4")
        max_tokens = assistant_config.get("max_tokens", 1000)
        
        # 🔍 DEBUG LOGY PRO OPENAI REQUEST
        logger.info(f"🤖 DEBUG: Model: {model}")
        logger.info(f"🤖 DEBUG: Max tokens: {max_tokens}")
        logger.info(f"🤖 DEBUG: Prompt délka: {len(system_prompt)} znaků")
        logger.info(f"🤖 DEBUG: Topic délka: {len(topic)} znaků")
        
        try:
            # Volání OpenAI API
            logger.info(f"🔄 Začínám OpenAI API volání...")
            logger.info(f"🌐 API endpoint: https://api.openai.com/v1/chat/completions")
            logger.info(f"🔑 API key prefix: {api_key[:15]}...")
            
            # Heartbeat před dlouhým OpenAI voláním
            activity.heartbeat()
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": topic}
                ],
                max_tokens=max_tokens
            )
            
            # Heartbeat po OpenAI volání
            activity.heartbeat()
            
            logger.info(f"✅ OpenAI API response úspěšný!")
            
            # 🔍 DEBUG LOGY PRO OPENAI RESPONSE
            logger.info(f"✅ DEBUG: OpenAI response received")
            logger.info(f"✅ DEBUG: Response model: {response.model}")
            logger.info(f"✅ DEBUG: Usage tokens: {response.usage.total_tokens if response.usage else 'N/A'}")
            
            output = response.choices[0].message.content
            logger.info(f"✅ DEBUG: Output délka: {len(output)} znaků")
        
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
            "tokens_used": response.usage.total_tokens if response.usage else 0,
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
        logger.error(f"❌ {assistant_name} selhal: {str(e)}")
        error_result = {
            "assistant_name": assistant_name,
            "function_key": function_key,
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        raise Exception(f"Asistent {assistant_name} selhal: {str(e)}")

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