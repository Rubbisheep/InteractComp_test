"""
@File    :   workflow/remind.py
@Time    :   2025/08/11
@Author  :   Deng Mingyi
"""

import re
from typing import List, Tuple, Set

from workflow.base import Workflow
from utils.async_llm import AsyncLLM
from utils.formatter import XmlFormatter
from workflow.search_engine import create_search_engine
# from workflow.human_agent import HumanAgent
from workflow.user_agent import UserAgent
from workflow.prompt import BASE_PROMPT, FORCE_PROMPT
from utils.logs import logger

class RemindWorkflow(Workflow):

    def __init__(
        self,
        name: str,
        llm_config,
        dataset: str,
        prompt: str,
        max_turns: int = 5,
        search_engine_type: str = "llm_knowledge",
        user_config: str = "gpt-4o"
    ):
        super().__init__(name, llm_config, dataset)
        self.max_turns = max_turns
        self.base_prompt = BASE_PROMPT

        self.search_engine = create_search_engine(search_engine_type, llm_config=llm_config)
        self.user_agent = UserAgent(llm_config=user_config)

        logger.info(
            f"RemindWorkflow initialized: max_turns={max_turns}, search={search_engine_type}"
        )

    async def __call__(self, problem_data: dict) -> Tuple[str, List[dict], float]:

        question = problem_data["question"]
        history: List[dict] = []
        total_cost = 0.0
        self.user_agent.reset(problem_data["context"])
        self.make_banner(question, problem_data)

        for turn in range(self.max_turns):
            print(f"\n--- TURN {turn + 1}/{self.max_turns} ---")

            prompt = self._build_prompt(question, history, turn)

            thought, action, cost = await self._get_agent_decision(prompt)
            total_cost += cost

            logger.info(f"💭 Agent Thought: {thought}")
            logger.info(f"🎯 Agent Action: {action}")

            action_type = self._get_action_type(action)
            turn_record = {
                "turn": turn + 1,
                "thought": thought,
                "action": action,
                "action_type": action_type,
                "cost": cost,
            }

            if action_type == "answer":
                history.append(self.answer(action, turn_record))
                logger.info(f"✅ Final Answer: {turn_record['final_answer']}")
                return turn_record['final_answer'], history, total_cost

            elif action_type == "ask":
                history.append(await self.ask(action, turn_record))

            elif action_type == "search":
                history.append(await self.search(action, turn_record))

            else:
                logger.error(f"Invalid action: {action}")
                turn_record["error"] = f"Invalid action: {action}"
                turn_record["action_type"] = "invalid"
                logger.error(f"❌ Invalid Action: {action}")
                history.append(turn_record)

        print(f"\n--- TURN {self.max_turns + 1} (FORCED) ---")
        logger.info("⏰ Max turns reached, forcing final answer...")

        final_answer, final_cost = await self._force_answer(question, history)
        total_cost += final_cost

        logger.info(f"🔚 Forced Final Answer: {final_answer}")

        history.append(
            {
                "turn": self.max_turns + 1,
                "final_answer": final_answer,
                "forced": True,
                "cost": final_cost,
                "action_type": "answer",
            }
        )

        return final_answer, history, total_cost

    def make_banner(self, question, problem_data):
        print("\n" + "=" * 80)
        print("SEARCH AGENT STARTED")
        print("=" * 80)
        print(f"Question: {question}")
        print(f"Domain: {problem_data.get('domain', 'Unknown')}| Max Turns: {self.max_turns}")
        print(f"Search Engine: {type(self.search_engine).__name__}")
        print("=" * 80)

    def _get_action_type(self, action: str) -> str:
        if action.startswith("ask:"):
            return "ask"
        if action.startswith("search:"):
            return "search"
        if action.startswith("answer:"):
            return "answer"
        return "invalid"

    def answer(self, action, turn_record):
        final_answer = action.strip()
        turn_record["final_answer"] = final_answer
        return turn_record
    
    async def ask(self, action, turn_record):
        question_asked = action.strip()
        turn_record["question_asked"] = question_asked

        try:
            response = await self.user_agent.answer(question_asked)
            turn_record["response"] = response
            logger.info(f"👤 Human Response: {response}")
        except Exception as e:
            turn_record["response"] = "Error in response"
            turn_record["error"] = str(e)
            logger.error(f"❌ Human Response Error: {e}")
        return turn_record

    async def search(self, action, turn_record):
        search_query = action[7:].strip()
        turn_record["search_query"] = search_query

        logger.info(f"🔍 Searching: {search_query}")
        logger.info(f"Using: {type(self.search_engine).__name__}")

        try:
            search_results = await self.search_engine.search(search_query)
            turn_record["search_results"] = search_results
            turn_record["search_results_count"] = len(search_results)

            logger.info(f"📄 Search Results ({len(search_results)} found):")
            for i, result in enumerate(search_results[:3], 1):
                title = result.get("title", "No title")
                snippet = result.get("snippet", "No snippet")
                print(f"{i}. {title}")
                print(f"{snippet}")
            print(f"Search completed: {len(search_results)} results")
            return turn_record
        
        except Exception as e:
            logger.error(f"Search error: {e}")
            turn_record["search_results"] = []
            turn_record["search_results_count"] = 0
            turn_record["error"] = str(e)
            print(f"❌ Search Error: {e}")
            return turn_record

    def _build_prompt(self, question: str, history: List[dict], turn: int) -> str:
        prompt = "\n".join([
            f"\nTurn: {turn + 1}/{self.max_turns}",
            self.base_prompt,
            f"\nInformation you have gathered:"
            f"\nQuestion: {question}",
            f"\nConversation History: {history}",
        ])
        return prompt

    async def _get_agent_decision(self, prompt: str) -> Tuple[str, str, float]:
        try:
            response = await self.llm(prompt)
            response = self.parse_response(response)
            cost = self.llm.get_usage_summary()["total_cost"]
            thought = response.get("thought", "No thought")
            action = response.get("action", "answer:No action")
            return thought, action, cost
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return "no thought","no action", 0.0

    async def _force_answer(self, question: str, history: List[dict]) -> Tuple[str, float]:

        force_prompt = FORCE_PROMPT.format(question=question, evidence_text=f"{history}")

        try:
            thought, action, cost = await self._get_agent_decision(force_prompt)
            logger.info(f"💭 Final Evidence-Based Thought: {thought}")

            if action.startswith("answer:"):
                return action[7:].strip(), cost
            return "No final answer provided", cost
        except Exception as e:
            logger.error(f"Force answer failed: {e}")
            return "Error generating final answer", 0.0

    def parse_response(self, response: str) -> dict:
        if response is None:
            return {"thought": "no_response", "action": "no_response"}
        # logger.info(f"LLM Response: {response}")

        text = str(response).strip()
        fence = re.search(r"```(?:\w+)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        if fence:
            text = fence.group(1).strip()

        thought_m = re.search(r"<\s*thought\s*>(.*?)</\s*thought\s*>", text, flags=re.IGNORECASE | re.DOTALL)
        action_m = re.search(r"<\s*action\s*>(.*?)</\s*action\s*>", text, flags=re.IGNORECASE | re.DOTALL)

        if not thought_m or not action_m:
            return {"thought": "can not find formatted thought, i need to use <thought></thought>", "action": "can not find formatted action, i need to use <action></action>"}

        thought = thought_m.group(1).strip()
        action = action_m.group(1).strip()

        return {"thought": thought, "action": action}