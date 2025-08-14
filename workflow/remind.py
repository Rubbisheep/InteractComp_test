"""
@File    :   workflow/remind.py
@Time    :   2025/08/11
@Author  :   Deng Mingyi
"""

import re
from typing import List, Tuple, Set

from workflow.base import Workflow
from utils.formatter import XmlFormatter
from workflow.search_engine import create_search_engine
from workflow.human_agent import HumanAgent
from workflow.prompt import BASE_PROMPT, PRINCIPLES_PROMPT, HARD_MODE_PROMPT, EASY_MODE_PROMPT, FORCE_PROMPT
from utils.logs import logger

class RemindWorkflow(Workflow):

    def __init__(
        self,
        name: str,
        llm_config,
        dataset: str,
        prompt: str,
        mode: str,
        max_turns: int = 5,
        search_engine_type: str = "llm_knowledge",
        interactive: bool = False,
    ):
        super().__init__(name, llm_config, dataset)
        self.mode = mode
        self.max_turns = max_turns
        self.base_prompt = BASE_PROMPT
        self.interactive = interactive
        self.llm_config = llm_config

        self.search_engine = create_search_engine(search_engine_type, llm_config=llm_config)
        self.human_agent = HumanAgent(mode=mode, interactive=interactive)

        self.formatter = XmlFormatter.from_dict(
            {
                "thought": "Your reasoning about the current situation",
                "action": "ask:question OR search:query OR answer:final_answer",
            }
        )

        logger.info(
            f"RemindWorkflow initialized: mode={mode}, max_turns={max_turns}, search={search_engine_type}"
        )

    async def __call__(self, problem_data: dict) -> Tuple[str, List[dict], float]:

        question = problem_data["q0"]
        context: List[dict] = []
        total_cost = 0.0
        self.human_agent.reset()
        self.make_banner(question, problem_data)

        for turn in range(self.max_turns):
            print(f"\n--- TURN {turn + 1}/{self.max_turns} ---")

            prompt = self._build_prompt(question, context, turn, problem_data)

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
                context.append(self.answer(action, turn_record))
                logger.info(f"✅ Final Answer: {turn_record['final_answer']}")
                return turn_record['final_answer'], context, total_cost

            elif action_type == "ask":
                context.append(await self.ask(action, turn_record, problem_data))

            elif action_type == "search":
                turn_record = await self.search(action, turn_record)
                context.append(turn_record)

            else:
                logger.warning(f"Invalid action: {action}")
                turn_record["error"] = f"Invalid action: {action}"
                turn_record["action_type"] = "invalid"
                logger.error(f"❌ Invalid Action: {action}")
                context.append(turn_record)

        print(f"\n--- TURN {self.max_turns + 1} (FORCED) ---")
        logger.info("⏰ Max turns reached, forcing final answer...")

        final_answer, final_cost = await self._force_answer(question, context)
        total_cost += final_cost

        logger.info(f"🔚 Forced Final Answer: {final_answer}")

        context.append(
            {
                "turn": self.max_turns + 1,
                "final_answer": final_answer,
                "forced": True,
                "cost": final_cost,
                "action_type": "answer",
            }
        )

        return final_answer, context, total_cost

    def make_banner(self, question, problem_data):
        print("\n" + "=" * 80)
        print("SEARCH AGENT STARTED")
        print("=" * 80)
        print(f"Question: {question}")
        print(f"Mode: {self.mode} | Max Turns: {self.max_turns}")
        print(f"Domain: {problem_data.get('domain', 'Unknown')}")
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
    
    async def ask(self, action, turn_record, problem_data):
        question_asked = action.strip()
        turn_record["question_asked"] = question_asked

        try:
            response = await self.human_agent.respond_to_question(question_asked, problem_data)
            turn_record["human_response"] = response
            turn_record["response_length"] = len(response)
            logger.info(f"👤 Human Response: {response}")
        except Exception as e:
            turn_record["human_response"] = "Error in response"
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
                title = result.get("title", "No title")[:80]
                snippet = result.get("snippet", "No snippet")[:120]
                print(f"{i}. {title}")
                print(f"{snippet}...")
            print(f"Search completed: {len(search_results)} results")
            return turn_record
        
        except Exception as e:
            logger.error(f"Search error: {e}")
            turn_record["search_results"] = []
            turn_record["search_results_count"] = 0
            turn_record["error"] = str(e)
            print(f"❌ Search Error: {e}")
            return turn_record

    def _get_available_slots(self, problem_data: dict) -> List[str]:
        allowed = problem_data.get("allowed_slots")
        if isinstance(allowed, list) and all(isinstance(x, str) for x in allowed):
            return allowed
        return []

    def _compute_used_slots(self, context: List[dict], available_slots: List[str]) -> Set[str]:
        used: Set[str] = set()
        for rec in context:
            if rec.get("action_type") == "ask":
                q = rec.get("question_asked", "")
                s = self._detect_question_slot(q, available_slots)
                used.add(s) if s else None
        return used
    
    @staticmethod
    def _detect_question_slot(question_asked: str, available_slots: List[str]) -> str:
        q = (question_asked or "").strip().lower()
        if not q or not available_slots:
            return ""
        for s in available_slots:
            if s.lower() in q:
                return s
        return ""

    def _build_prompt(self, question: str, context: List[dict], turn: int, problem_data: dict) -> str:
        prompt_parts = [
            self.base_prompt,
            f"\nOriginal Question: {question}",
            f"\nMode: {self.mode}",
            f"\nTurn: {turn + 1}/{self.max_turns}",
            PRINCIPLES_PROMPT,
        ]

        if self.mode == "HARD":
            prompt_parts.extend(
                [HARD_MODE_PROMPT,
                 f"\nConversation History: {context}"]
            )

        if self.mode == "EASY":
            prompt_parts.extend(
                [EASY_MODE_PROMPT,
                 f"\nConversation History: {context}"]
            )

            available_slots = self._get_available_slots(problem_data)
            used_slots = self._compute_used_slots(context, available_slots)
            unused = [s for s in available_slots if s not in used_slots]
            
            prompt_parts.append(
                f"\nUnused categories (may provide additional distinguishing details): {', '.join(unused)}"
            ) if unused else None

        return "\n".join(prompt_parts)

    async def _get_agent_decision(self, prompt: str) -> Tuple[str, str, float]:
        try:
            response = await self.llm.call_with_format(prompt, self.formatter)
            cost = self.llm.get_usage_summary()["total_cost"]
            thought = response.get("thought", "No thought")
            action = response.get("action", "answer:No action")
            return thought, action, cost
        except Exception as e:
            logger.warning(f"LLM generation failed: {e}")
            return "no thought","no action", 0.0

    async def _force_answer(self, question: str, context: List[dict]) -> Tuple[str, float]:

        force_prompt = FORCE_PROMPT.format(question=question, evidence_text=f"{context}")

        try:
            thought, action, cost = await self._get_agent_decision(force_prompt)
            logger.info(f"💭 Final Evidence-Based Thought: {thought}")

            if action.startswith("answer:"):
                return action[7:].strip(), cost
            return "No final answer provided", cost
        except Exception as e:
            logger.error(f"Force answer failed: {e}")
            return "Error generating final answer", 0.0