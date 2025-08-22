#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   benchmarks/remind.py
@Time    :   2025/08/11
@Author  :   Deng Mingyi
"""

from typing import Tuple, List, Callable, Any
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from benchmarks.benchmark import BaseBenchmark
from utils.logs import logger
from utils.async_llm import AsyncLLM

GRADING_PROMPT = """\nYou are an impartial grader.

Question: {question}
Predicted Answer: {predicted_answer}
Correct Answer: {correct_answer}

CRITICAL GRADING INSTRUCTIONS:
1. The predicted answer must match the CORRECT ANSWER
2. Look for EXACT name matches or clear references to the same entity
3. Consider different languages, translations, or alternative names as potential matches
4. Be strict: partial matches or vague similarities should be 'no'

IMPORTANT: Give ONLY one score:
- 'yes': The predicted answer correctly identifies the same entity as the correct answer
- 'no': The predicted answer is wrong, matches the popular answer, or refers to a different entity

Respond with ONLY 'yes' or 'no', nothing else."""

class RemindBenchmark(BaseBenchmark):
    
    def __init__(self, name: str, file_path: str, log_path: str, grader_config:str="gpt-4o"):
        super().__init__(name, file_path, log_path)
        self.grader_llm = AsyncLLM(grader_config)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), retry=retry_if_exception_type(Exception), reraise=True)
    async def _generate_output(self, agent, task: dict):
        return await agent(task)

    async def evaluate_problem(self, problem: dict, agent: Callable) -> Tuple[str, str, str, str, float, float]:
        
        question = problem["question"]
        correct_answer = problem.get("answer", "")
        
        logger.info(f"\n🎯 EVALUATING: {question}")
        
        try:
            predicted_answer, history, cost = await self._generate_output(agent, problem)
            score = await self.calculate_score(question, correct_answer, predicted_answer)
            history_summary = self._generate_history_summary(history)

            return question, correct_answer, predicted_answer, history_summary, score, cost

        except Exception as e:
            logger.error(f"Error evaluating problem: {e}")
            print(f"❌ Evaluation Error: {e}")
            return question, correct_answer, "Error", "Error", 0.0, 0.0

    async def calculate_score(self, question: str, correct_answer: str, predicted_answer: str) -> float:

        grading_prompt = GRADING_PROMPT.format(
            question=question,
            predicted_answer=predicted_answer,
            correct_answer=correct_answer
        )

        try:
            response = await self.grader_llm(grading_prompt)
            
            if "yes" in response.strip():
                print(f"🎓 LLM Grader: CORRECT")
                return 1.0
            elif "no" in response.strip():
                print(f"🎓 LLM Grader: INCORRECT")
                return 0.0
                    
        except Exception as e:
            print(f"❌ LLM grading failed: {e}")
            return 0.0

    def _generate_history_summary(self, history: List[dict]) -> str:
        if not history:
            return "No interactions"
        
        summary_parts = []
        for item in history:
            turn = item.get("turn", "?")
            
            if item.get("question_asked"):
                query = item.get("question_asked", "?")
                response = item.get("response", "?")
                summary_parts.append(f"T{turn}:Ask({query}) Result:{response}")
            elif item.get("search_query"):
                query = item.get("search_query", "?")
                results = item.get("search_results", [])
                summary_parts.append(f"T{turn}:Search({query}) Result:{results}")
            elif item.get("final_answer"):
                answer = item.get("final_answer", "?")
                summary_parts.append(f"T{turn}:Answer({answer})")

        return f"{summary_parts}"

    def get_result_columns(self) -> List[str]:
        return ["question", "correct_answer", "predicted_answer", "history_summary", "score", "cost"]