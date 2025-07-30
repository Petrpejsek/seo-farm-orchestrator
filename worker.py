import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

# Workflows
from workflows.seo_workflow import SEOWorkflow
from workflows.assistant_pipeline_workflow import AssistantPipelineWorkflow

# Original activities (only the ones that exist)
from activities.generate_llm_friendly_content import generate_llm_friendly_content
from activities.inject_structured_markup import inject_structured_markup
from activities.save_output_to_json import save_output_to_json

# New assistant activities
from activities.assistant_activities import load_assistants_from_database, execute_assistant

async def main():
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="default",
        workflows=[
            SEOWorkflow,
            AssistantPipelineWorkflow
        ],
        activities=[
            # Original activities (that exist)
            generate_llm_friendly_content,
            inject_structured_markup,
            save_output_to_json,
            # New assistant activities
            load_assistants_from_database,
            execute_assistant
        ],
    )
    print("✅ ENHANCED SEO Worker (Original + AssistantPipeline) je připraven a čeká na úkoly…")
    print("   🤖 Workflows: SEOWorkflow, AssistantPipelineWorkflow")
    print("   ⚙️ Activities: 3 original + 2 assistant activities")
    await worker.run()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 