#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   benchmarks/InteractComp.py
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

class InteractCompBenchmark(BaseBenchmark):
    
    def __init__(self, name: str, file_path: str, log_path: str, grader_config: str = "gpt-4o", models: List[str] = None):
        super().__init__(name, file_path, log_path)
        self.grader_llm = AsyncLLM(grader_config)
        
        # 如果指定了多个模型，则使用多模型评估模式
        if models and len(models) > 1:
            self.evaluation_models = models
            self.multi_model_mode = True
            logger.info(f"Multi-model evaluation mode: {models}")
        else:
            # 兼容原有单模型模式
            self.evaluation_models = None
            self.multi_model_mode = False
            logger.info("Single model evaluation mode")

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), retry=retry_if_exception_type(Exception), reraise=True)
    async def _generate_output(self, agent, task: dict):
        return await agent(task)

    async def evaluate_problem(self, problem: dict, agent_or_agent_factory: Callable) -> Tuple[Any, ...]:
        
        question = problem["question"]
        correct_answer = problem.get("answer", "")
        
        logger.info(f"\n🎯 EVALUATING: {question}")
        
        try:
            if self.multi_model_mode:
                # 多模型评估模式
                return await self._evaluate_multi_model(problem, agent_or_agent_factory)
            else:
                # 原有单模型评估模式（保持向后兼容）
                return await self._evaluate_single_model(problem, agent_or_agent_factory)
                
        except Exception as e:
            logger.error(f"Error evaluating problem: {e}")
            print(f"❌ Evaluation Error: {e}")
            
            if self.multi_model_mode:
                return question, correct_answer, {}, 0, 0.0, 0.0
            else:
                return question, correct_answer, "Error", "Error", 0.0, 0.0

    async def _evaluate_single_model(self, problem: dict, agent: Callable) -> Tuple[str, str, str, str, float, float]:
        """原有单模型评估逻辑"""
        question = problem["question"]
        correct_answer = problem.get("answer", "")
        
        predicted_answer, history, cost = await self._generate_output(agent, problem)
        score = await self.calculate_score(question, correct_answer, predicted_answer)
        history_summary = self._generate_history_summary(history)

        return question, correct_answer, predicted_answer, history_summary, score, cost

    async def _evaluate_multi_model(self, problem: dict, agent_factory: Callable) -> Tuple[str, str, dict, int, float, float]:
        """新的多模型评估逻辑"""
        question = problem["question"]
        correct_answer = problem.get("answer", "")
        
        model_results = {}
        total_cost = 0.0
        correct_models_count = 0
        
        # 对每个模型进行评估
        for model_name in self.evaluation_models:
            try:
                # 通过agent_factory创建特定模型的agent
                agent = agent_factory(model_name)
                
                # 获取模型预测
                predicted_answer, history, cost = await self._generate_output(agent, problem)
                total_cost += cost
                
                # 评估答案正确性
                is_correct = await self.calculate_score(question, correct_answer, predicted_answer)
                
                model_results[model_name] = {
                    "answer": predicted_answer,
                    "correct": bool(is_correct),
                    "cost": cost,
                    "history": self._generate_history_summary(history)
                }
                
                if is_correct:
                    correct_models_count += 1
                    
                logger.info(f"📊 Model {model_name}: {'✅ CORRECT' if is_correct else '❌ INCORRECT'}")
                print(f"🤖 {model_name}: {predicted_answer} ({'✅' if is_correct else '❌'})")
                    
            except Exception as e:
                logger.error(f"Model {model_name} evaluation failed: {e}")
                model_results[model_name] = {
                    "answer": "Evaluation failed",
                    "correct": False,
                    "cost": 0.0,
                    "error": str(e),
                    "history": "Error"
                }
        
        # 判断质量：2个以上模型答对就是质量不合格
        quality_failed = correct_models_count >= 2
        quality_score = 1.0 - (correct_models_count / len(self.evaluation_models))  # 质量分数
        
        logger.info(f"📈 Multi-model result: {correct_models_count}/{len(self.evaluation_models)} correct, Quality: {'FAILED' if quality_failed else 'PASSED'}")
        print(f"🎯 Quality Assessment: {correct_models_count}/{len(self.evaluation_models)} models correct → {'❌ Quality Failed' if quality_failed else '✅ Quality Passed'}")

        return question, correct_answer, model_results, correct_models_count, quality_score, total_cost

    async def calculate_score(self, question: str, correct_answer: str, predicted_answer: str) -> float:
        """评估单个答案的正确性"""
        grading_prompt = GRADING_PROMPT.format(
            question=question,
            predicted_answer=predicted_answer,
            correct_answer=correct_answer
        )

        try:
            response = await self.grader_llm(grading_prompt)
            
            if "yes" in response.strip().lower():
                return 1.0
            elif "no" in response.strip().lower():
                return 0.0
            else:
                return 0.0
                    
        except Exception as e:
            logger.error(f"LLM grading failed: {e}")
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
        """根据评估模式返回不同的列结构"""
        if self.multi_model_mode:
            # 多模型模式的列结构
            base_columns = ["question", "correct_answer", "model_results", "correct_models_count", "quality_score", "total_cost"]
            return base_columns
        else:
            # 原有单模型模式的列结构
            return ["question", "correct_answer", "predicted_answer", "history_summary", "score", "cost"]

    async def run_multi_model_evaluation(self, agent_factory: Callable, max_concurrent_tasks: int = 50):
        """专门用于多模型评估的运行方法"""
        if not self.multi_model_mode:
            raise ValueError("Multi-model evaluation requires models to be specified in constructor")
        
        data = await self.load_data()
        results = await self.evaluate_all_problems(data, agent_factory, max_concurrent_tasks)
        
        # 计算统计信息
        total_questions = len(results)
        total_cost = sum(result[5] for result in results)  # total_cost是第6列
        quality_failed_count = sum(1 for result in results if result[3] >= 2)  # correct_models_count >= 2
        avg_quality_failed_rate = quality_failed_count / total_questions if total_questions > 0 else 0
        avg_cost = total_cost / total_questions if total_questions > 0 else 0
        
        # 保存结果到CSV
        columns = self.get_result_columns()
        self.save_results_to_csv(results, columns)
        
        logger.info(f"Multi-model evaluation completed:")
        logger.info(f"  Total questions: {total_questions}")
        logger.info(f"  Quality failed rate: {avg_quality_failed_rate:.3f}")
        logger.info(f"  Total cost: ${total_cost:.4f}")
        logger.info(f"  Average cost: ${avg_cost:.4f}")
        
        return {
            "total_questions": total_questions,
            "quality_failed_count": quality_failed_count,
            "avg_quality_failed_rate": avg_quality_failed_rate,
            "total_cost": total_cost,
            "avg_cost": avg_cost,
            "detailed_results": [
                {
                    "question": result[0],
                    "correct_answer": result[1],
                    "model_results": result[2],
                    "correct_models_count": result[3],
                    "quality_failed": result[3] >= 2,
                    "quality_score": result[4],
                    "total_cost": result[5]
                }
                for result in results
            ]
        }