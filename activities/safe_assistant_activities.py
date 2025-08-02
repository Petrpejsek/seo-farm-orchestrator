"""
🛡️ BEZPEČNÉ ASSISTANT AKTIVITY PRO PRODUKČNÍ PROSTŘEDÍ
Stabilní verze assistant aktivit s kompletním error handlingem.
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from temporalio import activity

# Naše nové bezpečné moduly
from activity_wrappers import safe_activity, validate_activity_input, safe_llm_call
from logger import get_logger, log_llm_request, log_llm_response
from config import get_llm_config, get_activity_config

# Originální závislosti
from backend.llm_clients.factory import LLMClientFactory
from prisma import Prisma

logger = get_logger(__name__)

@safe_activity(name="load_assistants_from_database", timeout_seconds=60)
async def load_assistants_from_database(project_id: str) -> Dict[str, Any]:
    """
    Bezpečně načte asistenty z databáze pro daný projekt.
    
    Args:
        project_id: ID projektu
        
    Returns:
        Dict s načtenými asistenty
    """
    validate_activity_input({"project_id": project_id}, ["project_id"])
    
    if not project_id or not project_id.strip():
        raise ValueError("Project ID nesmí být prázdné")
    
    db = None
    try:
        db = Prisma()
        await db.connect()
        
        # Načtení pouze aktivních asistentů (bez order_by - seřadíme v Pythonu)
        assistants = await db.assistant.find_many(
            where={"projectId": project_id, "active": True}
        )
        
        logger.info(f"📊 Načteno {len(assistants)} asistentů z databáze pro projekt {project_id}")
        
        # Seřazení podle order pole v Pythonu
        assistants = sorted(assistants, key=lambda x: x.order if x.order is not None else 0)
        
        if not assistants:
            logger.warning(f"⚠️ Žádní asistenti nebyli nalezeni pro projekt {project_id}")
            return {
                "status": "warning",
                "assistants": [],
                "count": 0,
                "message": f"Žádní asistenti pro projekt {project_id}"
            }
        
        # Validace asistentů
        valid_assistants = []
        for assistant in assistants:
            if not assistant.name or not assistant.name.strip():
                logger.error(f"❌ Asistent {assistant.id} má prázdný název - přeskakuji")
                continue
            
            if not assistant.functionKey:
                logger.error(f"❌ Asistent {assistant.name} nemá functionKey - přeskakuji")
                continue
                
            valid_assistants.append({
                "id": assistant.id,
                "name": assistant.name,
                "function_key": assistant.functionKey,
                "system_prompt": assistant.system_prompt or "",
                "model_provider": assistant.model_provider or "openai", 
                "model": assistant.model or "gpt-3.5-turbo",
                "temperature": assistant.temperature or 0.7,
                "max_tokens": assistant.max_tokens,
                "order": assistant.order or 0
            })
        
        logger.info(f"✅ Načteno {len(valid_assistants)} validních asistentů z {len(assistants)} celkem")
        
        return {
            "status": "completed",
            "assistants": valid_assistants,
            "count": len(valid_assistants),
            "project_id": project_id
        }
        
    finally:
        if db:
            await db.disconnect()

@safe_activity(name="execute_assistant", timeout_seconds=600, heartbeat_interval=30)
async def execute_assistant(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bezpečně spustí jednoho asistenta s LLM voláním.
    
    Args:
        args: Dictionary obsahující:
            - assistant_config: Konfigurace asistenta
            - topic: Téma/vstup pro asistenta
            - current_date: Aktuální datum (optional)
            - previous_outputs: Výstupy předchozích asistentů (optional)
        
    Returns:
        Dict s výstupem asistenta
    """
    # Extrakce argumentů z args dictionary
    assistant_config = args.get("assistant_config")
    topic = args.get("topic")
    current_date = args.get("current_date")
    previous_outputs = args.get("previous_outputs", {})
    
    validate_activity_input(
        {"assistant_config": assistant_config, "topic": topic},
        ["assistant_config", "topic"]
    )
    
    assistant_name = assistant_config.get("name", "Unknown")
    function_key = assistant_config.get("function_key", "unknown")
    
    logger.info(f"🚀 Spouštím asistenta: {assistant_name} ({function_key})")
    
    # Validace konfigurace
    required_fields = ["name", "function_key", "model_provider", "model"]
    missing_fields = [field for field in required_fields if not assistant_config.get(field)]
    if missing_fields:
        raise ValueError(f"Chybí povinná pole v assistant_config: {missing_fields}")
    
    # Příprava vstupních dat
    if topic is None:
        raise ValueError("Topic nesmí být None")
    
    # 🔧 OPRAVA: Topic může být dict z předchozího asistenta - převádíme na string
    if isinstance(topic, dict):
        # Pokud je dict, vezmi "output" klíč nebo celý JSON
        import json
        topic = topic.get("output", json.dumps(topic, ensure_ascii=False))
        logger.info(f"🔄 Topic je dict - převádím na string ({len(str(topic))} chars)")
    elif not isinstance(topic, str):
        topic = str(topic)
        logger.info(f"🔄 Topic není string - převádím ({type(topic).__name__} -> str)")
    
    if not topic.strip():
        logger.warning(f"⚠️ Prázdný topic pro {assistant_name} - pokračuji")
        topic = ""
    
    # Příprava user message s datem
    user_message = topic
    if current_date:
        user_message = f"📅 Aktuální datum: {current_date}\n\n{topic}"
    
    # Speciální handling pro ImageRendererAssistant - použij data od MultimediaAssistant
    if function_key == "image_renderer_assistant" and previous_outputs:
        multimedia_output = previous_outputs.get("MultimediaAssistant", {}).get("output")
        if multimedia_output:
            try:
                # MultimediaAssistant nyní vrací nativní objekt, ne string
                if isinstance(multimedia_output, str):
                    # Backward compatibility - starší verze vracely string
                    import json
                    image_prompts = json.loads(multimedia_output)
                else:
                    # Nová verze - nativní objekt
                    image_prompts = multimedia_output
                
                if image_prompts and len(image_prompts) > 0:
                    # Použij první image prompt od MultimediaAssistant
                    first_prompt = image_prompts[0].get("image_prompt", user_message)
                    user_message = first_prompt
                    logger.info(f"🎨 ImageRenderer používá prompt od MultimediaAssistant: {first_prompt[:100]}...")
                else:
                    # ❌ ŽÁDNÉ FALLBACKY - pipeline musí selhat
                    raise ValueError("MultimediaAssistant nevrátil žádné validní image prompty")
            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                # ❌ ŽÁDNÉ FALLBACKY - pipeline musí selhat
                raise ValueError(f"Chyba při parsování MultimediaAssistant output: {e}")
        else:
            # ❌ ŽÁDNÉ FALLBACKY - pipeline musí selhat
            raise ValueError("ImageRenderer nenašel výstup od MultimediaAssistant")
    
    # Získání LLM konfigurace
    llm_config = get_llm_config()
    model_provider = assistant_config.get("model_provider", "openai")
    model = assistant_config.get("model", "gpt-3.5-turbo")
    temperature = assistant_config.get("temperature", llm_config.default_temperature)
    max_tokens = assistant_config.get("max_tokens", llm_config.default_max_tokens)
    system_prompt = assistant_config.get("system_prompt", "")
    
    # Speciální handling pro -1 (unlimited)
    if max_tokens == -1:
        max_tokens = None
    
    logger.info(f"🤖 LLM konfigurace: {model_provider}/{model} (temp: {temperature}, tokens: {max_tokens or 'unlimited'})")
    
    # Vytvoření LLM clienta
    try:
        llm_client = LLMClientFactory.create_client(model_provider)
        log_llm_request(logger, model_provider, model, max_tokens)
        
        # Bezpečné LLM volání - rozpoznání typu modelu
        start_time = datetime.now()
        
        # Detekce image modelů (DALL-E) - SPECIÁLNÍ HANDLING PRO IMAGERENDERER
        image_models = ["dall-e-3", "dall-e-2", "dall-e"]
        is_image_model = any(img_model in model.lower() for img_model in image_models)
        
        if is_image_model and function_key == "image_renderer_assistant":
            # 🎯 SPECIÁLNÍ LOGIKA PRO IMAGERENDERER - VYGENERUJ VŠECHNY OBRÁZKY
            logger.info(f"🎨 IMAGERENDERER SPECIÁLNÍ HANDLING: model={model}")
            
            try:
                # Extrahuj image_prompts z MultimediaAssistant výstupu
                image_prompts = await _extract_image_prompts_from_input(user_message)
                logger.info(f"🔍 Nalezeno {len(image_prompts)} image_prompts")
                
                if not image_prompts:
                    logger.warning("⚠️ ImageRenderer: Žádné image_prompts nalezeny v inputu")
                    # Vrať prázdný ale validní výsledek místo exception
                    final_result = {
                        "images": [],
                        "successful_count": 0,
                        "total_count": 0,
                        "model": model,
                        "config": {"provider": model_provider},
                        "warning": "No image_prompts found in input"
                    }
                    
                    return {
                        "status": "completed", 
                        "output": final_result,  # ← NATIVNÍ OBJEKT, NE STRING!
                        "assistant": assistant_name,
                        "function_key": function_key,
                        "provider": model_provider,
                        "model": model,
                        "duration": (datetime.now() - start_time).total_seconds(),
                        "input_length": len(user_message),
                        "output_length": len(str(final_result))
                    }
                
                logger.info(f"🎨 Nalezeno {len(image_prompts)} image_prompts k vygenerování")
                
                # Vygeneruj obrázek pro každý prompt
                generated_images = []
                
                for i, prompt in enumerate(image_prompts):
                    logger.info(f"🎨 Generuji obrázek {i+1}/{len(image_prompts)}: {prompt[:100]}...")
                    
                    # Tři pokusy pro každý obrázek
                    llm_result = None
                    last_error = None
                    
                    for attempt in range(3):
                        try:
                            activity.heartbeat()
                            logger.info(f"🤖 IMAGE pokus {attempt + 1}/3 pro prompt {i+1}: {model_provider}/{model}")
                            
                            llm_result = await llm_client.image_generation(
                                prompt=prompt,
                                size="1024x1024",
                                quality="standard", 
                                style="vivid"
                            )
                            
                            if llm_result and "content" in llm_result:
                                logger.info(f"✅ IMAGE úspěch pro prompt {i+1}: {model_provider}/{model}")
                                break
                            else:
                                raise Exception(f"Image generation vrátil nevalidní response: {llm_result}")
                                
                        except Exception as e:
                            last_error = e
                            logger.warning(f"⚠️ IMAGE pokus {attempt + 1} pro prompt {i+1} selhal: {str(e)}")
                            if attempt < 2:
                                await asyncio.sleep(2 ** attempt)
                    
                    if not llm_result or "content" not in llm_result:
                        logger.error(f"❌ Image generation selhal pro prompt {i+1}: {last_error}")
                        # Přidej chybný obrázek místo exception
                        generated_images.append({
                            "url": "",
                            "prompt": prompt,
                            "status": "failed",
                            "error": f"DALL-E generation failed: {last_error}"
                        })
                        continue
                    
                    # Extrahuj URL z response
                    image_url = await _extract_url_from_dalle_response(llm_result)
                    if not image_url:
                        logger.warning(f"⚠️ Žádná URL nalezena v DALL-E response pro prompt {i+1}")
                        generated_images.append({
                            "url": "",
                            "prompt": prompt,
                            "status": "failed",
                            "error": "No URL found in DALL-E response"
                        })
                        continue
                    
                    generated_images.append({
                        "url": image_url,
                        "prompt": prompt,
                        "status": "completed"
                    })
                    
                    logger.info(f"✅ Obrázek {i+1} vygenerován: {image_url[:100]}...")
                
                # Vytvoř finální output jako NATIVNÍ OBJEKT (ne string!)
                # I když některé obrázky selhaly, vrať co se podařilo vygenerovat
                successful_images = [img for img in generated_images if img["status"] == "completed"]
                
                final_result = {
                    "images": generated_images,  # Zahrnuj všechny obrázky (i chybné)
                    "successful_count": len(successful_images),
                    "total_count": len(image_prompts),
                    "model": model,
                    "config": {"provider": model_provider}
                }
                
                logger.info(f"🎉 ImageRenderer HOTOVO: {len(generated_images)} obrázků vygenerováno!")
                
                # Vrať jako nativní objekt pro workflow
                return {
                    "status": "completed", 
                    "output": final_result,  # ← NATIVNÍ OBJEKT, NE STRING!
                    "assistant": assistant_name,
                    "function_key": function_key,
                    "provider": model_provider,
                    "model": model,
                    "duration": (datetime.now() - start_time).total_seconds(),
                    "input_length": len(user_message),
                    "output_length": len(str(final_result))
                }
            
            except Exception as e:
                logger.error(f"❌ CHYBA v ImageRenderer speciální logice: {e}")
                # Vrať chybový výsledek jako nativní objekt - NIKDY nepokračuj do elif is_image_model
                error_result = {
                    "images": [],
                    "successful_count": 0,
                    "total_count": 0,
                    "model": model,
                    "config": {"provider": model_provider},
                    "error": f"ImageRenderer logic failed: {str(e)}"
                }
                
                return {
                    "status": "completed", 
                    "output": error_result,  # ← NATIVNÍ OBJEKT i při chybě!
                    "assistant": assistant_name,
                    "function_key": function_key,
                    "provider": model_provider,
                    "model": model,
                    "duration": (datetime.now() - start_time).total_seconds(),
                    "input_length": len(user_message),
                    "output_length": len(str(error_result))
                }
            
        elif is_image_model:
            # Pro ostatní image modely (pokud nějaké jsou)
            logger.info(f"🎨 OBECNÝ IMAGE GENERATION: model={model}")
            
            # Tři pokusy pro image generation
            llm_result = None
            last_error = None
            
            for attempt in range(3):
                try:
                    activity.heartbeat()
                    logger.info(f"🤖 IMAGE pokus {attempt + 1}/3: {model_provider}/{model}")
                    
                    llm_result = await llm_client.image_generation(
                        prompt=user_message,
                        size="1024x1024",
                        quality="standard", 
                        style="vivid"
                    )
                    
                    if llm_result and "content" in llm_result:
                        logger.info(f"✅ IMAGE úspěch: {model_provider}/{model}")
                        break
                    else:
                        raise Exception(f"Image generation vrátil nevalidní response: {llm_result}")
                        
                except Exception as e:
                    last_error = e
                    logger.warning(f"⚠️ IMAGE pokus {attempt + 1} selhal: {str(e)}")
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
            
            if not llm_result or "content" not in llm_result:
                raise Exception(f"Image generation selhalo po 3 pokusech. Poslední chyba: {last_error}")
        else:
            # Pro text modely používáme chat_completion API
            llm_result = await safe_llm_call(
                llm_func=llm_client.chat_completion,
                provider=model_provider,
                model=model,
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=temperature,
                max_tokens=max_tokens,
                max_retries=3
            )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Extraha odpověď
        content = llm_result.get("content", "")
        if not content:
            raise ValueError(f"LLM vrátil prázdný content: {llm_result}")
        
        log_llm_response(logger, model_provider, len(content), duration)
        
        # Speciální handling pro konkrétní asistenty (kromě ImageRenderer který má vlastní handling výše)
        logger.info(f"🔧 PRE-PROCESSING: {function_key} content preview: {content[:100]}...")
        processed_output = await _process_assistant_output(
            function_key, content, assistant_name
        )
        logger.info(f"🔧 POST-PROCESSING: {function_key} output preview: {processed_output[:100]}...")
        
        return {
            "status": "completed",
            "output": processed_output,
            "assistant": assistant_name,
            "function_key": function_key,
            "provider": model_provider,
            "model": model,
            "duration": duration,
            "input_length": len(user_message),
            "output_length": len(processed_output)
        }
        
    except Exception as e:
        logger.error(f"❌ LLM volání selhalo pro {assistant_name}: {str(e)}")
        raise

