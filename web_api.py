#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多用户版FastAPI - 固定使用三个模型评估标注质量
"""

import asyncio
import json
import os
import tempfile
import uuid
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import shutil
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, File, HTTPException, UploadFile, BackgroundTasks, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# 导入现有的模块
from benchmarks.InteractComp import InteractCompBenchmark
from workflow.InteractComp import InteractCompAgent
from utils.logs import logger
from utils.user_manager import UserManager, UserDataManager

app = FastAPI(title="InteractComp多用户标注质量测试API", version="3.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

# 固定的三个评估模型
EVALUATION_MODELS = [
    "gpt-5-mini",
    "gpt-5", 
    "claude-4-sonnet"
]

# 初始化用户管理器
user_manager = UserManager()
user_data_manager = UserDataManager()

# 并发任务管理器
class TaskManager:
    def __init__(self):
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.executor = ThreadPoolExecutor(max_workers=15)  # 最多5个并发评估任务
    
    def start_task(self, task_id: str, coro):
        """启动新的异步任务"""
        if task_id in self.running_tasks:
            logger.warning(f"任务 {task_id} 已在运行中")
            return
        
        # 包装协程，增加异常处理
        async def wrapped_coro():
            try:
                await coro
                logger.info(f"任务 {task_id} 成功完成")
            except Exception as e:
                logger.error(f"任务 {task_id} 执行失败: {e}")
                # 更新任务状态为失败
                try:
                    user_data_manager.update_task_by_id(task_id, {
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.now().isoformat()
                    })
                except Exception as update_error:
                    logger.error(f"更新任务状态失败 {task_id}: {update_error}")
        
        task = asyncio.create_task(wrapped_coro())
        self.running_tasks[task_id] = task
        
        # 任务完成后自动清理
        def cleanup(future):
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
                logger.debug(f"任务 {task_id} 已清理，剩余运行任务数: {len(self.running_tasks)}")
        
        task.add_done_callback(cleanup)
        logger.info(f"任务 {task_id} 已启动，当前运行任务数: {len(self.running_tasks)}")
    
    def is_task_running(self, task_id: str) -> bool:
        """检查任务是否正在运行"""
        return task_id in self.running_tasks
    
    def get_running_task_count(self) -> int:
        """获取当前运行任务数量"""
        return len(self.running_tasks)
    
    def get_running_task_ids(self) -> List[str]:
        """获取正在运行的任务ID列表"""
        return list(self.running_tasks.keys())

# 创建全局任务管理器
task_manager = TaskManager()

# Pydantic模型
class UserRegister(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class TaskCreate(BaseModel):
    file_ids: List[str]

# 认证依赖
async def get_current_user(authorization: Optional[str] = Header(None)):
    """获取当前用户"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证信息")
    
    token = authorization[7:]  # 移除 "Bearer "
    user_id = user_manager.validate_session(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="认证失效，请重新登录")
    
    user_info = user_manager.get_user_info(user_id)
    if not user_info:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    return user_info

# 支持的搜索引擎配置（用于Google搜索）
def get_search_config():
    """获取搜索引擎配置"""
    try:
        config = get_config()
        return config.get('search', {})
    except:
        return {}

