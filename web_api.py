#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化版FastAPI - 固定使用三个模型评估标注质量
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

from fastapi import FastAPI, File, HTTPException, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# 导入现有的模块
from benchmarks.InteractComp import InteractCompBenchmark
from workflow.InteractComp import InteractCompAgent
from utils.logs import logger

app = FastAPI(title="InteractComp标注质量测试API", version="2.0.0")

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

# 任务状态存储
tasks: Dict[str, dict] = {}
uploaded_files: Dict[str, str] = {}

@app.get("/")
async def root():
    """根路径 - 检查服务状态"""
    return {
        "message": "InteractComp标注数据质量测试API - 配置文件版本",
        "version": "2.1.0",
        "evaluation_models": EVALUATION_MODELS,
        "config_note": "API Keys通过config2.yaml文件配置",
        "status": "running"
    }

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传JSONL数据文件"""
    if not file.filename.endswith(('.jsonl', '.json')):
        raise HTTPException(status_code=400, detail="只支持.jsonl和.json格式文件")
    
    file_id = str(uuid.uuid4())
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    
    file_path = temp_dir / f"{file_id}_{file.filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    uploaded_files[file_id] = str(file_path)
    
    logger.info(f"文件上传成功: {file.filename}, ID: {file_id}")
    
    return {
        "file_id": file_id,
        "filename": file.filename,
        "size": file_path.stat().st_size,
        "status": "uploaded"
    }

@app.post("/test/start")
async def start_test(
    file_ids: List[str],
    background_tasks: BackgroundTasks
):
    """开始三模型评估测试"""
    # 验证文件
    for file_id in file_ids:
        if file_id not in uploaded_files:
            raise HTTPException(status_code=400, detail=f"文件{file_id}不存在")
    
    # 验证配置文件
    try:
        config = get_config()
        if 'models' not in config:
            raise HTTPException(status_code=500, detail="配置文件格式错误：缺少models配置")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="未找到config2.yaml配置文件，请先配置API Keys")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置文件读取失败：{str(e)}")
    
    # 创建任务
    task_id = str(uuid.uuid4())
    task_info = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "created_at": datetime.now().isoformat(),
        "file_ids": file_ids,
        "evaluation_models": EVALUATION_MODELS
    }
    tasks[task_id] = task_info
    
    # 启动后台任务
    background_tasks.add_task(run_multi_model_evaluation, task_id, file_ids)
    
    logger.info(f"三模型评估任务启动: {task_id}")
    
    return {"task_id": task_id, "status": "started", "models": EVALUATION_MODELS}

@app.get("/test/{task_id}")
async def get_test_status(task_id: str):
    """获取测试状态"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return tasks[task_id]

