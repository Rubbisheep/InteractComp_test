#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   run_baseline.py
@Time    :   2025/08/11
@Author  :   Deng Mingyi
@Desc    :   Run baseline for benchmarks with prompts
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
    
    prompt = """You are an intelligent search agent designed to answer questions by strategically gathering information.

Your task: Given a question that might have multiple plausible answers, determine the correct answer through targeted information gathering.

Available actions:
- ask: Ask a specific question to get more information (you'll get yes/no/idk responses)
- search: Search for external information using a search engine  
- answer: Provide your final answer when confident

Strategy: Focus on asking questions that help distinguish between similar options. Use search for verification. Answer when you have sufficient distinguishing information.

Format your response as:
<thought>Your reasoning about what to do next</thought>
<action>ask:question OR search:query OR answer:your_answer</action>"""

    print("🚀 INITIALIZING REMIND BENCHMARK")
    print("="*60)
    print("📋 Framework Features:")
    print("  - General-purpose design (any domain)")
    print("  - LLM-based answer evaluation")
    print("  - Human Agent with similarity matching")
    print("  - Configurable search engines")
    print("="*60)
    
    workflow = RemindWorkflow(
        name="Remind",
        llm_config=llm_config,
        dataset="Remind",
        prompt=prompt,
        mode="EASY",  # HARD or EASY
        max_turns=5,
        search_engine_type="mock"  # mock, real, or hybrid
    )

    benchmark = RemindBenchmark(
        name="Remind", 
        file_path=dataset_path, 
        log_path=log_path,
        grader_config=llm_config  # 使用相同的LLM配置进行评分
    )

    print("📊 STARTING EVALUATION")
    print("="*60)
    
    results = await benchmark.run_baseline(workflow, max_concurrent_tasks=1)
    
    avg_score, avg_cost, total_cost = results
    
    print("\n" + "="*60)
    print("📈 FINAL RESULTS")
    print("="*60)
    print(f"🎯 Average Score: {avg_score:.3f} ({avg_score*100:.1f}%)")
    print(f"💰 Average Cost: ${avg_cost:.4f}")
    print(f"💰 Total Cost: ${total_cost:.4f}")
    print("="*60)
    
    logger.info(f"Average Score: {avg_score:.3f}")
    logger.info(f"Total Cost: ${total_cost:.4f}")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())