#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   run_baseline.py
@Time    :   2025/08/11
@Author  :   Deng Mingyi1
"""

import asyncio
from utils.async_llm import LLMsConfig
from utils.logs import logger

from benchmarks.remind import RemindBenchmark 
from workflow.remind import RemindWorkflow

async def main():
    dataset_path = "data/data.jsonl"
    log_path = "workspace/"
    llm_config = LLMsConfig.default().get("gpt-4o")
    prompt = ""

    logger.info("🚀 INITIALIZING REMIND BENCHMARK")
    logger.info("="*60)
    
    results_summary = []
    print("-" * 60)
    
    workflow = RemindWorkflow(
        name="Remind",
        llm_config=llm_config,
        dataset="Remind",
        prompt=prompt,
        mode="EASY",  # HARD or EASY
        max_turns=5,
        search_engine_type="wikipedia",
        interactive=False
    )

    benchmark = RemindBenchmark(
        name=f"Remind_{"wikipedia"}", 
        file_path=dataset_path, 
        log_path=log_path,
        grader_config=llm_config
    )
    
    results = await benchmark.run_baseline(workflow, max_concurrent_tasks=1)
    avg_score, avg_cost, total_cost = results
    
    results_summary.append({
        "engine": "LLM Knowledge Search",
        "engine_type": "llm_knowledge",
        "avg_score": avg_score,
        "avg_cost": avg_cost,
        "total_cost": total_cost
    })
    
    print(f"🎯 Average Score: {avg_score:.3f} ({avg_score*100:.1f}%)")
    print(f"💰 Average Cost: ${avg_cost:.4f}")
    print(f"💰 Total Cost: ${total_cost:.4f}")
    return results_summary

if __name__ == "__main__":
    asyncio.run(main())