# 配置读取函数
def load_config():
    """从config2.yaml加载配置"""
    import yaml
    from pathlib import Path
    
    config_paths = [
        Path("config/config2.yaml"),
        Path("config2.yaml"),
        Path("./config/config2.yaml")
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.error(f"读取配置文件失败: {e}")
                continue
    
    raise FileNotFoundError("未找到config2.yaml配置文件")

# 全局配置
CONFIG = None

def get_config():
    """获取配置，如果未加载则加载"""
    global CONFIG
    if CONFIG is None:
        CONFIG = load_config()
    return CONFIG

@app.get("/")
async def root():
    """根路径 - 检查服务状态"""
    return {
        "message": "InteractComp多用户标注数据质量测试API",
        "version": "3.0.0",
        "evaluation_models": EVALUATION_MODELS,
        "features": ["多用户支持", "数据共享", "会话管理"],
        "config_note": "API Keys通过config2.yaml文件配置",
        "status": "running"
    }

# 用户认证相关接口
@app.post("/auth/register")
async def register_user(user_data: UserRegister):
    """用户注册"""
    try:
        result = user_manager.register_user(
            username=user_data.username,
            password=user_data.password,
            display_name=user_data.display_name
        )
        return {
            "message": "注册成功",
            "user": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/login")
async def login_user(user_data: UserLogin):
    """用户登录"""
    user_info = user_manager.authenticate_user(user_data.username, user_data.password)
    if not user_info:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 创建会话
    session_token = user_manager.create_session(user_info["user_id"])
    
    return {
        "message": "登录成功",
        "user": user_info,
        "token": session_token
    }

@app.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user

@app.post("/auth/logout")
async def logout_user(authorization: Optional[str] = Header(None)):
    """用户登出（清理会话）"""
    # 这里可以添加会话清理逻辑
    return {"message": "登出成功"}

# 用户管理接口
@app.get("/users")
async def list_users(current_user: dict = Depends(get_current_user)):
    """获取所有用户列表"""
    users = user_manager.list_all_users()
    return {
        "users": users,
        "total": len(users)
    }

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """上传JSONL数据文件"""
    if not file.filename.endswith(('.jsonl', '.json')):
        raise HTTPException(status_code=400, detail="只支持.jsonl或.json文件")
    
    file_id = str(uuid.uuid4())
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    
    file_path = temp_dir / f"{file_id}_{file.filename}"
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # 保存文件信息到用户数据
    file_info = {
        "file_id": file_id,
        "filename": file.filename,
        "size": len(content),
        "file_path": str(file_path),
        "status": "uploaded"
    }
    
    user_data_manager.save_user_file(current_user["user_id"], file_id, file_info)
    
    logger.info(f"用户 {current_user['username']} 上传文件: {file.filename}, ID: {file_id}")
    
    return {
        "file_id": file_id,
        "filename": file.filename,
        "size": len(content),
        "status": "uploaded"
    }

@app.get("/files")
async def get_user_files(current_user: dict = Depends(get_current_user)):
    """获取当前用户的文件列表"""
    files = user_data_manager.get_user_files(current_user["user_id"])
    return {
        "files": list(files.values()),
        "total": len(files)
    }

@app.delete("/files/{file_id}")
async def delete_user_file(file_id: str, current_user: dict = Depends(get_current_user)):
    """删除用户文件"""
    try:
        # 检查文件是否属于当前用户
        user_files = user_data_manager.get_user_files(current_user["user_id"])
        if file_id not in user_files:
            raise HTTPException(status_code=404, detail="文件不存在或无权限")
        
        # 检查文件是否正在被任务使用
        user_tasks = user_data_manager.get_user_tasks(current_user["user_id"])
        for task_id, task in user_tasks.items():
            if task.get('status') == 'running' and file_id in task.get('file_ids', []):
                raise HTTPException(status_code=400, detail="文件正在被运行中的任务使用，无法删除")
        
        file_info = user_files[file_id]
        file_path = file_info.get('file_path')
        
        # 删除物理文件
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"删除物理文件: {file_path}")
        
        # 从用户数据中删除文件记录
        user_data_manager.delete_user_file(current_user["user_id"], file_id)
        
        logger.info(f"用户 {current_user['username']} 删除文件: {file_id}")
        
        return {"success": True, "message": "文件删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败: {file_id}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")

@app.post("/start_test")
async def start_test(
    task_data: TaskCreate,
    current_user: dict = Depends(get_current_user)
):
    """开始三模型评估测试"""
    # 验证文件权限（检查文件是否属于当前用户）
    user_files = user_data_manager.get_user_files(current_user["user_id"])
    for file_id in task_data.file_ids:
        if file_id not in user_files:
            raise HTTPException(status_code=403, detail=f"文件 {file_id} 不属于当前用户")
    
    # 验证配置文件
    try:
        get_config()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="配置文件config2.yaml未找到")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置文件错误: {str(e)}")
    
    # 创建任务
    task_id = str(uuid.uuid4())
    task_info = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "created_at": datetime.now().isoformat(),
        "file_ids": task_data.file_ids,
        "evaluation_models": EVALUATION_MODELS,
        "user_id": current_user["user_id"],
        "username": current_user["username"],
        "display_name": current_user["display_name"]
    }
    
    # 保存任务到用户数据
    user_data_manager.save_user_task(current_user["user_id"], task_id, task_info)
    
    # 使用任务管理器启动并发任务
    evaluation_coro = run_multi_model_evaluation(task_id, task_data.file_ids, current_user["user_id"])
    task_manager.start_task(task_id, evaluation_coro)
    
    logger.info(f"用户 {current_user['username']} 启动三模型评估任务: {task_id}，当前运行任务数: {task_manager.get_running_task_count()}")
    
    return {"task_id": task_id, "status": "started", "models": EVALUATION_MODELS}

@app.get("/system/status")
async def get_system_status():
    """获取系统状态"""
    return {
        "running_tasks": task_manager.get_running_task_count(),
        "running_task_ids": task_manager.get_running_task_ids(),
        "max_concurrent_tasks": 5,
        "system_time": datetime.now().isoformat(),
        "available_slots": max(0, 5 - task_manager.get_running_task_count())
    }

@app.get("/test/{task_id}")
async def get_test_status(task_id: str, current_user: dict = Depends(get_current_user)):
    """获取测试状态"""
    # 从共享数据中获取任务（所有用户都可以查看）
    task = user_data_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return task

