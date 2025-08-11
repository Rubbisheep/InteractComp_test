#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   benchmarks/remind.py
@Time    :   2025/08/11
@Author  :   Deng Mingyi
@Desc    :   Remind数据集评估，通用化设计，使用LLM判断答案正确性
"""

from typing import Tuple, List, Callable, Any
from benchmarks.benchmark import BaseBenchmark
from utils.logs import logger
from utils.async_llm import create_llm_instance


class RemindBenchmark(BaseBenchmark):
    """Remind数据集评估基准 - 通用化设计"""
    
    def __init__(self, name: str, file_path: str, log_path: str, grader_config=None):
        super().__init__(name, file_path, log_path)
        
        # 初始化评分用的LLM
        if grader_config is None:
            from utils.async_llm import LLMsConfig
            grader_config = LLMsConfig.default().get("gpt-4o-mini")
        
        self.grader_llm = create_llm_instance(grader_config)

    async def evaluate_problem(self, problem: dict, workflow: Callable) -> Tuple[str, str, str, str, float, float]:
        """
        评估单个问题
        Returns: (question, correct_answer, predicted_answer, context_summary, score, cost)
        """
        question = problem["q0"]
        
        # 根据info_items确定正确答案
        correct_answer = self._determine_correct_answer(problem)
        
        print(f"\n🎯 EVALUATING: {question[:80]}...")
        print(f"📝 Correct Answer: {correct_answer}")
        print(f"🔍 Info items: {problem.get('info_items', [])}")
        
        try:
            # 调用search agent
            predicted_answer, context, cost = await workflow(problem)
            
            # 使用LLM进行评分
            print(f"\n📊 SCORING PHASE")
            print(f"🤖 Agent Answer: {predicted_answer}")
            
            score = await self._llm_score(question, correct_answer, predicted_answer, problem)
            
            print(f"⭐ Score: {score:.2f}")
            print(f"💰 Cost: ${cost:.4f}")
            
            # 生成上下文摘要
            context_summary = self._generate_context_summary(context)
            
            return question, correct_answer, predicted_answer, context_summary, score, cost
            
        except Exception as e:
            logger.error(f"Error evaluating problem: {e}")
            print(f"❌ Evaluation Error: {e}")
            return question, correct_answer, "Error", "Error", 0.0, 0.0

    def _determine_correct_answer(self, problem: dict) -> str:
        """
        确定正确答案：永远是B_hidden
        """
        b_hidden = problem.get("B_hidden", "")
        if not b_hidden:
            raise ValueError("Problem data missing B_hidden field")
        
        return b_hidden

    async def _llm_score(self, question: str, correct_answer: str, predicted_answer: str, problem: dict) -> float:
        """
        使用LLM进行二元判断：1.0 or 0.0
        """
        grading_prompt = f"""You are a grading assistant. Your task is to determine if the predicted answer is correct.

Question: {question}

Correct Answer: {correct_answer}

Predicted Answer: {predicted_answer}

Instructions:
1. Compare the predicted answer with the correct answer
2. Consider if they refer to the same entity/concept  
3. Account for different phrasings, translations, or alternative names
4. Give ONLY one of these two scores:
   - 1.0: The predicted answer is correct (same entity/concept)
   - 0.0: The predicted answer is incorrect or completely different

IMPORTANT: Respond with ONLY "1.0" or "0.0", nothing else."""

        try:
            response = await self.grader_llm(grading_prompt)
            
            # 提取分数
            score_text = response.strip()
            
            # 严格解析：只接受1.0或0.0
            if score_text == "1.0":
                print(f"🎓 LLM Grader: CORRECT (1.0)")
                return 1.0
            elif score_text == "0.0":
                print(f"🎓 LLM Grader: INCORRECT (0.0)")
                return 0.0
            else:
                # 尝试从响应中提取
                if "1.0" in response:
                    print(f"🎓 LLM Grader: CORRECT (1.0) - extracted from: {response}")
                    return 1.0
                elif "0.0" in response:
                    print(f"🎓 LLM Grader: INCORRECT (0.0) - extracted from: {response}")
                    return 0.0
                else:
                    # 不回退，直接报错
                    raise Exception(f"LLM grader returned invalid response: {response}")
                    
        except Exception as e:
            print(f"❌ LLM grading failed: {e}")
            raise Exception(f"LLM grading failed: {e}")  # 不回退，直接报错

    def _fallback_score(self, correct_answer: str, predicted_answer: str) -> float:
        """降级评分方法：简单字符串匹配"""
        if not correct_answer or not predicted_answer:
            return 0.0
        
        correct_lower = correct_answer.lower().strip()
        predicted_lower = predicted_answer.lower().strip()
        
        # 简单包含匹配
        if correct_lower in predicted_lower or predicted_lower in correct_lower:
            return 1.0
        
        # 词汇重叠
        correct_words = set(correct_lower.split())
        predicted_words = set(predicted_lower.split())
        
        intersection = correct_words.intersection(predicted_words)
        if len(intersection) > 0:
            overlap_ratio = len(intersection) / max(len(correct_words), len(predicted_words))
            return overlap_ratio if overlap_ratio > 0.3 else 0.0
        
        return 0.0

    def _generate_context_summary(self, context: List[dict]) -> str:
        """生成上下文摘要"""
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
        
        return " → ".join(summary_parts)

    def calculate_score(self, expected_output: Any, prediction: Any) -> Tuple[float, Any]:
        """实现基类抽象方法（同步版本，用于兼容性）"""
        # 这里只能做简单匹配，因为是同步方法
        if isinstance(expected_output, str) and isinstance(prediction, str):
            score = self._fallback_score(expected_output, prediction)
            return score, prediction
        return 0.0, prediction

    def get_result_columns(self) -> List[str]:
        """定义结果CSV列名"""
        return ["question", "correct_answer", "predicted_answer", "context_summary", "score", "cost"]