@app.get("/test/{task_id}/download-csv")
async def download_csv_report(task_id: str):
    """下载CSV格式的测试报告"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="测试未完成")
    
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
        'models_correct_count', 'quality_failed', 'cost'
    ])
    
    # 写入数据
    for item in task.get("detailed_results", []):
        writer.writerow([
            item.get("question", ""),
            item.get("correct_answer", ""),
            item.get("model_results", {}).get("gpt-4o-mini", {}).get("answer", ""),
            item.get("model_results", {}).get("gpt-4o-mini", {}).get("correct", False),
            item.get("model_results", {}).get("gpt-4o", {}).get("answer", ""),
            item.get("model_results", {}).get("gpt-4o", {}).get("correct", False),
            item.get("model_results", {}).get("claude-3-5-sonnet-20241022", {}).get("answer", ""),
            item.get("model_results", {}).get("claude-3-5-sonnet-20241022", {}).get("correct", False),
            item.get("correct_models_count", 0),
            item.get("quality_failed", False),
            item.get("total_cost", 0.0)
        ])
    
    temp_file.close()
    
    return FileResponse(
        path=temp_file.name,
        filename=f"三模型评估报告_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        media_type='text/csv'
    )

async def run_multi_model_evaluation(task_id: str, file_ids: List[str]):
    """运行三模型评估"""
    task = tasks[task_id]
    
    try:
        task["status"] = "running"
        task["progress"] = 10
        
        # 1. 读取配置文件（不再需要更新，直接使用现有配置）
        config = get_config()
        task["progress"] = 20
        
        # 2. 合并数据文件
        combined_file_path = await merge_uploaded_files(file_ids, task_id)
        task["progress"] = 30

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
        task["progress"] = 40
        
        # 4. 执行多模型评估
        logger.info(f"开始多模型评估: {task_id}")

        results = await benchmark.run_multi_model_evaluation(
            agent_factory, 
            max_concurrent_tasks=20
        )
        task["progress"] = 90
        
        # 5. 处理结果
        avg_quality_failed_rate = results["avg_quality_failed_rate"]
        total_questions = results["total_questions"]
        quality_failed_count = results["quality_failed_count"]  
        quality_passed_count = total_questions - quality_failed_count
        total_cost = results["total_cost"]
        detailed_results = results["detailed_results"]
        
        # 6. 更新任务结果
        task.update({
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
        })
        
        # 7. 清理临时文件
        if os.path.exists(combined_file_path):
            os.remove(combined_file_path)
        
        logger.info(f"三模型评估完成: {task_id}, 不合格率: {avg_quality_failed_rate:.3f}")
        
    except Exception as e:
        task.update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        })
        logger.error(f"三模型评估失败: {task_id}, 错误: {e}")

# 多模型评估基准测试类
class MultiModelBenchmark:
    def __init__(self, name: str, file_path: str, log_path: str, models: List[str]):
        self.name = name
        self.file_path = file_path
        self.log_path = log_path  
        self.models = models
        self.grader_llm = None  # 将在评估时初始化

    async def run_multi_model_evaluation(self, max_concurrent_tasks: int = 20):
        """运行多模型评估"""
        # 加载数据
        data = []
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        
        # 初始化评分器
        from utils.async_llm import AsyncLLM
        self.grader_llm = AsyncLLM("gpt-4o")
        
        # 评估所有问题
        detailed_results = []
        total_cost = 0.0
        quality_failed_count = 0
        
        for i, problem in enumerate(data):
            logger.info(f"评估问题 {i+1}/{len(data)}")
            
            result = await self.evaluate_single_problem(problem)
            detailed_results.append(result)
            total_cost += result["total_cost"]
            
            if result["quality_failed"]:
                quality_failed_count += 1
        
        avg_quality_failed_rate = quality_failed_count / len(data) if data else 0
        
        return {
            "total_questions": len(data),
            "quality_failed_count": quality_failed_count,
            "avg_quality_failed_rate": avg_quality_failed_rate,
            "total_cost": total_cost,
            "detailed_results": detailed_results
        }

    async def evaluate_single_problem(self, problem: dict):
        """评估单个问题"""
        question = problem["question"]
        correct_answer = problem.get("answer", "")
        
        model_results = {}
        total_cost = 0.0
        correct_models_count = 0
        
        # 对每个模型进行评估
        for model in self.models:
            try:
                # 创建Agent
                agent = InteractCompAgent(
                    name=f"Agent_{model}",
                    llm_config=model,
                    dataset="InteractComp", 
                    prompt="",
                    max_turns=5,  # 减少轮数节省成本
                    search_engine_type="google",
                    user_config="gpt-4o"
                )
                
                # 获取模型答案
                predicted_answer, history, cost = await agent(problem)
                total_cost += cost
                
                # 评估答案正确性
                is_correct = await self.grade_answer(question, correct_answer, predicted_answer)
                
                model_results[model] = {
                    "answer": predicted_answer,
                    "correct": is_correct,
                    "cost": cost,
                    "history_length": len(history)
                }
                
                if is_correct:
                    correct_models_count += 1
                    
                logger.info(f"模型 {model}: {'正确' if is_correct else '错误'}")
                    
            except Exception as e:
                logger.error(f"模型 {model} 评估失败: {e}")
                model_results[model] = {
                    "answer": "评估失败",
                    "correct": False,
                    "cost": 0.0,
                    "error": str(e)
                }
        
        # 判断质量：2个以上模型答对就是质量不合格
        quality_failed = correct_models_count >= 2
        
        return {
            "question": question,
            "correct_answer": correct_answer,
            "model_results": model_results,
            "correct_models_count": correct_models_count,
            "quality_failed": quality_failed,
            "total_cost": total_cost
        }

    async def grade_answer(self, question: str, correct_answer: str, predicted_answer: str) -> bool:
        """评估答案正确性"""
        grading_prompt = f"""你是一个公正的评分员。

问题: {question}
预测答案: {predicted_answer}
正确答案: {correct_answer}

关键评分指令:
1. 预测答案必须与正确答案匹配
2. 寻找确切的名称匹配或对同一实体的明确引用
3. 考虑不同语言、翻译或替代名称作为潜在匹配
4. 严格要求：部分匹配或模糊相似性应为'no'

重要：只给出一个评分：
- 'yes': 预测答案正确识别了与正确答案相同的实体
- 'no': 预测答案错误、匹配了流行答案，或指向了不同的实体

只回答'yes'或'no'，不要其他内容。"""

        try:
            response = await self.grader_llm(grading_prompt)
            
            if "yes" in response.strip().lower():
                return True
            elif "no" in response.strip().lower():
                return False
            else:
                return False
                
        except Exception as e:
            logger.error(f"评分失败: {e}")
            return False

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

async def merge_uploaded_files(file_ids: List[str], task_id: str) -> str:
    """合并上传的数据文件为单个JSONL文件"""
    output_dir = Path("workspace") / task_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"temp_combined_{task_id}.jsonl"
    
    with open(output_path, 'w', encoding='utf-8') as out_f:
        for file_id in file_ids:
            file_path = uploaded_files[file_id]
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