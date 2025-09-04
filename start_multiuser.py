#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多用户版启动脚本
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.logs import logger
from utils.user_manager import UserManager, UserDataManager

def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境...")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        return False
    
    print(f"✅ Python版本: {sys.version}")
    
    # 检查必需的目录
    dirs_to_check = ['config', 'user_data', 'workspace', 'temp_uploads', 'logs']
    for dir_name in dirs_to_check:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            print(f"📁 创建目录: {dir_name}")
            dir_path.mkdir(parents=True, exist_ok=True)
        else:
            print(f"✅ 目录存在: {dir_name}")
    
    # 检查配置文件
    config_file = project_root / 'config' / 'config2.yaml'
    if not config_file.exists():
        example_file = project_root / 'config' / 'config2.example.yaml'
        if example_file.exists():
            print("⚠️  config2.yaml不存在，请基于config2.example.yaml创建配置文件")
            print(f"📝 示例: cp {example_file} {config_file}")
        else:
            print("❌ 配置文件和示例文件都不存在")
        return False
    else:
        print("✅ 配置文件存在: config2.yaml")
    
    return True

def initialize_user_system():
    """初始化用户系统"""
    print("🔧 初始化用户系统...")
    
    try:
        user_manager = UserManager()
        user_data_manager = UserDataManager()
        print("✅ 用户系统初始化完成")
        
        # 检查是否存在管理员用户
        users = user_manager.list_all_users()
        if not users:
            print("📝 检测到首次运行，是否创建管理员用户? (y/N): ", end='')
            response = input().strip().lower()
            if response in ['y', 'yes']:
                create_admin_user(user_manager)
        else:
            print(f"✅ 发现 {len(users)} 个用户")
            
        return True
    except Exception as e:
        print(f"❌ 用户系统初始化失败: {e}")
        return False

def create_admin_user(user_manager):
    """创建管理员用户"""
    print("\n创建管理员用户:")
    username = input("请输入用户名: ").strip()
    if not username:
        print("❌ 用户名不能为空")
        return
    
    password = input("请输入密码: ").strip()
    if not password:
        print("❌ 密码不能为空")
        return
    
    display_name = input("请输入显示名称 (可选): ").strip()
    if not display_name:
        display_name = username
    
    try:
        result = user_manager.register_user(username, password, display_name)
        print(f"✅ 管理员用户创建成功: {result['username']}")
        print(f"🔑 用户ID: {result['user_id']}")
    except Exception as e:
        print(f"❌ 创建用户失败: {e}")

def start_services():
    """启动服务"""
    print("\n🚀 启动InteractComp多用户平台...")
    
    # 导入并启动web_api
    try:
        from web_api import app
        import uvicorn
        
        print("🌐 启动后端服务...")
        print("📱 前端开发服务器请在frontend目录运行: npm run dev")
        print("📊 API文档: http://localhost:8000/docs")
        print("🔧 配置状态: http://localhost:8000/config/status")
        print("🎯 多用户登录: http://localhost:3000")
        
        uvicorn.run(app, host="0.0.0.0", port=8000)
        
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("🧠 InteractComp 多用户标注质量测试平台")
    print("=" * 60)
    
    # 检查环境
    if not check_environment():
        print("❌ 环境检查失败")
        return
    
    # 初始化用户系统
    if not initialize_user_system():
        print("❌ 用户系统初始化失败")
        return
    
    # 启动服务
    start_services()

if __name__ == "__main__":
    main()
