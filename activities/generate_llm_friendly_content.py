import os
import json
import time
from temporalio import activity
from openai import OpenAI
from dotenv import load_dotenv

# Načtení environment variables
load_dotenv()

@activity.defn
async def generate_llm_friendly_content(topic: str) -> str:
    """
    Vygeneruje LLM-friendly SEO obsah pomocí OpenAI Assistant API.
    """
    activity.logger.info(f"Starting OpenAI Assistant for topic: {topic}")
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
    
    activity.logger.info(f"Assistant ID: {assistant_id}")
    
    if not assistant_id:
        activity.logger.error("OPENAI_ASSISTANT_ID není nastaveno v .env souboru")
        raise ValueError("OPENAI_ASSISTANT_ID není nastaveno v .env souboru")
    
    try:
        # Vytvoření threadu a spuštění asistenta
        activity.logger.info("Creating OpenAI thread and run...")
        run = client.beta.threads.create_and_run(
            assistant_id=assistant_id,
            thread={
                "messages": [{
                    "role": "user",
                    "content": f"Vygeneruj kompletní SEO obsah pro téma: {topic}"
                }]
            }
        )
        
        activity.logger.info(f"Run created: {run.id}, status: {run.status}")
        
        # Čekání na dokončení s timeout a heartbeat
        max_wait = 60  # 60 sekund timeout
        waited = 0
        while run.status in ['queued', 'in_progress'] and waited < max_wait:
            time.sleep(2)
            waited += 2
            
            # Heartbeat pro Temporal
            activity.heartbeat(f"Waiting for OpenAI Assistant: {waited}s elapsed, status: {run.status}")
            
            run = client.beta.threads.runs.retrieve(
                thread_id=run.thread_id,
                run_id=run.id
            )
            activity.logger.info(f"Run status: {run.status}, waited: {waited}s")
        
        if run.status != 'completed':
            activity.logger.error(f"OpenAI Assistant run failed with status: {run.status}")
            raise Exception(f"OpenAI Assistant run failed with status: {run.status}")
        
        # Získání odpovědi
        activity.logger.info("Retrieving assistant response...")
        messages = client.beta.threads.messages.list(
            thread_id=run.thread_id
        )
        
        assistant_response = messages.data[0].content[0].text.value
        activity.logger.info(f"Assistant response length: {len(assistant_response)} chars")
        
        # Pokus o parsování JSON odpovědi
        try:
            response_json = json.loads(assistant_response)
            # Vrátíme jen "generated" část pro konzistenci s původním workflow
            result = response_json.get("generated", assistant_response)
            activity.logger.info("Successfully parsed JSON response")
            return result
        except json.JSONDecodeError:
            # Pokud odpověď není JSON, použij plain text
            activity.logger.warning("Response is not JSON, returning as plain text")
            return assistant_response
            
    except Exception as e:
        activity.logger.error(f"OpenAI Assistant API error: {str(e)}")
        raise Exception(f"❌ generate_llm_friendly_content selhal: {str(e)} - workflow nemůže pokračovat") 