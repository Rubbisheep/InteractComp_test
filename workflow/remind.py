#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   workflow/remind.py
@Time    :   2025/08/11
@Author  :   Deng Mingyi
@Desc    :   Search Agent核心实现：ask/search/answer决策循环
"""

import re
from typing import List, Dict, Tuple, Optional
from workflow.base import Workflow
from utils.formatter import XmlFormatter
from workflow.search_engine import create_search_engine
from workflow.human_agent import HumanAgent
from utils.logs import logger


class RemindWorkflow(Workflow):
    """
    Search Agent工作流
    
    核心逻辑：多轮决策循环
    每轮：分析当前状态 → 选择action → 执行action → 更新状态
    """
    
    def __init__(
        self,
        name: str,
        llm_config,
        dataset: str,
        prompt: str,
        mode: str = "HARD",
        max_turns: int = 5,
        search_engine_type: str = "mock",
        interactive: bool = False
    ):
        super().__init__(name, llm_config, dataset)
        self.mode = mode
        self.max_turns = max_turns
        self.base_prompt = prompt
        self.interactive = interactive
        
        # 初始化组件
        self.search_engine = create_search_engine(search_engine_type)
        self.human_agent = HumanAgent(mode=mode, interactive=interactive)
        
        # 初始化XML解析器
        self.formatter = XmlFormatter.from_dict({
            "thought": "Your reasoning about the current situation",
            "action": "ask:question OR search:query OR answer:final_answer"
        })
        
        logger.info(f"RemindWorkflow initialized: mode={mode}, max_turns={max_turns}, search={search_engine_type}")

    async def __call__(self, problem_data: dict) -> Tuple[str, List[dict], float]:
        """
        Search Agent主循环
        
        Args:
            problem_data: 问题数据字典
            
        Returns:
            (final_answer, context_history, total_cost)
        """
        question = problem_data["q0"]
        context = []
        total_cost = 0
        
        print("\n" + "="*80)
        print("SEARCH AGENT STARTED")
        print("="*80)
        print(f"Question: {question}")
        print(f"Mode: {self.mode} | Max Turns: {self.max_turns}")
        print(f"Domain: {problem_data.get('domain', 'Unknown')}")
        print("="*80)
        
        logger.info(f"Starting search for: {question[:100]}...")
        self.human_agent.reset()
        
        # 主决策循环
        for turn in range(self.max_turns):
            print(f"\n--- TURN {turn + 1}/{self.max_turns} ---")
            
            # 构建prompt
            prompt = self._build_prompt(question, context, turn)
            
            # 获取LLM响应
            thought, action, cost = await self._get_agent_decision(prompt)
            total_cost += cost
            
            # 显示Agent的思考和行动
            print(f"💭 Agent Thought: {thought}")
            print(f"🎯 Agent Action: {action}")
            
            # 创建轮次记录
            turn_record = {
                "turn": turn + 1,
                "thought": thought,
                "action": action,
                "cost": cost
            }
            
            # 执行action并显示observation
            if action.startswith("answer:"):
                # 最终回答 - 立即结束
                final_answer = action[7:].strip()
                turn_record["final_answer"] = final_answer
                context.append(turn_record)
                
                print(f"✅ Final Answer: {final_answer}")
                print("="*80)
                print("SEARCH AGENT COMPLETED")
                print("="*80)
                
                logger.info(f"Agent answered: {final_answer}")
                return final_answer, context, total_cost
                
            elif action.startswith("ask:"):
                # 询问human agent
                question_asked = action[4:].strip()
                turn_record["question_asked"] = question_asked
                
                print(f"❓ Asking Human: {question_asked}")
                print("   🤔 Human Agent analyzing...")
                
                try:
                    response = self.human_agent.respond_to_question(question_asked, problem_data)
                    turn_record["human_response"] = response
                    print(f"👤 Human Response: {response}")
                except Exception as e:
                    logger.error(f"Human agent error: {e}")
                    turn_record["human_response"] = "Error in response"
                    print(f"❌ Human Response Error: {e}")
                
                context.append(turn_record)
                
            elif action.startswith("search:"):
                # 执行搜索
                search_query = action[7:].strip()
                turn_record["search_query"] = search_query
                
                print(f"🔍 Searching: {search_query}")
                
                try:
                    search_results = await self.search_engine.search(search_query)
                    turn_record["search_results"] = search_results
                    
                    # 格式化搜索结果为文本
                    formatted_results = self._format_search_results(search_results)
                    turn_record["formatted_results"] = formatted_results
                    
                    print(f"📄 Search Results ({len(search_results)} found):")
                    for i, result in enumerate(search_results[:3], 1):
                        print(f"   {i}. {result.get('title', 'No title')}")
                        print(f"      {result.get('snippet', 'No snippet')[:100]}...")
                    
                    logger.info(f"Search completed: {len(search_results)} results")
                except Exception as e:
                    logger.error(f"Search error: {e}")
                    turn_record["search_results"] = []
                    turn_record["formatted_results"] = "Search failed"
                    print(f"❌ Search Error: {e}")
                
                context.append(turn_record)
                
            else:
                # 无效action
                logger.warning(f"Invalid action: {action}")
                turn_record["error"] = f"Invalid action: {action}"
                print(f"❌ Invalid Action: {action}")
                context.append(turn_record)
        
        # 达到最大轮次，强制回答
        print(f"\n--- TURN {self.max_turns + 1} (FORCED) ---")
        print("⏰ Max turns reached, forcing final answer...")
        
        final_answer, final_cost = await self._force_final_answer(question, context)
        total_cost += final_cost
        
        print(f"🔚 Forced Final Answer: {final_answer}")
        print("="*80)
        print("SEARCH AGENT COMPLETED (FORCED)")
        print("="*80)
        
        context.append({
            "turn": self.max_turns + 1,
            "final_answer": final_answer,
            "forced": True,
            "cost": final_cost
        })
        
        return final_answer, context, total_cost

    def _build_prompt(self, question: str, context: List[dict], turn: int) -> str:
        """构建每轮的prompt - 区分HARD和EASY模式"""
        prompt_parts = [
            self.base_prompt,
            f"\nOriginal Question: {question}",
            f"\nMode: {self.mode}",
            f"\nTurn: {turn + 1}/{self.max_turns}"
        ]
        
        # 添加模式特定指令
        if self.mode == "HARD":
            prompt_parts.append("""
