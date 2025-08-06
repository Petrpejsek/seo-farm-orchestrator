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
    logger.info(f"🔍 DEBUG: function_key='{function_key}', type={type(function_key)}, len={len(str(function_key))}")
    logger.info(f"🔍 ASSISTANT_CONFIG KEYS: {list(assistant_config.keys())}")
    if "Publish" in assistant_name:
        logger.info(f"🔍 PUBLISH_ASSISTANT_CONFIG_FULL: {assistant_config}")
    
    # Validace konfigurace
    required_fields = ["name", "function_key", "model_provider", "model"]
    missing_fields = [field for field in required_fields if not assistant_config.get(field)]
    if missing_fields:
        raise ValueError(f"Chybí povinná pole v assistant_config: {missing_fields}")
    
    # Příprava vstupních dat
    if topic is None:
        raise ValueError("Topic nesmí být None")
    
    # 🔧 OPRAVA: PublishScript deterministický - bez AI!
    logger.info(f"🔍 KONTROLA: function_key == 'publish_script' ? {function_key == 'publish_script'}")
    if function_key == "publish_script":
        # 🔧 DETERMINISTICKÝ PUBLISH SCRIPT - žádné LLM!
        logger.info(f"🔧 SPOUŠTÍM DETERMINISTICKÝ PUBLISH SCRIPT")
        
        # Zajistit dictionary format pro publish_activity
        if not isinstance(topic, dict):
            logger.warning(f"⚠️ PublishScript očekává dict, dostal {type(topic).__name__}")
            topic = {"content": str(topic)}
        
        logger.info(f"🎯 PublishScript dostává dictionary s {len(topic)} klíči")
        
        # PŘÍMÉ VOLÁNÍ publish_activity místo LLM
        from activities.publish_activity import publish_activity
        import asyncio
        
        try:
            # Sestavení dat pro publish_activity
            # PublishScript potřebuje všechna pipeline data, ne jen výstup ImageRenderer
            final_outputs = previous_outputs.copy() if previous_outputs else {}
            if topic and isinstance(topic, dict):
                # Přidat ImageRenderer výstup do pipeline dat
                final_outputs["image_renderer_assistant_output"] = topic
            
            publish_data = {
                "assistant_config": assistant_config,
                "topic": final_outputs,  # Všechna pipeline data místo jen ImageRenderer výstupu
                "current_date": current_date or datetime.now().isoformat(),
                "previous_outputs": final_outputs
            }
            
            logger.info(f"🔧 Volám publish_activity s {len(final_outputs)} komponenty")
            
            # Přímé async volání publish_activity (již jsme v async kontextu)
            result = await publish_activity(publish_data)
            
            logger.info(f"✅ PublishScript dokončen: {len(str(result))} znaků")
            return result
            
        except Exception as e:
            logger.error(f"❌ PublishScript selhal: {e}")
            raise Exception(f"Deterministický PublishScript selhal: {e}")
        
        # Tohle se už nikdy nespustí, ale ponechám pro jistotu
        user_message = "DETERMINISTICKY_SCRIPT - tento text se nepoužívá"
        
    else:
        # Ostatní asistenti potřebují string
        if isinstance(topic, dict):
            # Pokud je dict, vezmi "output" klíč nebo celý JSON
            import json
            topic = topic.get("output", json.dumps(topic, ensure_ascii=False))
            logger.info(f"🔄 Topic je dict - převádím na string ({len(str(topic))} chars)")
        elif not isinstance(topic, str):
            topic = str(topic)
            logger.info(f"🔄 Topic není string - převádím ({type(topic).__name__} -> str)")
        
        # Kontrola prázdnosti pouze pro string topics
        if isinstance(topic, str) and not topic.strip():
            logger.warning(f"⚠️ Prázdný topic pro {assistant_name} - pokračuji")
            topic = ""
        
        # Příprava user message s datem
        user_message = topic
        if current_date:
            user_message = f"📅 Aktuální datum: {current_date}\n\n{topic}"
    
    # Speciální handling pro QAAssistant - analyzuj obsah ze VŠECH předchozích asistentů
    if function_key == "qa_assistant" and previous_outputs:
        # 🔍 DETAILNÍ DEBUGGING - co QA asistent skutečně dostává
        logger.info(f"🔍 QA ASISTENT DEBUGGING:")
        logger.info(f"   📦 Dostává {len(previous_outputs)} klíčů v previous_outputs:")
        for key, value in previous_outputs.items():
            value_length = len(str(value)) if value else 0
            logger.info(f"      🗝️ {key}: {value_length} znaků")
        
        # Shromaždi obsah k analýze ze VŠECH klíčových asistentů
        content_to_analyze = []
        
        # Definice VŠECH asistentů co QA potřebuje analyzovat (order 1-7, před QA v DB pořadí)
        assistant_priorities = [
            # V pořadí podle database order:
            ("brief_assistant_output", "Brief Assistant", 2000),           # order 1
            ("research_assistant_output", "Research Assistant", 3000),      # order 2  
            ("fact_validator_assistant_output", "Fact Validator Assistant", 2000), # order 3
            ("draft_assistant_output", "Draft Assistant", 5000),            # order 4
            ("humanizer_assistant_output", "Humanizer Assistant", 5000),    # order 5
            ("seo_assistant_output", "SEO Assistant", 2000),                # order 6
            ("multimedia_assistant_output", "Multimedia Assistant", 1500),  # order 7
            # QA asistent má order 8 (TENTO asistent)
            # ImageRenderer má order 9 (po QA)
        ]
        
        # Zpracuj všechny dostupné asistenty
        missing_assistants = []
        empty_assistants = []
        
        for output_key, assistant_name, max_chars in assistant_priorities:
            if output_key in previous_outputs:
                output = previous_outputs[output_key]
                if output and str(output).strip():
                    output_str = str(output)
                    if len(output_str) > max_chars:
                        output_preview = output_str[:max_chars] + f"...\n[ZKRÁCENO z {len(output_str)} znaků]"
                    else:
                        output_preview = output_str
                    content_to_analyze.append(f"=== OBSAH K ANALÝZE Z {assistant_name.upper()} ===\n{output_preview}")
                    logger.info(f"✅ QA přidal {assistant_name}: {len(output_str)} znaků (zkráceno na {min(len(output_str), max_chars)})")
                else:
                    empty_assistants.append(f"{assistant_name} ({output_key})")
                    logger.warning(f"⚠️ QA asistent má prázdný výstup z {assistant_name} ({output_key})")
            else:
                missing_assistants.append(f"{assistant_name} ({output_key})")
                logger.warning(f"❌ QA asistent nemá klíč {output_key} v previous_outputs")
        
        # 🔍 DETAILNÍ ANALÝZA CHYBĚJÍCÍCH DAT
        if missing_assistants:
            logger.error(f"❌ QA asistent: CHYBĚJÍCÍ KLÍČE v previous_outputs: {', '.join(missing_assistants)}")
        if empty_assistants:
            logger.warning(f"⚠️ QA asistent: PRÁZDNÉ VÝSTUPY z asistentů: {', '.join(empty_assistants)}")
        
        if content_to_analyze:
            # Vytvoř message pro QA analýzu se VŠEMI daty
            analysis_content = "\n\n".join(content_to_analyze)
            user_message = f"📅 Aktuální datum: {current_date}\n\nPROVEĎ KOMPLEXNÍ QA KONTROLU tohoto obsahu ze všech asistentů a vrať strukturovanou analýzu ve formátu JSON:\n\n{analysis_content}"
            logger.info(f"🔍 QA asistent dostává kompletní obsah k analýze: {len(analysis_content)} znaků z {len(content_to_analyze)} asistentů")
            logger.info(f"📊 QA STATISTIKY: Úspěšných {len(content_to_analyze)}, Prázdných {len(empty_assistants)}, Chybějících {len(missing_assistants)}")
        else:
            error_msg = f"QA asistent nenašel obsah k analýze z žádného předchozího asistenta! Chybějící: {missing_assistants}, Prázdné: {empty_assistants}"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
    
    # Speciální handling pro ImageRendererAssistant - použij data od MultimediaAssistant
    elif function_key == "image_renderer_assistant" and previous_outputs:
        multimedia_output = previous_outputs.get("multimedia_assistant_output")
        if multimedia_output:
            try:
                # MultimediaAssistant vrací markdown JSON blok
                if isinstance(multimedia_output, str):
                    import json
                    # Extrakce JSON z markdown bloku (```json\n...\n```)
                    if "```json" in multimedia_output:
                        json_start = multimedia_output.find("```json") + 7
                        json_end = multimedia_output.find("```", json_start)
                        if json_end != -1:
                            json_str = multimedia_output[json_start:json_end].strip()
                            image_prompts = json.loads(json_str)
                        else:
                            raise ValueError("Nepoařilo se najít ukončení JSON bloku v MultimediaAssistant výstupu")
                    else:
                        raise ValueError("❌ MultimediaAssistant výstup není validní JSON struktura - publish nemůže pokračovat")
                else:
                    # Nativní objekt
                    image_prompts = multimedia_output
                
                # 🔧 OPRAVA: MultimediaAssistant vrací {primary_visuals: [...], optional_visuals: [...]}
                # Převod na formát pro ImageRenderer: pole s image_prompt položkami
                visuals_data = []
                if "primary_visuals" in image_prompts:
                    visuals_data.extend(image_prompts["primary_visuals"])
                if "optional_visuals" in image_prompts:
                    visuals_data.extend(image_prompts["optional_visuals"])
                
                # 🎯 PŘEVOD NA FORMAT PRO IMAGERENDERER
                formatted_prompts = []
                for visual in visuals_data:
                    if "image_prompt" in visual:
                        formatted_prompts.append(visual["image_prompt"])
                
                logger.info(f"🎨 ImageRenderer input: {len(formatted_prompts)} image prompts z MultimediaAssistant")
                
                # Předej jako JSON string pro ImageRenderer
                if formatted_prompts:
                    # Vytvoř JSON se seznamem promptů
                    user_message = json.dumps(formatted_prompts, ensure_ascii=False)
                else:
                    raise ValueError("❌ MultimediaAssistant neposkytl požadovaná data pro ImageRenderer - publish nemůže pokračovat")
                
            except Exception as e:
                logger.error(f"❌ Chyba při parsování MultimediaAssistant output: {e}")
                raise ValueError(f"❌ MultimediaAssistant parsování selhalo: {str(e)} - publish nemůže pokračovat")
        else:
            raise ValueError("ImageRenderer neobdržel data od MultimediaAssistant")
    
    # 🔧 PŘIDÁNO: Speciální handling pro PublishAssistant - očekává dictionary input
    elif function_key == "publish_script":
        if isinstance(topic, dict):
            # PublishAssistant dostává všechny komponenty jako dictionary
            user_message = topic  # Předej celý dictionary
            logger.info(f"🎯 PublishAssistant input: dictionary s {len(topic)} komponentami")
        else:
            raise ValueError(f"❌ PublishScript očekává dictionary input, ale dostal {type(topic)} - publish nemůže pokračovat")
    
    else:
        # 🔧 OSTATNÍ ASISTENTI: standardní text input s datem  
        if current_date:
            user_message = f"📅 Aktuální datum: {current_date}\n\n{topic}"
        else:
            user_message = str(topic)
        
        if len(str(topic)) > 100:
            logger.info(f"📝 {assistant_name} input: {len(str(topic))} chars")
    
    # Získání LLM konfigurace
    llm_config = get_llm_config()
    model_provider = assistant_config.get("model_provider")
    model = assistant_config.get("model")
    temperature = assistant_config.get("temperature")
    max_tokens = assistant_config.get("max_tokens")
    
    # 🚫 ŽÁDNÉ DEFAULTY! Všechny hodnoty musí být explicitně nastavené v databázi!
    if not model_provider:
        raise Exception(f"❌ CHYBÍ model_provider pro asistenta {assistant_config.get('name', 'unknown')}!")
    if not model:
        raise Exception(f"❌ CHYBÍ model pro asistenta {assistant_config.get('name', 'unknown')}!")
    if temperature is None:
        raise Exception(f"❌ CHYBÍ temperature pro asistenta {assistant_config.get('name', 'unknown')}!")
    if max_tokens is None:
        raise Exception(f"❌ CHYBÍ max_tokens pro asistenta {assistant_config.get('name', 'unknown')}!")
    system_prompt = assistant_config.get("system_prompt")
    
    # 🚫 ŽÁDNÉ FALLBACKY! Pokud system_prompt není v databázi, SELHAT!
    if not system_prompt or not system_prompt.strip():
        raise Exception(f"❌ ŽÁDNÝ SYSTEM PROMPT pro asistenta {assistant_config.get('name', 'unknown')}! Musí být v databázi!")
    
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
        
        # Detekce image modelů (DALL-E + Google Imagen) - SPECIÁLNÍ HANDLING PRO IMAGERENDERER
        image_models = ["dall-e-3", "dall-e-2", "dall-e", "imagen-4", "imagen-3", "imagen"]
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
                    
                    # Použij safe_llm_call pro image generation
                    try:
                        logger.info(f"🤖 IMAGE generace pro prompt {i+1}: {model_provider}/{model}")
                        
                        llm_result = await safe_llm_call(
                            llm_func=llm_client.image_generation,
                            provider=model_provider,
                            model=model,
                            prompt=prompt,
                            size="1024x1024",
                            quality="standard",
                            style="vivid",
                            max_retries=3
                        )
                        
                        if not llm_result or "content" not in llm_result:
                            raise Exception(f"Image generation vrátil nevalidní response: {llm_result}")
                            
                        logger.info(f"✅ IMAGE úspěch pro prompt {i+1}: {model_provider}/{model}")
                        
                    except Exception as e:
                        logger.error(f"❌ Image generation selhal pro prompt {i+1}: {str(e)}")
                        # Přidej chybný obrázek místo exception
                        generated_images.append({
                            "url": "",
                            "prompt": prompt,
                            "status": "failed",
                            "error": f"Image generation failed: {str(e)}"
                        })
                        continue
                    
                    # Extrahuj URL z response
                    image_url = await _extract_url_from_image_response(llm_result)
                    if not image_url:
                        logger.warning(f"⚠️ Žádná URL nalezena v image response pro prompt {i+1}")
                        generated_images.append({
                            "url": "",
                            "prompt": prompt,
                            "status": "failed",
                            "error": "No URL found in image response"
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
            
            # Použij safe_llm_call pro image generation
            llm_result = await safe_llm_call(
                llm_func=llm_client.image_generation,
                provider=model_provider,
                model=model,
                prompt=user_message,
                size="1024x1024",
                quality="standard",
                style="vivid",
                max_retries=3
            )
            
            if not llm_result or "content" not in llm_result:
                raise Exception(f"Image generation selhalo - nevalidní response: {llm_result}")
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

async def _extract_url_from_image_response(image_response: dict) -> str:
    """
    Extrahuje URL z image API response.
    
    Args:
        image_response: Response z image API
        
    Returns:
        URL obrázku nebo None
    """
    try:
        logger.info(f"🔍 Extrakce URL z image response: {type(image_response)}")
        
        if isinstance(image_response, dict):
            # Zkus content.url structure
            if "content" in image_response:
                content = image_response["content"]
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
            if "url" in image_response:
                logger.info(f"✅ URL nalezena přímo: {image_response['url'][:100]}...")
                return image_response["url"]
        
        logger.warning(f"⚠️ Žádná URL nenalezena v image response")
        logger.warning(f"⚠️ Response structure: {image_response}")
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