@app.get("/tasks")
async def get_tasks(current_user: dict = Depends(get_current_user)):
    """获取任务列表"""
    # 用户自己的任务
    user_tasks = user_data_manager.get_user_tasks(current_user["user_id"])
    # 所有用户的任务（共享查看）
    all_tasks = user_data_manager.get_all_tasks()
    
    return {
        "user_tasks": list(user_tasks.values()),
        "all_tasks": list(all_tasks.values()),
        "user_task_count": len(user_tasks),
        "total_task_count": len(all_tasks)
    }

@app.get("/test/{task_id}/download-csv")
async def download_csv_report(task_id: str, current_user: dict = Depends(get_current_user)):
    """下载CSV格式的测试报告"""
    # 从共享数据中获取任务（所有用户都可以下载）
    task = user_data_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务未完成，无法下载报告")
    
    # 创建详细的CSV报告
    import tempfile
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
    
    writer = csv.writer(temp_file)
    # CSV标题
    writer.writerow([
        'question', 'correct_answer', 
        'gpt5_mini_answer', 'gpt5_mini_correct',
        'gpt5_answer', 'gpt5_correct', 
        'claude4_answer', 'claude4_correct',
        'models_correct_count', 'quality_failed', 'cost',
        'created_by', 'created_at'
    ])
    
    # 写入数据
    for item in task.get("detailed_results", []):
        writer.writerow([
            item.get("question", ""),
            item.get("correct_answer", ""),
            item.get("model_results", {}).get("gpt-5-mini", {}).get("answer", ""),           
            item.get("model_results", {}).get("gpt-5-mini", {}).get("correct", False),       
            item.get("model_results", {}).get("gpt-5", {}).get("answer", ""),               
            item.get("model_results", {}).get("gpt-5", {}).get("correct", False),           
            item.get("model_results", {}).get("claude-4-sonnet", {}).get("answer", ""),     
            item.get("model_results", {}).get("claude-4-sonnet", {}).get("correct", False), 
            item.get("correct_models_count", 0),
            item.get("quality_failed", False),
            item.get("total_cost", 0.0),
            task.get('display_name', task.get('username', '未知用户')),
            task.get('created_at', '')
        ])
    
    temp_file.close()
    
    task_creator = task.get('display_name', task.get('username', '未知用户'))
    return FileResponse(
        path=temp_file.name,
        filename=f"三模型评估报告_{task_creator}_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        media_type='text/csv'
    )

async def run_multi_model_evaluation(task_id: str, file_ids: List[str], user_id: str):
    """运行三模型评估"""
    task = user_data_manager.get_task(task_id)
    if not task:
        logger.error(f"任务不存在: {task_id}")
        return
    
    try:
        user_data_manager.update_task(user_id, task_id, {"status": "running", "progress": 10})
        
        # 1. 读取配置文件
        config = get_config()
        user_data_manager.update_task(user_id, task_id, {"progress": 20})
        
        # 2. 合并数据文件
        combined_file_path = await merge_uploaded_files(file_ids, task_id, user_id)
        user_data_manager.update_task(user_id, task_id, {"progress": 30})

        # 3. 创建多模型评估器和Agent工厂
        log_path = f"workspace/multi_model_test_{task_id}/"
        os.makedirs(log_path, exist_ok=True)

        # 使用修改后的InteractCompBenchmark，支持多模型评估
        benchmark = InteractCompBenchmark(
            name=f"MultiModelTest_{task_id}",
            file_path=combined_file_path,
            log_path=log_path,
            grader_config="gpt-4o",
            models=EVALUATION_MODELS  # 传入评估模型列表
        )

        # 创建Agent工厂
        from workflow.InteractComp import create_multi_model_agent_factory
        agent_factory = create_multi_model_agent_factory(
            max_turns=5,  # 多模型评估时减少轮数节省成本
            search_engine_type="google",
            user_config="gpt-4o"
        )
        user_data_manager.update_task(user_id, task_id, {"progress": 40})
        
        # 4. 执行多模型评估
        logger.info(f"开始多模型评估: {task_id}")

        results = await benchmark.run_multi_model_evaluation(
            agent_factory, 
            max_concurrent_tasks=20
        )
        user_data_manager.update_task(user_id, task_id, {"progress": 90})
        
        # 5. 处理结果
        avg_quality_failed_rate = results["avg_quality_failed_rate"]
        total_questions = results["total_questions"]
        quality_failed_count = results["quality_failed_count"]  
        quality_passed_count = total_questions - quality_failed_count
        total_cost = results["total_cost"]
        detailed_results = results["detailed_results"]
        
        # 6. 更新任务结果
        final_update = {
            "status": "completed",
            "progress": 100,
            "total_questions": total_questions,
            "quality_passed_count": quality_passed_count,  # 质量合格数（少数模型答对）
            "quality_failed_count": quality_failed_count,  # 质量不合格数（多数模型答对）
            "quality_failed_rate": avg_quality_failed_rate,  # 质量不合格率
            "total_cost": total_cost,
            "detailed_results": detailed_results,
            "failed_items": [item for item in detailed_results if item["quality_failed"]],
            "completed_at": datetime.now().isoformat(),
            "evaluation_summary": {
                "models_used": EVALUATION_MODELS,
                "evaluation_logic": "质量不合格 = 2个以上模型答对",
                "quality_standard": "优秀标注应该让多数AI模型难以找到正确答案"
            }
        }
        
        user_data_manager.update_task(user_id, task_id, final_update)
        
        # 7. 清理临时文件
        if os.path.exists(combined_file_path):
            os.remove(combined_file_path)
        
        logger.info(f"三模型评估完成: {task_id}, 不合格率: {avg_quality_failed_rate:.3f}")
        
    except Exception as e:
        error_update = {
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }
        
        user_data_manager.update_task(user_id, task_id, error_update)
            
        logger.error(f"三模型评估失败: {task_id}, 错误: {e}")

