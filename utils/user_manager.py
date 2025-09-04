#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户管理模块 - 基于JSON文件存储
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import hashlib
import secrets

from utils.logs import logger

class UserManager:
    """用户管理器 - 基于JSON文件存储"""
    
    def __init__(self, data_dir: str = "user_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.users_file = self.data_dir / "users.json"
        self.sessions_file = self.data_dir / "sessions.json"
        
        # 初始化数据文件
        self._init_data_files()
    
    def _init_data_files(self):
        """初始化数据文件"""
        if not self.users_file.exists():
            self._save_json(self.users_file, {})
        
        if not self.sessions_file.exists():
            self._save_json(self.sessions_file, {})
    
    def _load_json(self, file_path: Path) -> dict:
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_json(self, file_path: Path, data: dict):
        """保存JSON文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, username: str, password: str, display_name: str = None) -> Dict:
        """注册用户"""
        users = self._load_json(self.users_file)
        
        # 检查用户名是否已存在
        if username in users:
            raise ValueError(f"用户名 {username} 已存在")
        
        # 创建用户
        user_id = str(uuid.uuid4())
        user_data = {
            "user_id": user_id,
            "username": username,
            "display_name": display_name or username,
            "password_hash": self._hash_password(password),
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "is_active": True
        }
        
        users[username] = user_data
        self._save_json(self.users_file, users)
        
        # 创建用户目录
        user_dir = self.data_dir / "users" / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建用户的任务和文件记录
        (user_dir / "tasks.json").write_text('{}', encoding='utf-8')
        (user_dir / "files.json").write_text('{}', encoding='utf-8')
        
        logger.info(f"用户注册成功: {username} (ID: {user_id})")
        return {"user_id": user_id, "username": username, "display_name": user_data["display_name"]}
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """验证用户"""
        users = self._load_json(self.users_file)
        
        if username not in users:
            return None
        
        user = users[username]
        if not user["is_active"]:
            return None
        
        if user["password_hash"] != self._hash_password(password):
            return None
        
        # 更新最后登录时间
        user["last_login"] = datetime.now().isoformat()
        users[username] = user
        self._save_json(self.users_file, users)
        
        return {
            "user_id": user["user_id"],
            "username": user["username"],
            "display_name": user["display_name"]
        }
    
    def create_session(self, user_id: str) -> str:
        """创建用户会话"""
        sessions = self._load_json(self.sessions_file)
        
        session_token = secrets.token_urlsafe(32)
        session_data = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
        }
        
        sessions[session_token] = session_data
        self._save_json(self.sessions_file, sessions)
        
        return session_token
    
    def validate_session(self, session_token: str) -> Optional[str]:
        """验证会话并返回用户ID"""
        sessions = self._load_json(self.sessions_file)
        
        if session_token not in sessions:
            return None
        
        session = sessions[session_token]
        expires_at = datetime.fromisoformat(session["expires_at"])
        
        if datetime.now() > expires_at:
            # 会话过期，删除
            del sessions[session_token]
            self._save_json(self.sessions_file, sessions)
            return None
        
        return session["user_id"]
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        users = self._load_json(self.users_file)
        
        for username, user_data in users.items():
            if user_data["user_id"] == user_id:
                return {
                    "user_id": user_data["user_id"],
                    "username": user_data["username"],
                    "display_name": user_data["display_name"],
                    "created_at": user_data["created_at"],
                    "last_login": user_data["last_login"]
                }
        return None
    
    def list_all_users(self) -> List[Dict]:
        """列出所有用户（管理功能）"""
        users = self._load_json(self.users_file)
        return [
            {
                "user_id": user_data["user_id"],
                "username": user_data["username"],
                "display_name": user_data["display_name"],
                "created_at": user_data["created_at"],
                "last_login": user_data["last_login"],
                "is_active": user_data["is_active"]
            }
            for user_data in users.values()
        ]
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        sessions = self._load_json(self.sessions_file)
        now = datetime.now()
        
        expired_tokens = []
        for token, session_data in sessions.items():
            expires_at = datetime.fromisoformat(session_data["expires_at"])
            if now > expires_at:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del sessions[token]
        
        if expired_tokens:
            self._save_json(self.sessions_file, sessions)
            logger.info(f"清理了 {len(expired_tokens)} 个过期会话")


class UserDataManager:
    """用户数据管理器"""
    
    def __init__(self, data_dir: str = "user_data"):
        self.data_dir = Path(data_dir)
        self.users_dir = self.data_dir / "users"
        self.shared_dir = self.data_dir / "shared"
        
        self.shared_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化共享数据
        self.shared_tasks_file = self.shared_dir / "all_tasks.json"
        if not self.shared_tasks_file.exists():
            self._save_json(self.shared_tasks_file, {})
    
    def _load_json(self, file_path: Path) -> dict:
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_json(self, file_path: Path, data: dict):
        """保存JSON文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def save_user_file(self, user_id: str, file_id: str, file_info: Dict):
        """保存用户上传的文件信息"""
        user_dir = self.users_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        
        files_file = user_dir / "files.json"
        files_data = self._load_json(files_file)
        
        files_data[file_id] = {
            **file_info,
            "uploaded_at": datetime.now().isoformat(),
            "user_id": user_id
        }
        
        self._save_json(files_file, files_data)
    
    def get_user_files(self, user_id: str) -> Dict:
        """获取用户的文件列表"""
        user_dir = self.users_dir / user_id
        files_file = user_dir / "files.json"
        return self._load_json(files_file)
    
    def delete_user_file(self, user_id: str, file_id: str):
        """删除用户文件"""
        user_dir = self.users_dir / user_id
        files_file = user_dir / "files.json"
        files_data = self._load_json(files_file)
        
        if file_id in files_data:
            del files_data[file_id]
            self._save_json(files_file, files_data)
            logger.info(f"删除用户 {user_id} 的文件记录: {file_id}")
        else:
            logger.warning(f"文件 {file_id} 不存在于用户 {user_id} 的记录中")
    
    def save_user_task(self, user_id: str, task_id: str, task_info: Dict):
        """保存用户任务"""
        user_dir = self.users_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存到用户目录
        tasks_file = user_dir / "tasks.json"
        tasks_data = self._load_json(tasks_file)
        tasks_data[task_id] = task_info
        self._save_json(tasks_file, tasks_data)
        
        # 同时保存到共享目录（供所有用户查看）
        shared_tasks = self._load_json(self.shared_tasks_file)
        shared_tasks[task_id] = {
            **task_info,
            "user_id": user_id,
            "created_at": task_info.get("created_at", datetime.now().isoformat())
        }
        self._save_json(self.shared_tasks_file, shared_tasks)
    
    def get_user_tasks(self, user_id: str) -> Dict:
        """获取用户的任务列表"""
        user_dir = self.users_dir / user_id
        tasks_file = user_dir / "tasks.json"
        return self._load_json(tasks_file)
    
    def get_all_tasks(self) -> Dict:
        """获取所有用户的任务（共享数据）"""
        return self._load_json(self.shared_tasks_file)
    
    def update_task(self, user_id: str, task_id: str, updates: Dict):
        """更新任务状态"""
        # 更新用户目录中的任务
        user_dir = self.users_dir / user_id
        tasks_file = user_dir / "tasks.json"
        tasks_data = self._load_json(tasks_file)
        
        if task_id in tasks_data:
            tasks_data[task_id].update(updates)
            tasks_data[task_id]["updated_at"] = datetime.now().isoformat()
            self._save_json(tasks_file, tasks_data)
        
        # 更新共享目录中的任务
        shared_tasks = self._load_json(self.shared_tasks_file)
        if task_id in shared_tasks:
            shared_tasks[task_id].update(updates)
            shared_tasks[task_id]["updated_at"] = datetime.now().isoformat()
            self._save_json(self.shared_tasks_file, shared_tasks)
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务详情（从共享数据中）"""
        shared_tasks = self._load_json(self.shared_tasks_file)
        return shared_tasks.get(task_id)
    
    def update_task_by_id(self, task_id: str, updates: Dict):
        """通过任务ID更新任务（自动查找对应用户）"""
        shared_tasks = self._load_json(self.shared_tasks_file)
        if task_id not in shared_tasks:
            logger.warning(f"任务 {task_id} 在共享数据中不存在")
            return
        
        task = shared_tasks[task_id]
        user_id = task.get("user_id")
        
        if user_id:
            # 使用现有的update_task方法
            self.update_task(user_id, task_id, updates)
        else:
            # 如果没有user_id，直接更新共享数据
            shared_tasks[task_id].update(updates)
            shared_tasks[task_id]["updated_at"] = datetime.now().isoformat()
            self._save_json(self.shared_tasks_file, shared_tasks)
    
    def delete_task(self, user_id: str, task_id: str):
        """删除任务（仅创建者可删除）"""
        # 从用户目录删除
        user_dir = self.users_dir / user_id
        tasks_file = user_dir / "tasks.json"
        tasks_data = self._load_json(tasks_file)
        
        if task_id in tasks_data:
            del tasks_data[task_id]
            self._save_json(tasks_file, tasks_data)
        
        # 从共享目录删除（检查权限）
        shared_tasks = self._load_json(self.shared_tasks_file)
        if task_id in shared_tasks and shared_tasks[task_id]["user_id"] == user_id:
            del shared_tasks[task_id]
            self._save_json(self.shared_tasks_file, shared_tasks)
