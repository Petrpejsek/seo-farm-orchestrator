import asyncio
import logging
from temporalio.client import Client  
from temporalio.worker import Worker

# Console logging místo souboru
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Workflows
from workflows.assistant_pipeline_workflow import AssistantPipelineWorkflow
from activities.assistant_activities import execute_assistant

async def main():
    client = await Client.connect("localhost:7233", namespace="default")
    worker = Worker(
        client, 
        task_queue="default",
        workflows=[AssistantPipelineWorkflow],
        activities=[execute_assistant]
    )
    logger.info("✅ Simple Worker spuštěn")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
