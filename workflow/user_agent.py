import re
from typing import List, Tuple, Optional
from utils.async_llm import AsyncLLM
from utils.logs import logger

class UserAgent:
    def __init__(self, llm_config: str = "gpt-4o"):
        self.context = ""
        self.llm = AsyncLLM(llm_config)
        self.history = []

    def reset(self, context: str):
        self.history = []
        self.context = context
        logger.info(f"UserAgent reset")

    async def answer(self, question: str) -> str:
        q = (question or "").strip()
        if not q or not self.context:
            return "idk"
        
        prompt = self._build_prompt(question)
        
        try:
            response = await self.llm(prompt)
            
            answer = self._parse_response(response)
            
            self.history.append({
                "question": question,
                "answer": answer,
                "raw_response": response
            })
            
            return answer
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "idk"

    def _build_prompt(self, question: str) -> str:
        prompt = f"""You are a specialized Q&A agent. Please carefully read the complete CONTEXT content below, then answer the question based solely on the information contained within it.

CONTEXT:
{self.context}

IMPORTANT RULES:
1. You can only answer with one of three responses: Yes / No / idk
2. You must strictly base your judgment on the exact information in the above CONTEXT
3. If the CONTEXT does not clearly mention relevant information, you must answer "idk"
4. Carefully read the entire CONTEXT and consider all information before giving your answer
5. Do not speculate or add information that is not in the CONTEXT
6. Only output the answer itself, do not provide explanations

Question: {question}

Answer:"""
        return prompt

    def _parse_response(self, response: str) -> str:
        response = response.strip().lower()
        
        if "yes" in response:
            return "Yes"
        elif "no" in response:
            return "No"
        elif "idk" in response:
            return "idk"
        return "idk"

    def get_history(self) -> List[dict]:
        return self.history.copy()

    def clear_history(self):
        self.history = []
        logger.info("HumanAgent history cleared")