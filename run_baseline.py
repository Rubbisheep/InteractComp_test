#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   run_baseline.py
@Time    :   2025/08/11
@Author  :   Deng Mingyi1
"""

import asyncio
from utils.logs import logger

from benchmarks.InteractComp import InteractCompBenchmark
from workflow.InteractComp import InteractCompAgent

async def main():
    dataset_path = "data/data.jsonl"
    log_path = "workspace/"
    prompt = ""
    
    results_summary = []

    agent = InteractCompAgent(
        name="InteractComp",
        llm_config="o3",
        dataset="InteractComp",
        prompt=prompt,
        max_turns=5,
        search_engine_type="google", # llm_knowledge, google, wikipedia
        user_config="gpt-4o"
    )

    benchmark = InteractCompBenchmark(
        name=f"InteractComp", 
        file_path=dataset_path, 
        log_path=log_path,
        grader_config="gpt-4o"
    )

    results = await benchmark.run_baseline(agent, max_concurrent_tasks=1)
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