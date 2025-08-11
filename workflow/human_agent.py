#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   workflow/human_agent.py  
@Time    :   2025/08/11
@Author  :   Deng Mingyi
@Desc    :   Human Agent，支持HARD/EASY两种模式和人类交互
"""

from typing import Dict, List, Any
from utils.logs import logger


class HumanAgent:
    """Human Agent，模拟观察者回答问题"""
    
    def __init__(self, mode: str = "HARD", interactive: bool = False):
        """
        Args:
            mode: "HARD" 或 "EASY"
            interactive: 是否启用人类交互模式
        """
        self.mode = mode
        self.interactive = interactive
        self.interaction_history = []
        self.easy_mode_state = "waiting_for_request"  # EASY模式状态: waiting_for_request, waiting_for_slot_choice
        
        logger.info(f"HumanAgent initialized: mode={mode}, interactive={interactive}")
    
    def respond_to_question(self, question: str, problem_data: dict) -> str:
        """
        回答search agent的问题
        
        Args:
            question: agent提出的问题
            problem_data: 问题相关数据
            
        Returns:
            回答字符串
        """
        # 记录交互
        self.interaction_history.append({
            "question": question,
            "mode": self.mode,
            "state": self.easy_mode_state if self.mode == "EASY" else "N/A"
        })
        
        if self.interactive:
            # 人类交互模式
            response = self._human_interactive_response(question, problem_data)
        else:
            # 自动模拟模式
            if self.mode == "HARD":
                response = self._auto_hard_response(question, problem_data)
            else:  # EASY
                response = self._auto_easy_response(question, problem_data)
        
        # 记录回答
        self.interaction_history[-1]["response"] = response
        logger.info(f"Human response to '{question[:50]}...': {response}")
        
        return response
    
    def _human_interactive_response(self, question: str, problem_data: dict) -> str:
        """人类交互模式：让真人回答"""
        print("\n" + "="*60)
        print("HUMAN INTERACTION MODE")
        print("="*60)
        print(f"Question from Search Agent: {question}")
        print()
        
        # 显示数据集中的相关信息
        print("Available Information from Dataset:")
        print(f"Original Question: {problem_data.get('q0', 'N/A')}")
        
        # 显示info_items
        info_items = problem_data.get('info_items', [])
        if info_items:
            print("Key Information Available:")
            for i, item in enumerate(info_items, 1):
                print(f"  {i}. {item}")
        
        # 显示选项
        if 'A_pop' in problem_data:
            print(f"Option A: {problem_data['A_pop']}")
        if 'B_hidden' in problem_data:
            print(f"Option B (Correct): {problem_data['B_hidden']}")
        print()
        
        if self.mode == "HARD":
            print("Please respond with: yes, no, or 'I don't know'")
            while True:
                response = input("Your response: ").strip()
                if response.lower() in ['yes', 'no'] or response.lower() == "i don't know":
                    return response if response.lower() != "i don't know" else "I don't know"
                print("Please enter 'yes', 'no', or 'I don't know'")
        else:  # EASY模式
            if self.easy_mode_state == "waiting_for_request":
                print("Agent is asking for information slots. Provide available slots.")
                response = input("Available slots (comma-separated): ").strip()
                self.easy_mode_state = "waiting_for_slot_choice"
                return response
            else:  # waiting_for_slot_choice
                print("Agent is asking for specific slot information.")
                response = input("Your detailed response: ").strip()
                self.easy_mode_state = "waiting_for_request"  # 重置状态
                return response
    
    def _auto_hard_response(self, question: str, problem_data: dict) -> str:
        """
        HARD模式自动回答：基于所有packs内容回答yes/no/I don't know
        """
        question_lower = question.lower().strip()
        
        print(f"      🔍 Analyzing HARD mode question...")
        print(f"      📋 Checking against all packs content...")
        
        # 获取所有packs内容进行匹配
        packs = problem_data.get("packs", [])
        all_items = []
        
        # 收集所有pack中的items
        for pack in packs:
            slot_id = pack.get("slot", "")
            items = pack.get("items", [])
            for item in items:
                all_items.append({
                    "slot": slot_id,
                    "content": item
                })
        
        print(f"      📦 Total items to check: {len(all_items)}")
        
        # 检查问题是否与任何pack中的items匹配
        best_match_score = 0
        best_match_slot = None
        
        for item_info in all_items:
            similarity = self._calculate_text_similarity(question_lower, item_info["content"].lower())
            if similarity > best_match_score:
                best_match_score = similarity
                best_match_slot = item_info["slot"]
        
        # 使用阈值判断
        if best_match_score > 0.3:
            print(f"      ✅ Best match in slot '{best_match_slot}' (similarity: {best_match_score:.2f})")
            return "yes"
        elif best_match_score > 0.1:
            print(f"      🤔 Weak match in slot '{best_match_slot}' (similarity: {best_match_score:.2f})")
            return "I don't know"
        else:
            print(f"      ❓ No significant match found (best: {best_match_score:.2f})")
            return "I don't know"
    
    def _auto_easy_response(self, question: str, problem_data: dict) -> str:
        """
        EASY模式自动回答：两步交互流程
        """
        print(f"      🔍 EASY mode state: {self.easy_mode_state}")
        
        # 检查是否是请求信息类别的问题
        question_lower = question.lower().strip()
        is_requesting_categories = any(phrase in question_lower for phrase in [
            "what information", "information categories", "categories available", 
            "what categories", "available information", "what can you tell me"
        ])
        
        if self.easy_mode_state == "waiting_for_request" or is_requesting_categories:
            # 第一步：提供可选择的slots（包含id和描述）
            allowed_slots = problem_data.get("allowed_slots", [])
            if allowed_slots:
                print(f"      📋 Providing {len(allowed_slots)} slot options with descriptions")
                
                # 更新状态
                self.easy_mode_state = "waiting_for_slot_choice"
                
                # 格式化slots信息（id + desc）
                slots_info = []
                for slot in allowed_slots:
                    slot_id = slot.get("id", "")
                    slot_desc = slot.get("desc", "")
                    slots_info.append(f"{slot_id}: {slot_desc}")
                
                formatted_slots = "; ".join(slots_info)
                return f"Available information categories: {formatted_slots}. Please choose a specific category name (e.g., mobility_platform)."
            else:
                return "No information categories available."
        
        else:  # waiting_for_slot_choice
            # 第二步：根据选择的slot返回详细信息
            selected_slot = self._extract_slot_from_question(question_lower, problem_data)
            
            if selected_slot:
                print(f"      🎯 Selected slot: {selected_slot}")
                
                # 查找对应的pack信息
                packs = problem_data.get("packs", [])
                for pack in packs:
                    if pack.get("slot") == selected_slot:
                        items = pack.get("items", [])
                        if items:
                            # 重置状态
                            self.easy_mode_state = "waiting_for_request"
                            
                            # 返回完整的pack信息（所有items）
                            formatted_info = " | ".join(items)  # 用|分隔，便于区分不同items
                            print(f"      📄 Returning all {len(items)} items for slot '{selected_slot}'")
                            return formatted_info
                
                # 重置状态
                self.easy_mode_state = "waiting_for_request"
                return f"No detailed information available for {selected_slot}."
            else:
                print(f"      ❓ Could not extract slot from: {question}")
                # 重置状态  
                self.easy_mode_state = "waiting_for_request"
                return "Please specify a valid information category name (e.g., mobility_platform, weakpoint_anatomy)."
    
    def _extract_slot_from_question(self, question: str, problem_data: dict) -> str:
        """从问题中提取slot名称 - 改进版"""
        allowed_slots = problem_data.get("allowed_slots", [])
        
        # 方法1：直接匹配完整slot_id
        for slot_info in allowed_slots:
            slot_id = slot_info["id"]
            if slot_id.lower() in question:
                return slot_id
        
        # 方法2：匹配slot_id的主要词汇
        for slot_info in allowed_slots:
            slot_id = slot_info["id"]
            slot_words = slot_id.split('_')
            
            # 检查是否所有主要词汇都在问题中
            main_words = [word for word in slot_words if len(word) > 3]  # 只考虑长词
            if main_words and all(word.lower() in question for word in main_words):
                return slot_id
        
        # 方法3：匹配描述中的关键词
        for slot_info in allowed_slots:
            slot_id = slot_info["id"]
            slot_desc = slot_info.get("desc", "").lower()
            
            # 提取描述中的关键词
            desc_words = [word.strip('.,!?;:()[]{}"\'-') for word in slot_desc.split()]
            desc_words = [word for word in desc_words if len(word) > 4]  # 只考虑长词
            
            # 检查问题是否包含描述中的关键词
            matches = sum(1 for word in desc_words if word in question)
            if matches >= 2:  # 至少匹配2个关键词
                return slot_id
        
        # 方法4：部分匹配（降级策略）
        for slot_info in allowed_slots:
            slot_id = slot_info["id"]
            for part in slot_id.split('_'):
                if len(part) > 4 and part.lower() in question:
                    return slot_id
        
        return None
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        stop_words = {
            "is", "are", "the", "a", "an", "and", "or", "but", "in", "on", "at", 
            "to", "for", "of", "with", "by", "do", "does", "did", "will", "would",
            "can", "could", "should", "have", "has", "had", "was", "were", "be", "been",
            "this", "that", "these", "those", "what", "which", "who", "where", "when", 
            "why", "how", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them"
        }
        
        # 清理并提取关键词
        words1 = set(word.strip('.,!?;:()[]{}"\'-') for word in text1.split()) - stop_words
        words2 = set(word.strip('.,!?;:()[]{}"\'-') for word in text2.split()) - stop_words
        
        # 过滤短词和数字
        words1 = {word for word in words1 if len(word) > 2 and not word.isdigit()}
        words2 = {word for word in words2 if len(word) > 2 and not word.isdigit()}
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard相似度
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        jaccard_similarity = len(intersection) / len(union) if union else 0.0
        
        # 部分词匹配
        partial_matches = 0
        for word1 in words1:
            for word2 in words2:
                if len(word1) > 3 and len(word2) > 3:
                    if word1 in word2 or word2 in word1:
                        partial_matches += 1
                        break
        
        partial_score = partial_matches / max(len(words1), len(words2)) if words1 or words2 else 0.0
        final_score = max(jaccard_similarity, partial_score * 0.5)
        
        if final_score > 0.1:
            print(f"      🔍 Similarity: {final_score:.2f} (intersection: {intersection})")
        
        return final_score
    
    def get_interaction_summary(self) -> Dict[str, Any]:
        """获取交互总结"""
        return {
            "mode": self.mode,
            "interactive": self.interactive,
            "total_interactions": len(self.interaction_history),
            "history": self.interaction_history
        }
    
    def reset(self):
        """重置状态"""
        self.interaction_history = []
        self.easy_mode_state = "waiting_for_request"