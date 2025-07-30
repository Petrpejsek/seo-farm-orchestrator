import json
import os
from temporalio import workflow
from datetime import timedelta

@workflow.defn
class SEOWorkflow:
    @workflow.run
    async def run(self, topic: str) -> dict:
        workflow_id = workflow.info().workflow_id
        run_id = workflow.info().run_id
        
        workflow.logger.info(f"🚀 WORKFLOW_STARTED: topic='{topic}' workflow_id={workflow_id} run_id={run_id}")
        
        # Inicializace stage logs pro tracking
        stage_logs = []
        
        try:
            # 1️⃣ Generování LLM-friendly obsahu
            stage_name = "generate_llm_friendly_content"
            stage_start = workflow.now().timestamp()
            workflow.logger.info(f"🔄 STAGE_STARTED: {stage_name}")
            stage_logs.append({"stage": stage_name, "status": "STARTED", "timestamp": stage_start})
            
            content = await workflow.execute_activity(
                "generate_llm_friendly_content",
                topic,
                schedule_to_close_timeout=timedelta(seconds=120),  # Zvýšen timeout
                heartbeat_timeout=timedelta(seconds=30)
            )
            
            stage_duration = workflow.now().timestamp() - stage_start
            workflow.logger.info(f"✅ STAGE_FINISHED: {stage_name} duration={stage_duration:.2f}s")
            stage_logs.append({"stage": stage_name, "status": "COMPLETED", "timestamp": workflow.now().timestamp(), "duration": stage_duration})

            # 2️⃣ Přidání strukturovaného JSON-LD
            stage_name = "inject_structured_markup"
            stage_start = workflow.now().timestamp()
            workflow.logger.info(f"🔄 STAGE_STARTED: {stage_name}")
            stage_logs.append({"stage": stage_name, "status": "STARTED", "timestamp": stage_start})
            
            structured = await workflow.execute_activity(
                "inject_structured_markup",
                content,
                schedule_to_close_timeout=timedelta(seconds=60),
                heartbeat_timeout=timedelta(seconds=15)
            )
            
            stage_duration = workflow.now().timestamp() - stage_start
            workflow.logger.info(f"✅ STAGE_FINISHED: {stage_name} duration={stage_duration:.2f}s")
            stage_logs.append({"stage": stage_name, "status": "COMPLETED", "timestamp": workflow.now().timestamp(), "duration": stage_duration})

            # 3️⃣ Obohacení entitami
            stage_name = "enrich_with_entities"
            stage_start = workflow.now().timestamp()
            workflow.logger.info(f"🔄 STAGE_STARTED: {stage_name}")
            stage_logs.append({"stage": stage_name, "status": "STARTED", "timestamp": stage_start})
            
            enriched = await workflow.execute_activity(
                "enrich_with_entities",
                structured,
                schedule_to_close_timeout=timedelta(seconds=60),
                heartbeat_timeout=timedelta(seconds=15)
            )
            
            stage_duration = workflow.now().timestamp() - stage_start
            workflow.logger.info(f"✅ STAGE_FINISHED: {stage_name} duration={stage_duration:.2f}s")
            stage_logs.append({"stage": stage_name, "status": "COMPLETED", "timestamp": workflow.now().timestamp(), "duration": stage_duration})

            # 4️⃣ Přidání konverzačních FAQ
            stage_name = "add_conversational_faq"
            stage_start = workflow.now().timestamp()
            workflow.logger.info(f"🔄 STAGE_STARTED: {stage_name}")
            stage_logs.append({"stage": stage_name, "status": "STARTED", "timestamp": stage_start})
            
            faq_final = await workflow.execute_activity(
                "add_conversational_faq",
                enriched,
                schedule_to_close_timeout=timedelta(seconds=60),
                heartbeat_timeout=timedelta(seconds=15)
            )
            
            stage_duration = workflow.now().timestamp() - stage_start
            workflow.logger.info(f"✅ STAGE_FINISHED: {stage_name} duration={stage_duration:.2f}s")
            stage_logs.append({"stage": stage_name, "status": "COMPLETED", "timestamp": workflow.now().timestamp(), "duration": stage_duration})

            # Příprava výsledného objektu
            result = {
                "topic": topic,
                "generated": content,
                "structured": structured,
                "enriched": enriched,
                "faq_final": faq_final,
                "workflow_id": workflow_id,
                "run_id": run_id,
                "stage_logs": stage_logs
            }

            # 5️⃣ Ukládání výstupu jako JSON soubor
            stage_name = "save_output_to_json"
            stage_start = workflow.now().timestamp()
            workflow.logger.info(f"🔄 STAGE_STARTED: {stage_name}")
            stage_logs.append({"stage": stage_name, "status": "STARTED", "timestamp": stage_start})
            
            saved_path = await workflow.execute_activity(
                "save_output_to_json",
                result,
                schedule_to_close_timeout=timedelta(seconds=30)
            )
            
            stage_duration = workflow.now().timestamp() - stage_start
            workflow.logger.info(f"✅ STAGE_FINISHED: {stage_name} duration={stage_duration:.2f}s")
            stage_logs.append({"stage": stage_name, "status": "COMPLETED", "timestamp": workflow.now().timestamp(), "duration": stage_duration})

            # Přidání cesty k uloženému souboru do výsledku
            result["saved_to"] = saved_path
            result["stage_logs"] = stage_logs  # Update s finálními logs
            
            total_duration = workflow.now().timestamp() - stage_logs[0]["timestamp"]
            workflow.logger.info(f"🎉 WORKFLOW_COMPLETED: total_duration={total_duration:.2f}s stages={len([l for l in stage_logs if l['status'] == 'COMPLETED'])}")
            
            return result
            
        except Exception as e:
            # Log failed stage
            current_stage = stage_logs[-1]["stage"] if stage_logs else "UNKNOWN"
            workflow.logger.error(f"❌ STAGE_FAILED: {current_stage} error={str(e)}")
            stage_logs.append({"stage": current_stage, "status": "FAILED", "timestamp": workflow.now().timestamp(), "error": str(e)})
            
            workflow.logger.error(f"💥 WORKFLOW_FAILED: topic='{topic}' error={str(e)} stage={current_stage}")
            raise 