@app.get("/config/status")
async def get_config_status():
    """检查配置文件状态"""
    try:
        config = get_config()
        models = config.get('models', {})
        
        # 检查必需的模型配置
        required_models = EVALUATION_MODELS
        missing_models = []
        configured_models = []
        
        for model in required_models:
            if model not in models:
                missing_models.append(f"{model} (未配置)")
            elif not models[model].get('api_key'):
                missing_models.append(f"{model} (缺少API Key)")
            else:
                configured_models.append(model)
        
        logger.info(f"配置检查 - 已配置: {configured_models}, 缺失: {missing_models}")
        
        return {
            "config_found": True,
            "models_configured": len(configured_models),
            "configured_models": configured_models,
            "required_models": required_models,
            "missing_models": missing_models,
            "ready": len(missing_models) == 0,
            "config_path": "config/config2.yaml"
        }
        
    except FileNotFoundError:
        logger.warning("配置文件未找到")
        return {
            "config_found": False,
            "error": "未找到 config2.yaml 配置文件",
            "ready": False,
            "suggestion": "请参考 config2.example.yaml 创建配置文件"
        }
    except Exception as e:
        logger.error(f"配置检查失败: {e}")
        return {
            "config_found": False,
            "error": f"配置文件读取失败: {str(e)}",
            "ready": False
        }

async def merge_uploaded_files(file_ids: List[str], task_id: str, user_id: str = None) -> str:
    """合并上传的数据文件为单个JSONL文件"""
    output_dir = Path("workspace") / task_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"temp_combined_{task_id}.jsonl"
    
    with open(output_path, 'w', encoding='utf-8') as out_f:
        for file_id in file_ids:
            # 从用户数据中获取文件路径
            if user_id:
                user_files = user_data_manager.get_user_files(user_id)
                if file_id not in user_files:
                    logger.warning(f"文件 {file_id} 不属于用户 {user_id}")
                    continue
                file_path = user_files[file_id]['file_path']
            else:
                # 回退到临时存储文件夹搜索
                temp_dir = Path("temp_uploads")
                file_path = None
                for temp_file in temp_dir.glob(f"{file_id}_*"):
                    file_path = str(temp_file)
                    break
                if not file_path:
                    logger.error(f"找不到文件: {file_id}")
                    continue
            
            with open(file_path, 'r', encoding='utf-8') as in_f:
                if file_path.endswith('.jsonl'):
                    for line in in_f:
                        if line.strip():
                            out_f.write(line)
                else:  # .json
                    data = json.load(in_f)
                    if isinstance(data, list):
                        for item in data:
                            out_f.write(json.dumps(item, ensure_ascii=False) + '\n')
                    else:
                        out_f.write(json.dumps(data, ensure_ascii=False) + '\n')
    
    return str(output_path)

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 启动InteractComp三模型标注质量测试平台")
    print("🤖 评估模型:", EVALUATION_MODELS)
    print("📊 评估逻辑: 2个以上模型答对 = 标注质量不合格")
    
    # 检查配置文件
    try:
        config = load_config()
        print("✅ 配置文件加载成功")
        models = config.get('models', {})
        
        for model in EVALUATION_MODELS:
            if model in models and models[model].get('api_key'):
                print(f"✅ {model} 配置完成")
            else:
                print(f"⚠️ {model} 配置缺失")
                
    except FileNotFoundError:
        print("❌ 未找到config2.yaml配置文件")
        print("📝 请参考config2.example.yaml创建配置文件")
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
    
    print("🌐 API文档: http://localhost:8000/docs")
    print("📋 配置状态: http://localhost:8000/config/status")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)