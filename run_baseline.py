#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   run_baseline.py
@Time    :   2025/07/21
@Author  :   Deng Mingyi
@Desc    :   Run baseline for benchmarks with prompts
"""

import asyncio
from typing import Literal
from utils.async_llm import LLMsConfig
from utils.logs import logger
from benchmarks.remind import RemindBenchmark
from workflow.remind import RemindWorkflow

async def main():
    dataset_path = "data/data.jsonl"
    log_path = "workspace/"
    llm_config = LLMsConfig.default().get("gpt-4o-mini")
    prompt = ""

    workflow = RemindWorkflow(
    name="Remind",
    llm_config=llm_config,
    dataset = "Remind",
    prompt=prompt
    )

    benchmark = RemindBenchmark(name="Remind", file_path=dataset_path, log_path=log_path)

    results = await benchmark.run_baseline(workflow, max_concurrent_tasks=1)
    return results

if __name__ == "__main__":
    asyncio.run(main())

