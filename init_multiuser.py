#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化多用户系统的数据目录和结构
"""

import os
import json
from pathlib import Path
from datetime import datetime

def init_user_data_structure():
    """初始化用户数据目录结构"""
    base_dir = Path("user_data")
    
    # 创建基本目录
    directories = [
        base_dir,
        base_dir / "users",
        base_dir / "shared",
        Path("workspace"),
        Path("temp_uploads"),
        Path("logs")
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✅ 创建目录: {directory}")
    
    # 初始化基本数据文件
    files_to_init = {
        base_dir / "users.json": {},
        base_dir / "sessions.json": {},
        base_dir / "shared" / "all_tasks.json": {},
    }
    
    for file_path, default_data in files_to_init.items():
        if not file_path.exists():
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)
            print(f"✅ 创建文件: {file_path}")
        else:
            print(f"📁 文件已存在: {file_path}")
    
    # 创建 .gitignore 忽略敏感数据
    gitignore_content = """# 用户数据 - 包含敏感信息，不提交到版本控制
user_data/users.json
user_data/sessions.json
user_data/users/*/
temp_uploads/
workspace/
logs/
*.log
"""
    
    gitignore_path = Path(".gitignore")
    if not gitignore_path.exists():
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write(gitignore_content)
        print(f"✅ 创建文件: {gitignore_path}")
    else:
        # 检查是否需要添加用户数据忽略规则
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "user_data/" not in content:
            with open(gitignore_path, 'a', encoding='utf-8') as f:
                f.write(f"\n# 多用户数据忽略规则 - {datetime.now().isoformat()}\n")
                f.write(gitignore_content)
            print(f"✅ 更新文件: {gitignore_path}")
    
    print("\n🎉 用户数据结构初始化完成!")
    return True

def create_demo_users():
    """创建演示用户数据（可选）"""
    try:
        from utils.user_manager import UserManager
        
        user_manager = UserManager()
        users = user_manager.list_all_users()
        
        if len(users) > 0:
            print(f"📊 当前已有 {len(users)} 个用户，跳过演示数据创建")
            return
        
        # 创建演示用户
        demo_users = [
            {"username": "admin", "password": "admin123", "display_name": "管理员"},
            {"username": "test_user", "password": "test123", "display_name": "测试用户"},
            {"username": "researcher", "password": "research123", "display_name": "研究员"}
        ]
        
        print("\n🧪 创建演示用户数据...")
        for user_data in demo_users:
            try:
                result = user_manager.register_user(
                    user_data["username"],
                    user_data["password"],
                    user_data["display_name"]
                )
                print(f"✅ 创建用户: {result['username']} ({result['user_id'][:8]}...)")
            except Exception as e:
                print(f"⚠️ 用户 {user_data['username']} 创建失败: {e}")
        
        print("\n🔑 演示用户登录信息:")
        for user_data in demo_users:
            print(f"  用户名: {user_data['username']}, 密码: {user_data['password']}")
            
    except ImportError:
        print("⚠️ 无法导入用户管理器，跳过演示用户创建")
    except Exception as e:
        print(f"❌ 创建演示用户失败: {e}")

if __name__ == "__main__":
    print("🔧 初始化InteractComp多用户系统...")
    
    init_user_data_structure()
    
    # 询问是否创建演示用户
    try:
        response = input("\n是否创建演示用户数据? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            create_demo_users()
    except KeyboardInterrupt:
        print("\n👋 初始化完成")
    
    print("\n✨ 系统初始化完成，可以启动服务了!")
    print("📝 下一步: python start_multiuser.py")
