from typing import Tuple, List, Callable, Dict, Any
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed
import pandas as pd
import os
from datetime import datetime

from benchmarks.benchmark import BaseBenchmark
from utils.logs import logger
from utils.async_llm import create_llm_instance

class RemindBenchmark(BaseBenchmark):
    def __init__(self, name: str, file_path: str, log_path: str, grader_config=None):
        super().__init__(name, file_path, log_path)
        self.grader_llm = create_llm_instance(grader_config) if grader_config else None

    def _extract_final_answer(self, response: str) -> str:
        if 'FINAL_ANSWER:' in response:
            return response.split('FINAL_ANSWER:')[-1].strip()
        return response.strip()

    def _extract_selected_slots_from_response(self, response: str) -> List[str]:
        if 'SELECTED_SLOTS:' in response:
            slots_text = response.split('SELECTED_SLOTS:')[-1].strip()
            slots_text = slots_text.replace('[', '').replace(']', '').replace(',', ' ')
            return [slot.strip() for slot in slots_text.split() if slot.strip()]
        
        slot_ids = ['mobility_platform', 'weakpoint_anatomy', 'organization', 'tone_structure', 'settlement_layout', 'weapon_doctrine', 'supply_rhythm']
        return [slot_id for slot_id in slot_ids if slot_id.lower() in response.lower()][:2]

    async def parse_response(self, response: str, correct_answer: str, popular_answer: str = None) -> Tuple[float, str]:
        extracted_answer = self._extract_final_answer(response)
        
        if 'vague' in extracted_answer.lower():
            return 1.0, 'vague'
        
        if not self.grader_llm:
            return (1.0, 'correct') if correct_answer.lower() in extracted_answer.lower() else (0.0, 'incorrect_other')
        
        try:
            semantic_judge_prompt = f"""Are these two answers referring to the same thing?

Answer A: {correct_answer}
Answer B: {extracted_answer}

Instructions:
- Judge whether both answers refer to the same entity, concept, or thing
- Ignore differences in language (English/Japanese), formatting, or extra details
- Focus on the core meaning

Reply with only "YES" or "NO":"""
            logger.info(f"Grader LLM Prompt: {semantic_judge_prompt}")
            grader_response = await self.grader_llm(semantic_judge_prompt)
            logger.info(f"Grader LLM Response: {grader_response}")
            if 'YES' in grader_response.upper():
                return 1.0, 'correct'
            elif popular_answer and popular_answer.lower() in extracted_answer.lower():
                return 0.0, 'incorrect_popular'
            else:
                return 0.0, 'incorrect_other'
                
        except Exception as e:
            logger.error(f"Grader LLM failed: {str(e)}")
            return (1.0, 'correct') if correct_answer.lower() in extracted_answer.lower() else (0.0, 'incorrect_other')

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), retry=retry_if_exception_type(Exception), reraise=True)
    async def _generate_output(self, workflow, task: Dict[str, Any]) -> Tuple[List[Dict], float]:
        return await workflow(task)

    async def calculate_score(self, problem_data: Dict, conversation_history: List[Dict]) -> Tuple[float, Dict[str, Any]]:
        metrics = {
            'step1_vague_identification': 0.0, 
            'step2_slots_coverage': 0.0, 
            'step3_correct_answer': 0.0, 
            'early_correct': False
        }
        
        correct_answer = problem_data.get('B_hidden', '')
        popular_answer = problem_data.get('A_pop', '')
        info_slots = set(problem_data.get('info_slots', []))
        
        for step_data in conversation_history:
            step_num = step_data.get('step', 0)
            response = step_data.get('response', '')
            
            if step_num == 1:
                _, response_type = await self.parse_response(response, correct_answer, popular_answer)
                if response_type == 'vague':
                    metrics['step1_vague_identification'] = 1.0
                elif response_type == 'correct':
                    metrics['step3_correct_answer'] = 1.0
                    metrics['early_correct'] = True
            
            elif step_num == 2 and not metrics['early_correct']:
                selected_slots = set(self._extract_selected_slots_from_response(response))
                metrics['step2_slots_coverage'] = len(selected_slots & info_slots) / len(info_slots) if info_slots else 0.0
            
            elif step_num == 3:
                _, response_type = await self.parse_response(response, correct_answer, popular_answer)
                metrics['step3_correct_answer'] = 1.0 if response_type == 'correct' else 0.0
        
        overall_score = sum(metrics[k] for k in ['step1_vague_identification', 'step2_slots_coverage', 'step3_correct_answer']) / 3.0
        return overall_score, metrics

    async def evaluate_problem(self, problem: dict, workflow: Callable) -> Tuple[str, str, List[Dict], Dict[str, Any], float, float, float, float]:
        question = problem.get('q0', '')
        correct_answer = problem.get('B_hidden', '')
        
        try:
            conversation_history, cost = await self._generate_output(workflow, problem)
            overall_score, metrics = await self.calculate_score(problem, conversation_history)
            
            scores = (metrics['step1_vague_identification'], metrics['step2_slots_coverage'], metrics['step3_correct_answer'])
            
            if metrics.get('early_correct', False):
                self.log_mismatch(
                    problem=question, 
                    expected_output=correct_answer, 
                    prediction=conversation_history[0]['response'], 
                    extracted_output="Early correct", 
                    extract_answer_code="early_correct"
                )
            
            return question, correct_answer, conversation_history, metrics, *scores, cost
            
        except Exception as e:
            logger.error(f"Error evaluating problem: {str(e)}")
            return question, correct_answer, [{"error": str(e)}], {}, 0.0, 0.0, 0.0, 0.0

    def save_results_to_csv(self, results: List[Tuple[Any, ...]], columns: List[str]):
        df = pd.DataFrame([r[:len(columns)] for r in results], columns=columns)
        
        scores = {
            'vague_identification_score': df['vague_identification_score'].mean(),
            'slots_coverage_score': df['slots_coverage_score'].mean(),
            'correct_answer_score': df['correct_answer_score'].mean()
        }
        
        cost_info = (df["cost"].sum(), df["cost"].sum() / len(df))
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{scores['vague_identification_score']:.3f}_{scores['slots_coverage_score']:.3f}_{scores['correct_answer_score']:.3f}_{timestamp}.csv"
        
        os.makedirs(self.log_path, exist_ok=True)
        df.to_csv(os.path.join(self.log_path, filename), index=False)
        
        logger.info(f"Step 1 (Vague Identification): {scores['vague_identification_score']:.5f}")
        logger.info(f"Step 2 (Slots Coverage): {scores['slots_coverage_score']:.5f}")
        logger.info(f"Step 3 (Correct Answer): {scores['correct_answer_score']:.5f}")
        
        return scores['vague_identification_score'], cost_info[1], cost_info[0]

    async def run_baseline(self, agent: Callable, max_concurrent_tasks: int = 50):
        data = await self.load_data()
        results = await self.evaluate_all_problems(data, agent, max_concurrent_tasks)
        return self.save_results_to_csv(results, self.get_result_columns())

    def get_result_columns(self) -> List[str]:
        return ['question', 'correct_answer', 'conversation_history', 'metrics', 
                'vague_identification_score', 'slots_coverage_score', 'correct_answer_score', 'cost']