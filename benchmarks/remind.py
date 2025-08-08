#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   remind.py
@Time    :   2025/08/08
@Author  :   Deng Mingyi
"""

from typing import Tuple, List, Callable, Dict, Any
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from benchmarks.benchmark import BaseBenchmark
from utils.logs import logger
from utils.async_llm import create_llm_instance

class RemindBenchmark(BaseBenchmark):
    def __init__(self, name: str, file_path: str, log_path: str, grader_config):
        super().__init__(name, file_path, log_path)
        self.grader_llm = create_llm_instance(grader_config)

    def parse_response(self) -> Tuple[float, str]:

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), retry=retry_if_exception_type(Exception), reraise=True)
    async def _generate_output(self, workflow, task: str):
        return await workflow(task)

    async def calculate_score(self, ) -> Tuple[float, str]:

    async def evaluate_problem(self, problem: dict, workflow: Callable) -> Tuple[str, str, str, List[dict], float, float]:

    def get_result_columns(self) -> List[str]: