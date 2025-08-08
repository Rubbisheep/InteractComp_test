#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   IO.py
@Time    :   2025/06/16
@Author  :   Deng Mingyi
@Desc    :  workflow for IO
"""

from workflow.base import Workflow

class IOWorkflow(Workflow):
    def __init__(
        self,
        name: str,
        llm_config,
        dataset,
        prompt: str,
    ) -> None:
        super().__init__(name, llm_config, dataset)
        self.prompt = prompt

    async def __call__(self, problem: str):
        full_input = self.prompt + problem
        response = await self.llm(full_input)
        return response, self.llm.get_usage_summary()["total_cost"]