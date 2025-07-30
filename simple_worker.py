from temporalio.client import Client
from temporalio.worker import Worker

# Import workflow
from workflows.simple_seo_workflow import SimpleSEOWorkflow

# Import jen jedné aktivity
from activities.generate_llm_friendly_content import generate_llm_friendly_content

async def main():
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="default",
        workflows=[SimpleSEOWorkflow],
        activities=[generate_llm_friendly_content],
    )
    print("✅ Simple Worker ready!")
    await worker.run()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 