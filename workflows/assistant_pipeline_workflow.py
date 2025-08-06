import json
import os
import logging
from temporalio import workflow, activity
from datetime import timedelta
from typing import Dict, List, Any, Optional
import temporalio.common

# Nastavení loggingu
logger = logging.getLogger(__name__)

@workflow.defn
class AssistantPipelineWorkflow:
    @workflow.run
    async def run(self, topic: str, project_id: Optional[str] = None, csv_base64: Optional[str] = None, current_date: Optional[str] = None) -> dict:
        workflow_id = workflow.info().workflow_id
        run_id = workflow.info().run_id
        
        workflow.logger.info(f"🚀 ASSISTANT_PIPELINE_STARTED: topic='{topic}' project_id={project_id} date='{current_date}' workflow_id={workflow_id} run_id={run_id}")
        
        # Inicializace stage logs pro tracking
        stage_logs = []
        pipeline_data = {
            "topic": topic,
            "project_id": project_id,
            "csv_base64": csv_base64,
            "current_date": current_date,
            "current_output": topic  # Začneme s tématem jako prvním vstupem
        }
        
        try:
            # 1️⃣ Načtení asistentů z databáze podle project_id
            stage_name = "load_assistants_config"
            stage_start = workflow.now().timestamp()
            workflow.logger.info(f"📋 STAGE_STARTED: {stage_name} for project_id={project_id}")
            stage_logs.append({"stage": stage_name, "status": "STARTED", "timestamp": stage_start})
            
            # 🚫 STRICT PROJECT_ID VALIDATION - žádné fallbacky
            if not project_id:
                workflow.logger.error("❌ project_id je povinný pro načtení asistentů - workflow nelze spustit")
                raise Exception("❌ project_id je povinný pro načtení asistentů - workflow nelze spustit")
            
            assistants_config = await workflow.execute_activity(
                "load_assistants_from_database",
                project_id,
                schedule_to_close_timeout=timedelta(seconds=30),
                heartbeat_timeout=timedelta(seconds=10)
            )
            
            stage_duration = workflow.now().timestamp() - stage_start
            assistants_count = len(assistants_config.get("assistants", [])) if isinstance(assistants_config, dict) else len(assistants_config) if assistants_config else 0
            workflow.logger.info(f"✅ STAGE_FINISHED: {stage_name} duration={stage_duration:.2f}s assistants_count={assistants_count}")
            stage_logs.append({"stage": stage_name, "status": "COMPLETED", "timestamp": workflow.now().timestamp(), "duration": stage_duration})

            # Extrakce asistentů z Dict response
            if isinstance(assistants_config, dict):
                assistants = assistants_config.get("assistants", [])
                workflow.logger.info(f"📋 Extrahováno {len(assistants)} asistentů z dict response")
            else:
                assistants = assistants_config if assistants_config else []
                workflow.logger.warning(f"⚠️ Neočekávaný typ response: {type(assistants_config)}")
            
            if not assistants:
                workflow.logger.warning("⚠️ Žádní asistenti nenalezeni - ukončuji workflow")
                raise Exception("Žádní aktivní asistenti nenalezeni pro daný projekt")

            # 2️⃣ Postupné spuštění asistentů podle pořadí
            for i, assistant in enumerate(assistants):
                # 🚫 STRICT ASSISTANT VALIDATION - žádné fallbacky
                assistant_name = assistant.get("name")
                if not assistant_name:
                    workflow.logger.error(f"❌ Asistent #{i+1} nemá name - workflow nelze spustit")
                    raise Exception(f"❌ Asistent #{i+1} nemá name - workflow nelze spustit")
                
                function_key = assistant.get("function_key")
                if not function_key:
                    workflow.logger.error(f"❌ Asistent {assistant_name} nemá function_key - workflow nelze spustit")
                    raise Exception(f"❌ Asistent {assistant_name} nemá function_key - workflow nelze spustit")
                # Nastavení timeoutů pro asistenta - prodlouženo pro finální asistenty
                timeout = 600  # 10 minut pro dlouhé LLM odpovědi
                heartbeat = 180  # 3 minuty heartbeat pro Claude API volání
                
                stage_name = assistant_name
                stage_start = workflow.now().timestamp()
                workflow.logger.info(f"🤖 ASSISTANT_STARTED: {assistant_name} (function_key={function_key})")
                # Validace order - musí být specifikován
                order = assistant.get("order")
                if order is None:
                    workflow.logger.error(f"❌ Asistent {assistant_name} nemá order - workflow nelze spustit")
                    raise Exception(f"❌ Asistent {assistant_name} nemá order - workflow nelze spustit")
                
                stage_logs.append({
                    "stage": assistant_name, 
                    "status": "STARTED", 
                    "timestamp": stage_start,
                    "function_key": function_key,
                    "order": order
                })
                
                try:
                    # 🎯 INTELIGENTNÍ TOPIC SELECTION PRO KAŽDÉHO ASISTENTA
                    if function_key == "draft_assistant":
                        # DraftAssistant dostává kombinaci Brief + Research dat
                        brief_output = pipeline_data.get("brief_assistant_output", "")
                        research_output = pipeline_data.get("research_assistant_output", "")
                        
                        topic_input = f"""📋 BRIEF:
{brief_output}

📊 RESEARCH DATA:
{research_output}"""
                        
                        workflow.logger.info(f"🎯 DraftAssistant vstup: Brief ({len(brief_output)} chars) + Research ({len(research_output)} chars)")
                    
                    # ✅ STANDARDNÍ SEKVENČNÍ TOK pro všechny asistenty
                    topic_input = pipeline_data["current_output"]
                    
                    # Spuštění assistant activity s konfiguračními parametry  
                    assistant_output = await workflow.execute_activity(
                        "execute_assistant",
                        {
                            "assistant_config": assistant,
                            "topic": topic_input,  # 🔧 INTELIGENTNÍ TOPIC SELECTION
                            "current_date": pipeline_data["current_date"],  # 📅 AKTUÁLNÍ DATUM PRO VŠECHNY ASISTENTY
                            "previous_outputs": {k: v for k, v in pipeline_data.items() if k.endswith("_output")}
                        },
                        start_to_close_timeout=timedelta(seconds=600),  # 10 minut pro finální asistenty
                        schedule_to_close_timeout=timedelta(seconds=timeout),
                        heartbeat_timeout=timedelta(seconds=heartbeat),
                        retry_policy=temporalio.common.RetryPolicy(
                            initial_interval=timedelta(seconds=1),
                            maximum_interval=timedelta(seconds=10),
                            maximum_attempts=1,  # 🚫 ŽÁDNÉ RETRY - strict fail fast
                            backoff_coefficient=1.0
                        )
                    )
                    
                    # 🚫 STRICT OUTPUT VALIDATION - žádné fallbacky
                    if not assistant_output:
                        workflow.logger.error(f"❌ Asistent {assistant_name} nevrátil žádný výstup - workflow selhal")
                        raise Exception(f"❌ Asistent {assistant_name} nevrátil žádný výstup - workflow selhal")
                    
                    output_content = assistant_output.get("output")
                    if output_content is None:
                        workflow.logger.error(f"❌ Asistent {assistant_name} nevrátil 'output' klíč - workflow selhal")
                        raise Exception(f"❌ Asistent {assistant_name} nevrátil 'output' klíč - workflow selhal")
                    
                    # 🔧 INTELIGENTNÍ UPDATE PIPELINE DATA
                    # Ukládáme výstup podle function_key pro pozdější kombinování
                    pipeline_data[f"{function_key}_output"] = output_content
                    
                    # ✅ STANDARDNÍ SEKVENČNÍ TOK - aktualizace current_output
                    pipeline_data["current_output"] = output_content
                    
                    stage_duration = workflow.now().timestamp() - stage_start
                    workflow.logger.info(f"✅ ASSISTANT_FINISHED: {assistant_name} duration={stage_duration:.2f}s output_length={len(str(output_content))}")
                    
                    # Uložení úspěšného stage logu s výstupem
                    stage_logs.append({
                        "stage": assistant_name, 
                        "status": "COMPLETED", 
                        "timestamp": workflow.now().timestamp(), 
                        "duration": stage_duration,
                        "function_key": function_key,
                        "order": order,
                        "output": output_content,
                        "metadata": assistant_output.get("metadata") or {}
                    })
                    
                except Exception as assistant_error:
                    stage_duration = workflow.now().timestamp() - stage_start
                    workflow.logger.error(f"❌ ASSISTANT_FAILED: {assistant_name} duration={stage_duration:.2f}s error={str(assistant_error)}")
                    
                    # Uložení failed stage logu
                    stage_logs.append({
                        "stage": assistant_name, 
                        "status": "FAILED", 
                        "timestamp": workflow.now().timestamp(), 
                        "duration": stage_duration,
                        "function_key": function_key,
                        "order": order,  # 🚫 ŽÁDNÝ FALLBACK - order už je validovaný výše
                        "error": str(assistant_error)
                    })
                    
                    # 🚫 STRICT MODE - KAŽDÉ SELHÁNÍ ASISTENTA UKONČÍ WORKFLOW
                    workflow.logger.error(f"💥 ASSISTANT_FAILED: {assistant_name} - ukončuji workflow (strict mode)")
                    raise Exception(f"Asistent {assistant_name} selhal v strict mode: {str(assistant_error)}")

            # 3️⃣ Příprava finálního výsledku
            final_result = {
                "topic": topic,
                "project_id": project_id,
                "workflow_id": workflow_id,
                "run_id": run_id,
                "final_output": pipeline_data["current_output"],
                "stage_logs": stage_logs,
                "assistants_executed": len([log for log in stage_logs if log.get("status") == "COMPLETED" and log.get("stage") != "load_assistants_config"]),
                "total_assistants": len(assistants),
                "pipeline_success": True
            }

            # 4️⃣ Uložení finálního výsledku
            stage_name = "save_pipeline_result"
            stage_start = workflow.now().timestamp()
            workflow.logger.info(f"💾 STAGE_STARTED: {stage_name}")
            stage_logs.append({"stage": stage_name, "status": "STARTED", "timestamp": stage_start})
            
            try:
                saved_path = await workflow.execute_activity(
                    "save_output_to_json",
                    final_result,
                    schedule_to_close_timeout=timedelta(seconds=30)
                )
                
                stage_duration = workflow.now().timestamp() - stage_start
                workflow.logger.info(f"✅ STAGE_FINISHED: {stage_name} duration={stage_duration:.2f}s saved_to={saved_path}")
                stage_logs.append({"stage": stage_name, "status": "COMPLETED", "timestamp": workflow.now().timestamp(), "duration": stage_duration})
                
                final_result["saved_to"] = saved_path
                
            except Exception as save_error:
                stage_duration = workflow.now().timestamp() - stage_start
                workflow.logger.warning(f"⚠️ SAVE_FAILED: {stage_name} duration={stage_duration:.2f}s error={str(save_error)}")
                stage_logs.append({"stage": stage_name, "status": "FAILED", "timestamp": workflow.now().timestamp(), "duration": stage_duration, "error": str(save_error)})
                # Pokračujeme i bez uložení

            # Update finálních stage logs
            final_result["stage_logs"] = stage_logs
            
            total_duration = workflow.now().timestamp() - stage_logs[0]["timestamp"]
            completed_assistants = len([log for log in stage_logs if log.get("status") == "COMPLETED" and "Assistant" in log.get("stage", "")])
            
            # ✅ STRICT VALIDACE FINÁLNÍ PIPELINE - všichni načtení asistenti musí být dokončeni
            expected_assistants = len(assistants)
            if completed_assistants == expected_assistants:
                workflow.logger.info(f"🎉 ASSISTANT_PIPELINE_COMPLETED: total_duration={total_duration:.2f}s assistants_completed={completed_assistants}/{expected_assistants} ✅")
                workflow.logger.info(f"🏆 FINÁLNÍ PIPELINE ÚSPĚŠNĚ DOKONČENA - všech {expected_assistants} asistentů z databáze proběhlo!")
                
                # 🚀 AUTOMATICKÉ SPUŠTĚNÍ PUBLISH SCRIPTU PO DOKONČENÍ VŠECH ASISTENTŮ
                try:
                    stage_name = "PublishScript"
                    stage_start = workflow.now().timestamp()
                    workflow.logger.info(f"🚀 PUBLISH_SCRIPT_STARTED: po dokončení {expected_assistants} asistentů")
                    stage_logs.append({"stage": stage_name, "status": "STARTED", "timestamp": stage_start})
                    
                    # Připravení všech výstupů pro publish script
                    components = {
                        "brief_assistant_output": pipeline_data.get("brief_assistant_output", ""),
                        "research_assistant_output": pipeline_data.get("research_assistant_output", ""),
                        "fact_validator_assistant_output": pipeline_data.get("fact_validator_assistant_output", ""),
                        "draft_assistant_output": pipeline_data.get("draft_assistant_output", ""),
                        "humanizer_assistant_output": pipeline_data.get("humanizer_assistant_output", ""),
                        "seo_assistant_output": pipeline_data.get("seo_assistant_output", ""),
                        "multimedia_assistant_output": pipeline_data.get("multimedia_assistant_output", ""),
                        "qa_assistant_output": pipeline_data.get("qa_assistant_output", ""),
                        "image_renderer_assistant_output": pipeline_data.get("image_renderer_assistant_output", "")
                    }
                    
                    active_components = [k for k,v in components.items() if v]
                    workflow.logger.info(f"🔧 PUBLISH SCRIPT: {len(active_components)} aktivních komponent z pipeline")
                    
                    # Spuštění publish_activity
                    publish_output = await workflow.execute_activity(
                        "publish_activity",
                        {
                            "assistant_config": {"name": "PublishScript", "function_key": "publish_script"},
                            "topic": components,  # Pipeline data ze všech asistentů
                            "current_date": pipeline_data["current_date"],
                            "previous_outputs": {k: v for k, v in pipeline_data.items() if k.endswith("_output")}
                        },
                        start_to_close_timeout=timedelta(seconds=300),  # 5 minut pro deterministický script
                        schedule_to_close_timeout=timedelta(seconds=300),
                        heartbeat_timeout=timedelta(seconds=60),
                        retry_policy=temporalio.common.RetryPolicy(
                            initial_interval=timedelta(seconds=1),
                            maximum_interval=timedelta(seconds=5),
                            maximum_attempts=1,  # 🚫 ŽÁDNÉ RETRY - strict fail fast
                            backoff_coefficient=1.0
                        )
                    )
                    
                    stage_duration = workflow.now().timestamp() - stage_start
                    if publish_output and publish_output.get("success") == True:
                        workflow.logger.info(f"✅ PUBLISH_SCRIPT_COMPLETED: duration={stage_duration:.2f}s")
                        stage_logs.append({"stage": stage_name, "status": "COMPLETED", "timestamp": workflow.now().timestamp(), "duration": stage_duration, "output": publish_output})
                        
                        # Přidej publish output do finálního výsledku
                        final_result["publish_output"] = publish_output
                    else:
                        workflow.logger.error(f"❌ PUBLISH_SCRIPT_FAILED: duration={stage_duration:.2f}s")
                        workflow.logger.error(f"❌ PUBLISH_OUTPUT_DEBUG: {publish_output}")
                        stage_logs.append({"stage": stage_name, "status": "FAILED", "timestamp": workflow.now().timestamp(), "duration": stage_duration, "error": "Publish script failed"})
                        
                except Exception as publish_error:
                    stage_duration = workflow.now().timestamp() - stage_start if 'stage_start' in locals() else 0
                    workflow.logger.error(f"❌ PUBLISH_SCRIPT_ERROR: {str(publish_error)} duration={stage_duration:.2f}s")
                    stage_logs.append({"stage": "PublishScript", "status": "FAILED", "timestamp": workflow.now().timestamp(), "duration": stage_duration, "error": str(publish_error)})
                    # Nepokračujeme s chybou - publish script není kritický pro úspěch pipeline
                
            else:
                # 🚫 STRICT MODE - pokud neproběhly všichni asistenti, je to chyba
                error_msg = f"NEÚPLNÁ PIPELINE - očekáváno {expected_assistants} asistentů z databáze, dokončeno pouze {completed_assistants}"
                workflow.logger.error(f"❌ {error_msg}")
                raise Exception(error_msg)
            
            return final_result
            
        except Exception as e:
            # Log failed pipeline
            current_stage = stage_logs[-1]["stage"] if stage_logs else "UNKNOWN"
            workflow.logger.error(f"❌ PIPELINE_FAILED: topic='{topic}' project_id={project_id} error={str(e)} current_stage={current_stage}")
            
            # Přidej failed log pokud ještě není
            if not stage_logs or stage_logs[-1].get("status") != "FAILED":
                stage_logs.append({
                    "stage": current_stage, 
                    "status": "FAILED", 
                    "timestamp": workflow.now().timestamp(), 
                    "error": str(e)
                })
            
            # 🚫 STRICT FAILED RESULT - žádné fallbacky
            current_output = pipeline_data.get("current_output")
            if current_output is None:
                current_output = "PIPELINE_FAILED_NO_OUTPUT"
            
            failed_result = {
                "topic": topic,
                "project_id": project_id,
                "workflow_id": workflow_id,
                "run_id": run_id,
                "final_output": current_output,
                "stage_logs": stage_logs,
                "pipeline_success": False,
                "error": str(e),
                "failed_stage": current_stage
            }
            
            workflow.logger.error(f"💥 RETURNING_FAILED_RESULT: error={str(e)}")
            return failed_result 