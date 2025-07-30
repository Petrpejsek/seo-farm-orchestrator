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
    async def run(self, topic: str, project_id: Optional[str] = None, csv_base64: Optional[str] = None) -> dict:
        workflow_id = workflow.info().workflow_id
        run_id = workflow.info().run_id
        
        workflow.logger.info(f"🚀 ASSISTANT_PIPELINE_STARTED: topic='{topic}' project_id={project_id} workflow_id={workflow_id} run_id={run_id}")
        
        # Inicializace stage logs pro tracking
        stage_logs = []
        pipeline_data = {
            "topic": topic,
            "project_id": project_id,
            "csv_base64": csv_base64,
            "current_output": topic  # Začneme s tématem jako prvním vstupem
        }
        
        try:
            # 1️⃣ Načtení asistentů z databáze podle project_id
            stage_name = "load_assistants_config"
            stage_start = workflow.now().timestamp()
            workflow.logger.info(f"📋 STAGE_STARTED: {stage_name} for project_id={project_id}")
            stage_logs.append({"stage": stage_name, "status": "STARTED", "timestamp": stage_start})
            
            assistants_config = await workflow.execute_activity(
                "load_assistants_from_database",
                project_id or "",  # ← Předávám přímo string místo dict
                schedule_to_close_timeout=timedelta(seconds=30),
                heartbeat_timeout=timedelta(seconds=10)
            )
            
            stage_duration = workflow.now().timestamp() - stage_start
            workflow.logger.info(f"✅ STAGE_FINISHED: {stage_name} duration={stage_duration:.2f}s assistants_count={len(assistants_config)}")
            stage_logs.append({"stage": stage_name, "status": "COMPLETED", "timestamp": workflow.now().timestamp(), "duration": stage_duration})

            assistants = assistants_config  # assistants_config je už přímo list
            if not assistants:
                workflow.logger.warning("⚠️ Žádní asistenti nenalezeni - ukončuji workflow")
                raise Exception("Žádní aktivní asistenti nenalezeni pro daný projekt")

            # 2️⃣ Postupné spuštění asistentů podle pořadí
            for assistant in assistants:
                assistant_name = assistant.get("name", "UnknownAssistant")
                function_key = assistant.get("function_key", "")
                # Nastavení timeoutů pro asistenta - prodlouženo pro finální asistenty
                timeout = 300  # 5 minut místo 3 minut
                heartbeat = 60  # 60s heartbeat místo 30s
                
                stage_name = assistant_name
                stage_start = workflow.now().timestamp()
                workflow.logger.info(f"🤖 ASSISTANT_STARTED: {assistant_name} (function_key={function_key})")
                stage_logs.append({
                    "stage": assistant_name, 
                    "status": "STARTED", 
                    "timestamp": stage_start,
                    "function_key": function_key,
                    "order": assistant.get("order", 0)
                })
                
                try:
                    # Spuštění assistant activity s konfiguračními parametry  
                    assistant_output = await workflow.execute_activity(
                        "execute_assistant",
                        {
                            "assistant_config": assistant,
                            "topic": topic, 
                            "previous_outputs": {}
                        },
                        start_to_close_timeout=timedelta(seconds=600),  # 10 minut pro finální asistenty
                        schedule_to_close_timeout=timedelta(seconds=timeout),
                        heartbeat_timeout=timedelta(seconds=heartbeat),
                        retry_policy=temporalio.common.RetryPolicy(
                            initial_interval=timedelta(seconds=1),
                            maximum_interval=timedelta(seconds=60),
                            maximum_attempts=3,
                            backoff_coefficient=2.0
                        )
                    )
                    
                    # Update pipeline data s výstupem asistenta
                    pipeline_data["current_output"] = assistant_output.get("output", "")
                    
                    stage_duration = workflow.now().timestamp() - stage_start
                    workflow.logger.info(f"✅ ASSISTANT_FINISHED: {assistant_name} duration={stage_duration:.2f}s output_length={len(str(pipeline_data['current_output']))}")
                    
                    # Uložení úspěšného stage logu s výstupem
                    stage_logs.append({
                        "stage": assistant_name, 
                        "status": "COMPLETED", 
                        "timestamp": workflow.now().timestamp(), 
                        "duration": stage_duration,
                        "function_key": function_key,
                        "order": assistant.get("order", 0),
                        "output": assistant_output.get("output", ""),
                        "metadata": assistant_output.get("metadata", {})
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
                        "order": assistant.get("order", 0),
                        "error": str(assistant_error)
                    })
                    
                    # Rozhodnutí o pokračování nebo ukončení
                    if assistant.get("critical", True):  # Pokud je asistent kritický, ukončíme workflow
                        workflow.logger.error(f"💥 CRITICAL_ASSISTANT_FAILED: {assistant_name} - ukončuji workflow")
                        raise Exception(f"Kritický asistent {assistant_name} selhal: {str(assistant_error)}")
                    else:
                        workflow.logger.warning(f"⚠️ NON_CRITICAL_ASSISTANT_FAILED: {assistant_name} - pokračuji s dalším asistent")
                        continue

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
            
            workflow.logger.info(f"🎉 ASSISTANT_PIPELINE_COMPLETED: total_duration={total_duration:.2f}s assistants_completed={completed_assistants}/{len(assistants)}")
            
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
            
            # Vrať částečný výsledek s chybou
            failed_result = {
                "topic": topic,
                "project_id": project_id,
                "workflow_id": workflow_id,
                "run_id": run_id,
                "final_output": pipeline_data.get("current_output", ""),
                "stage_logs": stage_logs,
                "pipeline_success": False,
                "error": str(e),
                "failed_stage": current_stage
            }
            
            workflow.logger.error(f"💥 RETURNING_FAILED_RESULT: error={str(e)}")
            return failed_result 