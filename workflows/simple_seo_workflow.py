from temporalio import workflow

@workflow.defn
class SimpleSEOWorkflow:
    @workflow.run
    async def run(self, topic: str) -> str:
        # Importy jsou nyní top-level, takže použijeme string reference
        content = await workflow.execute_activity(
            "generate_llm_friendly_content", 
            topic, 
            schedule_to_close_timeout=30
        )
        
        return content 