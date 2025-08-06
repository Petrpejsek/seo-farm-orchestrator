"""
🛡️ BEZPEČNÉ WRAPPERY PRO TEMPORAL AKTIVITY
Zabezpečuje všechny aktivity proti neočekávaným pádom.
"""

import functools
import time
from typing import Any, Dict, Callable, Optional
from temporalio import activity
from logger import get_logger, log_activity_start, log_activity_success, log_activity_error

logger = get_logger(__name__)

def safe_activity(
    name: Optional[str] = None,
    timeout_seconds: int = 600,
    heartbeat_interval: int = 60
):
    """
    Decorator pro bezpečné Temporal aktivity.
    
    Args:
        name: Název aktivity (pokud není poskytnut, použije se název funkce)
        timeout_seconds: Timeout v sekundách
        heartbeat_interval: Interval heartbeat v sekundách
    """
    def decorator(func: Callable) -> Callable:
        activity_name = name or func.__name__
        
        @activity.defn(name=activity_name)
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Dict[str, Any]:
            """Bezpečný wrapper pro aktivitu."""
            start_time = time.time()
            
            # Příprava vstupních dat pro logování
            inputs = {
                "args": args,
                "kwargs": kwargs
            }
            
            try:
                # Logování začátku
                log_activity_start(logger, activity_name, inputs)
                
                # Heartbeat před spuštěním
                activity.heartbeat()
                
                # Spuštění aktivity (odstranil jsem problematickou kontrolu cancel stavu)
                result = await func(*args, **kwargs)
                
                # Kontrola výsledku
                if result is None:
                    logger.warning(f"⚠️ Activity {activity_name} vrátila None")
                    result = {"status": "completed", "output": "", "warning": "Empty result"}
                elif isinstance(result, str):
                    # Převod stringu na standardní formát
                    result = {"status": "completed", "output": result}
                elif not isinstance(result, dict):
                    # Převod ostatních typů na standardní formát
                    result = {"status": "completed", "output": str(result)}
                
                # Zajištění status pole
                if "status" not in result:
                    result["status"] = "completed"
                
                # Logování úspěchu
                duration = time.time() - start_time
                output_preview = str(result.get("output", ""))[:200]
                log_activity_success(logger, activity_name, output_preview)
                logger.info(f"   ⏱️ Duration: {duration:.2f}s")
                
                return result
                
            except Exception as e:
                # Logování chyby
                duration = time.time() - start_time
                log_activity_error(logger, activity_name, e, inputs)
                logger.error(f"   ⏱️ Failed after: {duration:.2f}s")
                
                # Standardizovaný error response
                error_result = {
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration": duration,
                    "activity": activity_name
                }
                
                # Pro kritické chyby propagujeme výjimku
                if isinstance(e, (KeyboardInterrupt, SystemExit)):
                    raise
                
                # Pro ostatní chyby vracíme error response
                return error_result
        
        return wrapper
    return decorator

def validate_activity_input(inputs: Dict[str, Any], required_fields: list) -> None:
    """
    Validuje vstupní data aktivity.
    
    Args:
        inputs: Vstupní data
        required_fields: Seznam povinných polí
        
    Raises:
        ValueError: Pokud chybí povinná pole
    """
    missing_fields = [field for field in required_fields if field not in inputs]
    if missing_fields:
        raise ValueError(f"Chybí povinná pole: {missing_fields}")

def standardize_activity_output(output: Any, activity_name: str) -> Dict[str, Any]:
    """
    Standardizuje výstup aktivity do jednotného formátu.
    
    Args:
        output: Surový výstup aktivity
        activity_name: Název aktivity
        
    Returns:
        Standardizovaný výstup
    """
    if isinstance(output, dict) and "status" in output:
        return output
    
    return {
        "status": "completed",
        "output": output,
        "activity": activity_name,
        "timestamp": time.time()
    }

async def safe_llm_call(
    llm_func: Callable,
    provider: str,
    model: str,
    max_retries: int = 3,
    **kwargs
) -> Dict[str, Any]:
    """
    Bezpečné volání LLM s retry logikou.
    
    Args:
        llm_func: LLM funkce k volání
        provider: LLM provider (openai, claude, gemini)
        model: Model name
        max_retries: Maximální počet pokusů
        **kwargs: Argumenty pro LLM funkci
        
    Returns:
        Standardizovaný LLM response
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Heartbeat před každým pokusem
            activity.heartbeat()
            
            logger.info(f"🤖 LLM pokus {attempt + 1}/{max_retries}: {provider}/{model}")
            
            # Rozpoznání typu LLM funkce podle názvu
            func_name = getattr(llm_func, '__name__', str(llm_func))
            func_str = str(llm_func)
            logger.info(f"🔍 FUNC DEBUG: func_name='{func_name}', func_str='{func_str}'")
            
            if 'image_generation' in func_name or 'image_generation' in func_str:
                # Pro image generation API - používáme prompt + model parametr
                prompt = kwargs.get('prompt', kwargs.get('user_message', ''))
                size = kwargs.get('size', '1024x1024')
                quality = kwargs.get('quality', 'standard')
                style = kwargs.get('style', 'vivid')
                logger.info(f"🎨 IMAGE GENERATION: provider={provider}, model={model}, prompt={prompt[:100]}...")
                result = await llm_func(prompt=prompt, model=model, size=size, quality=quality, style=style)
            else:
                # Pro chat completion API - KONVERZE NA STRING!!
                system_prompt = kwargs.get('system_prompt', '')
                user_message = kwargs.get('user_message', '')
                
                # 🔧 KRITICKÁ OPRAVA: VŽDY PŘEVÉST user_message NA STRING!
                if not isinstance(user_message, str):
                    logger.warning(f"⚠️ user_message není string: {type(user_message)}, převádím na string")
                    user_message = str(user_message)
                
                temperature = kwargs.get('temperature', 0.7)
                max_tokens = kwargs.get('max_tokens')
                
                logger.info(f"🔍 LLM_CALL DEBUG: user_message type={type(user_message)}, len={len(user_message)}")
                
                result = await llm_func(
                    system_prompt=system_prompt,
                    user_message=user_message, 
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            
            # Kontrola výsledku podle typu API
            if result:
                if 'image_generation' in func_name or 'image_generation' in func_str:
                    # Pro image generation očekáváme "content" klíč
                    if "content" in result:
                        logger.info(f"✅ LLM úspěch: {provider}/{model}")
                        return result
                    else:
                        raise Exception(f"Image generation vrátil nevalidní response (missing 'content'): {result}")
                elif "content" in result:
                    # Pro chat completion očekáváme "content" klíč
                    logger.info(f"✅ LLM úspěch: {provider}/{model}")
                    return result
                else:
                    raise Exception(f"Chat completion vrátil nevalidní response (missing 'content'): {result}")
            else:
                raise Exception(f"LLM vrátil prázdný response: {result}")
                
        except Exception as e:
            last_error = e
            logger.warning(f"⚠️ LLM pokus {attempt + 1} selhal: {str(e)}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    # Všechny pokusy selhaly
    raise Exception(f"LLM selhalo po {max_retries} pokusech. Poslední chyba: {last_error}")

# Import asyncio pro safe_llm_call
import asyncio