HARD Mode Instructions:
- You can ask any specific question to get yes/no/"I don't know" responses
- Ask questions that help distinguish between similar options
- Example: ask:Does the series feature mobile transportation?
- Response will be: yes, no, or "I don't know"
            """)
        else:  # EASY Mode
            prompt_parts.append("""
EASY Mode Instructions:
- FIRST ASK: ask:What information categories are available?
- Human will provide all available categories with descriptions like:
  "mobility_platform: Is the primary mobility/transport platform...; weakpoint_anatomy: Is the target's vital spot..."
- THEN CHOOSE: ask:mobility_platform (choose the exact category name)
- You will receive detailed information about that category (multiple items separated by |)
- You can choose multiple different categories in subsequent turns
- Choose categories that might help distinguish between similar options
- Use search: to verify information from external sources

Example conversation:
You: ask:What information categories are available?
Human: Available information categories: mobility_platform: Is the primary mobility...; weakpoint_anatomy: Is the target's vital...
You: ask:mobility_platform
Human: Residents rely on armored mobile stronghold... | Movement windows trigger alarms... | Inside compartments are sealed...
You: ask:weakpoint_anatomy  
Human: The target's vital area is encased in dense shell... | Close-quarters combat emphasizes...
You: search:armored mobile train anime
Search: Results about Kabaneri of the Iron Fortress...
You: answer:Kabaneri of the Iron Fortress
            """)
        
        # 特殊处理：如果是EASY模式且没有历史，给出第一步提示
        if self.mode == "EASY" and not context:
            prompt_parts.append("""
