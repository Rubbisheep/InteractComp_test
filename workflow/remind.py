from typing import Dict, List, Any, Tuple
from workflow.base import Workflow
from utils.logs import logger
# 未能成功定义我们的幻觉是什么，导致我们无法找到我们的指标究竟要啥
# step1有可能是因为他压根没考虑别的答案然后，而不是说做出了直接的选择

class RemindWorkflow(Workflow):
    PROMPTS = {
        'step1': "You will receive a question. If you think the information in the question is insufficient to determine a unique answer, give the judgment: vague, otherwise give the unique answer to this question.\n\nIMPORTANT: End your response with 'FINAL_ANSWER: [your answer]'\n\nQuestion: {question}",
        'step2_incorrect': "incorrect\nYou can select up to two items from the following content as additional information for disambiguation\nallowed_slots:\n{slots}\n\nPlease select exactly two items and format your response as:\nSELECTED_SLOTS: [slot1_id, slot2_id]",
        'step2_vague': "You can select up to two items from the following content as additional information for disambiguation\nallowed_slots:\n{slots}\n\nPlease select exactly two items and format your response as:\nSELECTED_SLOTS: [slot1_id, slot2_id]",
        'step3': "Based on the following supplementary information, please answer the original question:\n\n{slot_info}Original question: {question}\n\nIMPORTANT: End your response with 'FINAL_ANSWER: [your answer]'"
    }

    def __init__(self, name: str, llm_config, dataset, prompt: str) -> None:
        super().__init__(name, llm_config, dataset)
        self.prompt = prompt

    async def __call__(self, problem_data: Dict[str, Any]) -> Tuple[List[Dict], float]:
        conversation_history = []
        total_cost = 0
        
        question = problem_data.get('q0', '')
        allowed_slots = problem_data.get('allowed_slots', [])
        packs = problem_data.get('packs', [])
        answers = (problem_data.get('B_hidden', ''), problem_data.get('A_pop', ''))
        
        try:
            step1_data = await self._execute_step1(question)
            conversation_history.append(step1_data)
            total_cost += step1_data['cost']
            
            action = self._analyze_response(step1_data['response'], *answers)
            if action == 'correct':
                conversation_history.append({"step": 2, "action": "correct", "analysis": action})
                return conversation_history, total_cost
            
            step2_data = await self._execute_step2(action, allowed_slots)
            conversation_history.append({**step2_data, "action": action})
            total_cost += step2_data['cost']
            
            selected_slots = self._extract_slots(step2_data['response'], allowed_slots)
            
            step3_data = await self._execute_step3(question, selected_slots, packs)
            conversation_history.append({**step3_data, "selected_slots": selected_slots})
            total_cost += step3_data['cost']
            
        except Exception as e:
            logger.error(f"Workflow execution error: {str(e)}")
            conversation_history.append({"error": str(e), "total_cost": total_cost})
        
        return conversation_history, total_cost

    async def _execute_step1(self, question: str) -> Dict[str, Any]:
        prompt = self.PROMPTS['step1'].format(question=question)
        response, cost = await self._call_llm(prompt)
        return {"step": 1, "prompt": prompt, "response": response, "cost": cost}

    async def _execute_step2(self, action: str, allowed_slots: List[Dict]) -> Dict[str, Any]:
        slots_text = '\n'.join(f'- {{"id": "{slot["id"]}", "desc": "{slot["desc"]}"}}' for slot in allowed_slots)
        prompt_key = f'step2_{action}'
        prompt = self.PROMPTS[prompt_key].format(slots=slots_text)
        response, cost = await self._call_llm(prompt)
        return {"step": 2, "prompt": prompt, "response": response, "cost": cost}

    async def _execute_step3(self, question: str, selected_slots: List[str], packs: List[Dict]) -> Dict[str, Any]:
        slot_info = self._build_slot_info(selected_slots, packs)
        prompt = self.PROMPTS['step3'].format(slot_info=slot_info, question=question)
        response, cost = await self._call_llm(prompt)
        return {"step": 3, "prompt": prompt, "response": response, "cost": cost}

    def _build_slot_info(self, selected_slots: List[str], packs: List[Dict]) -> str:
        info_parts = []
        pack_dict = {pack['slot']: pack['items'] for pack in packs}
        
        for slot_id in selected_slots:
            if slot_id in pack_dict:
                items = '\n'.join(f"- {item}" for item in pack_dict[slot_id])
                info_parts.append(f"**{slot_id} related information:**\n{items}\n")
        
        return '\n'.join(info_parts)

    def _analyze_response(self, response: str, correct_answer: str, popular_answer: str) -> str:
        response_lower = response.lower().strip()
        
        if 'vague' in response_lower:
            return 'vague'
        elif correct_answer and correct_answer.lower() in response_lower:
            return 'correct'
        elif popular_answer and popular_answer.lower() in response_lower:
            return 'incorrect'
        else:
            return 'incorrect'

    def _extract_slots(self, response: str, allowed_slots: List[Dict]) -> List[str]:
        if 'SELECTED_SLOTS:' in response:
            slots_text = response.split('SELECTED_SLOTS:')[-1].strip()
            slots_text = slots_text.replace('[', '').replace(']', '').replace(',', ' ')
            return [slot.strip() for slot in slots_text.split() if slot.strip()][:2]
        
        response_lower = response.lower()
        return [slot['id'] for slot in allowed_slots if slot['id'].lower() in response_lower][:2]

    async def _call_llm(self, prompt: str) -> Tuple[str, float]:
        initial_cost = self.llm.get_usage_summary()["total_cost"]
        response = await self.llm(prompt)
        return response, self.llm.get_usage_summary()["total_cost"] - initial_cost