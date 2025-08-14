#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   workflow/human_agent.py  
@Time    :   2025/08/11
@Author  :   Deng Mingyi
"""

from typing import Dict, List, Any
from utils.logs import logger
from utils.async_llm import create_llm_instance


class HumanAgent:
    
    def __init__(self, mode: str, interactive: bool = False):
        self.mode = mode
        self.interactive = interactive
        self.interaction_history = []
        self.easy_mode_state = "waiting_for_request"
        self.available_slots_provided = False 
        
        logger.info(f"HumanAgent initialized: mode={mode}, interactive={interactive}")
    
    async def respond_to_question(self, question: str, problem_data: dict) -> str:
        self.interaction_history.append({
            "question": question,
            "mode": self.mode,
            "state": self.easy_mode_state if self.mode == "EASY" else "N/A"
        })
        if self.interactive:
            response = self._human_interactive_response(question, problem_data)
        else:
            if self.mode == "HARD":
                response = await self._auto_hard_response(question, problem_data)
            if self.mode == "EASY":
                response = self._auto_easy_response(question, problem_data)
        
        self.interaction_history[-1]["response"] = response
        
        return response
    
    async def _auto_hard_response(self, question: str, problem_data: dict) -> str:
        question_lower = question.lower().strip()
        logger.info(f"🔍 Analyzing HARD mode question...")
        
        packs = problem_data.get("packs", [])
        all_items = HumanAgent.get_all_items(packs)

        res = await self._llm_judge(question_lower, all_items_info="\n".join([f"{item['slot']}: {item['content']}" for item in all_items]))
        return res 
    
    def _auto_easy_response(self, question: str, problem_data: dict) -> str:
        try:
            question_lower = (question or "").lower().strip()
            selected_slot = self._get_slots(question_lower, problem_data)

            if not self.available_slots_provided:
                allowed_slots = problem_data.get("allowed_slots", [])
                if allowed_slots:
                    self.available_slots_provided = True
                    self.easy_mode_state = "waiting_for_slot_choice"
                    formatted_slots = HumanAgent.get_formatted_slots(allowed_slots)
                    return (
                        f"Available information categories: {formatted_slots}. "
                        "Please choose a specific category name (e.g., mobility_platform)."
                    )
                return "No information categories available."

            if selected_slot and self.available_slots_provided:
                packs = problem_data.get("packs", [])
                for pack in packs:
                    if pack.get("slot") == selected_slot:
                        items = pack.get("items", [])
                        return " | ".join(items) if items else f"No detailed information available for {selected_slot}."
                return f"No detailed information available for {selected_slot}."

            raise ValueError("Unhandled EASY flow")
        except Exception:
            if self.available_slots_provided:
                return "I already provided the available categories. Please choose a specific category name"
            return "Please ask about available information categories first."
    
    def _human_interactive_response(self, question: str, problem_data: dict) -> str:
        print("\n" + "="*60)
        print("HUMAN INTERACTION MODE")
        print("="*60)
        print(f"Question from Search Agent: {question}\n")
        print("Available Information from Dataset:")
        print(f"Original Question: {problem_data.get('q0', 'N/A')}")
        
        allowed_items = problem_data.get("allowed_slots", [])
        info_items = problem_data.get('info_items', [])

        print("Information Available:")
        for i, item in enumerate(allowed_items, 1):
            print(f"  {i}. {item}")

        print("Key Information Available:")
        for i, item in enumerate(info_items, 1):
            print(f"  {i}. {item}")
        
        if self.mode == "HARD":
            print("Please respond with: yes, no, or 'idk'")
            while True:
                response = input("Your response: ").strip()
                if response.lower() in ['yes', 'no'] or response.lower() == "idk":
                    return response if response.lower() != "idk" else "idk"
                print("Please enter 'yes', 'no', or 'idk'")
        else: 
            if not self.available_slots_provided:
                print("Agent is asking for information slots. Provide available slots.")
                response = input("Available slots (comma-separated): ").strip()
                self.available_slots_provided = True
                return response
            else:
                print("Agent is asking for specific slot information.")
                response = input("Your detailed response: ").strip()
                return response
    
    @staticmethod
    def get_all_items(packs) -> List[Dict[str, str]]:
        all_items = []
        
        for pack in packs:
            slot_id = pack.get("slot", "")
            items = pack.get("items", [])
            for item in items:
                all_items.append({
                    "slot": slot_id,
                    "content": item
                })
        return all_items

    @staticmethod
    def get_formatted_slots(slots) -> str:
        slots_info = []
        for slot in slots:
            slot_id = slot.get("id", "")
            slot_desc = slot.get("desc", "")
            slots_info.append(f"{slot_id}: {slot_desc}")
        
        formatted_slots = "; ".join(slots_info)
        return formatted_slots

    def _get_slots(self, question: str, problem_data: dict) -> str:
        allowed_slots = problem_data.get("allowed_slots", [])
        for slot_info in allowed_slots:
            slot_id = slot_info["id"]
            if slot_id.lower() in question:
                return slot_id
        return ""

    async def _llm_judge(self, question: str, all_items_info: str) -> str:
    
        system_prompt = """You are a knowledge assistant. Based on the provided information, answer the user's question with exactly one of these responses: "yes", "no", or "idk".

    Rules:
    - Answer "yes" only if the information clearly supports the question
    - Answer "no" only if the information clearly contradicts the question  
    - Answer "idk" if the information is insufficient or unclear"""

        user_prompt = f"""Available information:
    {all_items_info}

    Question: {question}

    Answer with exactly one word: yes, no, idk"""

        try:
            llm = create_llm_instance("gpt-4o")
            llm.sys_msg = system_prompt
            response = await llm(user_prompt)
            
            clean_response = response.strip().lower()
            if clean_response in ['yes', 'no', "idk"]:
                return clean_response
                
        except Exception as e:
            logger.error(f"LLM judge fail: {e}")
            return "idk"
    
    def reset(self):
        self.interaction_history = []
        self.easy_mode_state = "waiting_for_request"
        self.available_slots_provided = False