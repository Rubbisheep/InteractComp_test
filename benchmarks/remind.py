#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   benchmarks/remind.py
@Time    :   2025/08/11
@Author  :   Deng Mingyi
"""

from typing import Tuple, List, Callable, Any
from benchmarks.benchmark import BaseBenchmark
from utils.logs import logger
from utils.async_llm import create_llm_instance, LLMsConfig


class RemindBenchmark(BaseBenchmark):
    
    def __init__(self, name: str, file_path: str, log_path: str, grader_config=LLMsConfig.default().get("gpt-4o")):
        super().__init__(name, file_path, log_path)
        self.grader_llm = create_llm_instance(grader_config)

    async def evaluate_problem(self, problem: dict, agent: Callable) -> Tuple[str, str, str, str, float, float]:
        
        question = problem["q0"]
        correct_answer = problem.get("B_hidden", "")
        
        print(f"\n🎯 EVALUATING: {question[:80]}...")
        
        try:
            predicted_answer, context, cost = await agent(problem)
            score = await self.calculate_score(question, correct_answer, predicted_answer, problem)

            print(f"📝 Correct Answer: {correct_answer}")
            print(f"🤖 Agent Answer: {predicted_answer}")
            print(f"⭐ Score: {score:.2f}")
            print(f"💰 Cost: ${cost:.4f}")
            
            context_summary = self._generate_context_summary(context)
            return question, correct_answer, predicted_answer, context_summary, score, cost
            
        except Exception as e:
            logger.error(f"Error evaluating problem: {e}")
            print(f"❌ Evaluation Error: {e}")
            return question, correct_answer, "Error", "Error", 0.0, 0.0

    async def calculate_score(self, question: str, correct_answer: str, predicted_answer: str, problem: dict) -> float:
        a_pop = problem.get("A_pop", "")

        grading_prompt = f"""\n"You are a strict grading assistant. Your task is to determine if the predicted answer is EXACTLY correct.

Question: {question}

Correct Answer: {correct_answer}
Popular wrong Answer: {a_pop}

Predicted Answer: {predicted_answer}

CRITICAL GRADING INSTRUCTIONS:
1. The predicted answer must match the CORRECT ANSWER
2. Look for EXACT name matches or clear references to the same entity
3. If the prediction matches the popular answer but NOT the correct answer, score it as 0.0
4. Consider different languages, translations, or alternative names as potential matches
5. Be strict: partial matches or vague similarities should score 0.0

EXAMPLES:
- If correct="Kabaneri of the Iron Fortress" and predicted="Attack on Titan" → Score: 0.0 (matches popular but wrong)
- If correct="Kabaneri of the Iron Fortress" and predicted="Kabaneri" → Score: 1.0 (references to the same entity)
- If correct="Miranda v. Arizona" and predicted="Gideon v. Wainwright" → Score: 0.0 (different cases)

IMPORTANT: Give ONLY one score:
- 1.0: The predicted answer correctly identifies the same entity as the correct answer
- 0.0: The predicted answer is wrong, matches the popular answer, or refers to a different entity

Respond with ONLY "1.0" or "0.0", nothing else."""

        try:
            response = await self.grader_llm(grading_prompt)
            score_text = response.strip()
            
            if "1.0" in score_text:
                print(f"🎓 LLM Grader: CORRECT (1.0)")
                return 1.0
            elif "0.0" in score_text:
                print(f"🎓 LLM Grader: INCORRECT (0.0)")
                return 0.0
                    
        except Exception as e:
            print(f"❌ LLM grading failed: {e}")
            return 0.0

    def _generate_context_summary(self, context: List[dict]) -> str:
        if not context:
            return "No interactions"
        
        summary_parts = []
        for item in context:
            turn = item.get("turn", "?")
            
            if item.get("question_asked"):
                response = item.get("human_response", "?")
                summary_parts.append(f"T{turn}:Ask({response})")
            elif item.get("search_query"):
                results_count = len(item.get("search_results", []))
                summary_parts.append(f"T{turn}:Search({results_count})")
            elif item.get("final_answer"):
                forced = " (forced)" if item.get("forced") else ""
                summary_parts.append(f"T{turn}:Answer{forced}")

        return f"{summary_parts}"

    def get_result_columns(self) -> List[str]:
        return ["question", "correct_answer", "predicted_answer", "context_summary", "score", "cost"]