async def _extract_image_prompts_from_input(user_message: str) -> list:
    """
    Extrahuje image_prompts z výstupu MultimediaAssistant.
    
    Args:
        user_message: Input pro ImageRenderer (obsahuje output od MultimediaAssistant)
        
    Returns:
        Seznam image_prompts jako List[str]
    """
    import json
    import re
    
    try:
        logger.info(f"🔍 Extrakce image_prompts z input: {user_message[:200]}...")
        
        # Zkusíme najít JSON s image_prompts v user_message
        # MultimediaAssistant vrací output jako JSON string s image_prompts
        
        # Metoda 1: Hledáme JSON přímo
        try:
            # Možná je to celé JSON
            data = json.loads(user_message)
            if isinstance(data, list) and len(data) > 0:
                # Je to seznam promptů přímo
                logger.info(f"🎨 Našel jsem seznam promptů přímo: {len(data)} items")
                return [str(item) for item in data if str(item).strip()]
            elif isinstance(data, dict):
                # 🔧 NOVÁ LOGIKA: Podpora primary_visuals + optional_visuals struktury
                all_prompts = []
                
                if "image_prompts" in data:
                    prompts = data["image_prompts"]
                    logger.info(f"🎨 Našel jsem image_prompts v dict: {len(prompts)} items")
                    all_prompts.extend([str(prompt) for prompt in prompts if str(prompt).strip()])
                
                # Podpora nové struktury z MultimediaAssistant
                if "primary_visuals" in data:
                    for visual in data["primary_visuals"]:
                        if "image_prompt" in visual:
                            all_prompts.append(visual["image_prompt"])
                    logger.info(f"🎨 Našel jsem {len(data['primary_visuals'])} primary_visuals promptů")
                
                if "optional_visuals" in data:
                    for visual in data["optional_visuals"]:
                        if "image_prompt" in visual:
                            all_prompts.append(visual["image_prompt"])
                    logger.info(f"🎨 Našel jsem {len(data['optional_visuals'])} optional_visuals promptů")
                
                if all_prompts:
                    logger.info(f"🎨 CELKEM nalezeno {len(all_prompts)} image_prompts")
                    return [prompt.strip() for prompt in all_prompts if prompt.strip()]
        except json.JSONDecodeError:
            pass
        
        # Metoda 2: Hledáme JSON uvnitř textu pomocí regex
        json_pattern = r'\[\s*"[^"]+(?:"\s*,\s*"[^"]+)*"\s*\]'
        json_matches = re.findall(json_pattern, user_message, re.DOTALL)
        
        for match in json_matches:
            try:
                prompts = json.loads(match)
                if isinstance(prompts, list) and len(prompts) > 0:
                    valid_prompts = [str(prompt) for prompt in prompts if str(prompt).strip()]
                    if valid_prompts:
                        logger.info(f"🎨 Našel jsem {len(valid_prompts)} promptů pomocí regex")
                        return valid_prompts
            except:
                continue
        
        # Metoda 3: Hledáme prompty jako citované řetězce
        quote_pattern = r'"([^"]{20,})"'
        quote_matches = re.findall(quote_pattern, user_message)
        
        if quote_matches:
            # Filtruj jen ty co vypadají jako image prompty (aspoň 20 znaků)
            valid_prompts = [match for match in quote_matches if len(match) >= 20]
            if valid_prompts:
                logger.info(f"🎨 Našel jsem {len(valid_prompts)} promptů v uvozovkách")
                return valid_prompts
        
        logger.warning(f"⚠️ Žádné image_prompts nenalezeny v input")
        logger.warning(f"⚠️ Input sample: {user_message[:500]}")
        return []
        
    except Exception as e:
        logger.error(f"❌ Chyba při extrakci image_prompts: {e}")
        return []