IMPORTANT: Start by asking what information categories are available.
            """)
        
        # 添加对话历史
        if context:
            history_parts = []
            for item in context:
                if item.get("is_slot_provision"):
                    continue  # 跳过slot提供步骤的历史显示
                
                turn_info = f"\nTurn {item['turn']}:"
                
                if item.get("thought"):
                    turn_info += f"\n  Your thought: {item['thought'][:200]}{'...' if len(item['thought']) > 200 else ''}"
                
                action_type = item.get("action_type", "unknown")
                
                if action_type == "ask":
                    turn_info += f"\n  You asked: {item.get('question_asked', 'Unknown question')}"
                    if item.get("human_response"):
                        turn_info += f"\n  Response: {item['human_response'][:100]}{'...' if len(item.get('human_response', '')) > 100 else ''}"
                
                elif action_type == "search":
                    turn_info += f"\n  You searched: {item.get('search_query', 'Unknown query')}"
                    results_count = item.get("search_results_count", 0)
                    turn_info += f"\n  Found {results_count} results"
                    
                    if item.get("search_results"):
                        results_summary = []
                        for result in item["search_results"][:2]:
                            snippet = result.get("snippet", "")[:100]
                            results_summary.append(f"'{snippet}...'" if len(snippet) == 100 else f"'{snippet}'")
                        turn_info += f"\n  Key results: {'; '.join(results_summary)}"
                
                elif action_type == "answer":
                    turn_info += f"\n  You answered: {item.get('final_answer', 'Unknown answer')}"
                
                if item.get("error"):
                    turn_info += f"\n  Error: {item['error']}"
                
                history_parts.append(turn_info)
            
            if history_parts:
                prompt_parts.append("\nConversation History:" + "\n".join(history_parts))
        
        return "\n".join(prompt_parts)

    async def _get_agent_decision(self, prompt: str) -> Tuple[str, str, float]:
        """获取agent的决策"""
        try:
            # 尝试结构化解析
            response = await self.llm.call_with_format(prompt, self.formatter)
            cost = self.llm.get_usage_summary()["total_cost"]
            
            thought = response.get("thought", "No thought")
            action = response.get("action", "answer:No action")
            
            return thought, action, cost
            
        except Exception as e:
            logger.warning(f"Structured parsing failed: {e}, trying fallback")
            
            # 降级到文本解析
            response = await self.llm(prompt)
            cost = self.llm.get_usage_summary()["total_cost"]
            
            thought, action = self._parse_text_response(response)
            return thought, action, cost

    def _parse_text_response(self, response: str) -> Tuple[str, str]:
        """解析文本响应"""
        # 尝试提取XML标签
        thought_match = re.search(r'<thought>(.*?)</thought>', response, re.DOTALL)
        action_match = re.search(r'<action>(.*?)</action>', response, re.DOTALL)
        
        if thought_match and action_match:
            thought = thought_match.group(1).strip()
            action = action_match.group(1).strip()
        else:
            # 简单文本解析
            lines = response.strip().split('\n')
            thought = "Unable to parse thought"
            action = "answer:Unable to parse action"
            
            for line in lines:
                line = line.strip()
                if line.startswith(('ask:', 'search:', 'answer:')):
                    action = line
                    break
        
        return thought, action

    def _format_search_results(self, results: List[Dict]) -> str:
        """格式化搜索结果为文本"""
        if not results:
            return "No results found"
        
        formatted = []
        for i, result in enumerate(results[:3], 1):  # 只显示前3个
            title = result.get("title", "No title")
            snippet = result.get("snippet", "No description")
            formatted.append(f"{i}. {title}: {snippet}")
        
        return "; ".join(formatted)

    def _is_slot_provision_response(self, response: str) -> bool:
        """检测响应是否是slot提供 - 适配新格式"""
        response_lower = response.lower()
        return (
            "available information categories" in response_lower or
            "please choose" in response_lower or
            (":" in response and any(slot in response_lower for slot in [
                "mobility_platform", "weakpoint_anatomy", "organization", 
                "tone_structure", "settlement_layout", "weapon_doctrine", "supply_rhythm"
            ])) or
            ("platform:" in response_lower or "anatomy:" in response_lower)
        )

    async def _force_final_answer(self, question: str, context: List[dict]) -> Tuple[str, float]:
        """强制获取最终答案"""
        # 计算实际使用的轮次数
        actual_turns_used = len([item for item in context if not item.get("is_slot_provision", False)])
        
        force_prompt = self._build_prompt(question, context, actual_turns_used) + """

IMPORTANT: You must provide a final answer now. Based on all the information you've gathered, make your best decision.

<thought>Your final reasoning</thought>
<action>answer:your_final_answer</action>"""
        
        try:
            thought, action, cost = await self._get_agent_decision(force_prompt)
            print(f"💭 Final Thought: {thought}")
            if action.startswith("answer:"):
                return action[7:].strip(), cost
            else:
                return "No final answer provided", cost
        except Exception as e:
            logger.error(f"Force answer failed: {e}")
            return "Error generating final answer", 0