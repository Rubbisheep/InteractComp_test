import asyncio
import os
from utils.async_llm import LLMsConfig
from utils.logs import logger
from benchmarks.remind import RemindBenchmark
from workflow.remind import RemindWorkflow

async def main():
    dataset_path = "data/data.jsonl"
    log_path = "workspace/"
    
    os.makedirs(log_path, exist_ok=True)
    
    llm_config = LLMsConfig.default().get("gpt-4o")
    prompt = ""

    workflow = RemindWorkflow(
        name="Remind",
        llm_config=llm_config,
        dataset="Remind",
        prompt=prompt
    )

    benchmark = RemindBenchmark(
        name="Remind", 
        file_path=dataset_path, 
        log_path=log_path,
        grader_config=LLMsConfig.default().get("o3-mini")
    )

    logger.info("Starting REMIND benchmark evaluation...")
    results = await benchmark.run_baseline(workflow, max_concurrent_tasks=1)
    
    step1_score, avg_cost, total_cost = results
    logger.info("Evaluation completed!")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())