async def _extract_url_from_dalle_response(dalle_response: dict) -> str:
    """
    Extrahuje URL z DALL-E API response.
    
    Args:
        dalle_response: Response z DALL-E API
        
    Returns:
        URL obrázku nebo None
    """
    try:
        logger.info(f"🔍 Extrakce URL z DALL-E response: {type(dalle_response)}")
        
        if isinstance(dalle_response, dict):
            # Zkus content.url structure
            if "content" in dalle_response:
                content = dalle_response["content"]
                if isinstance(content, str):
                    # Je to string s URL - extrahni pomocí regex
                    import re
                    urls = re.findall(r'https://[^\s\n\)]+', content)
                    if urls:
                        logger.info(f"✅ URL nalezena v content string: {urls[0][:100]}...")
                        return urls[0]
                elif isinstance(content, list) and len(content) > 0:
                    # Je to seznam s objekty
                    item = content[0]
                    if isinstance(item, dict) and "url" in item:
                        logger.info(f"✅ URL nalezena v content[0].url: {item['url'][:100]}...")
                        return item["url"]
            
            # Zkus přímou URL
            if "url" in dalle_response:
                logger.info(f"✅ URL nalezena přímo: {dalle_response['url'][:100]}...")
                return dalle_response["url"]
        
        logger.warning(f"⚠️ Žádná URL nenalezena v DALL-E response")
        logger.warning(f"⚠️ Response structure: {dalle_response}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Chyba při extrakci URL: {e}")
        return None

async def _process_assistant_output(
    function_key: str, 
    raw_output: str, 
    assistant_name: str
) -> str:
    """
    Zpracuje výstup asistenta podle jeho typu.
    ImageRenderer už má vlastní speciální handling, takže tahle funkce se už nepoužívá.
    """
    # Pro všechny asistenty vrátíme surový výstup
    return raw_output.strip()

# 🗑️ ODSTRANĚNO: _process_image_renderer_output - ImageRenderer má teď vlastní speciální handling