#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的FastAPI包装器 - 基于现有的InteractCompAgent和InteractCompBenchmark
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

app = FastAPI(title="InteractComp标注质量测试API", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class TestConfig(BaseModel):
    llm_config: str = "gpt-4o"  # 对应你代码中的llm_config参数
    user_config: str = "gpt-4o"  # 对应你代码中的user_config参数  
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    max_turns: int = 5
    search_engine_type: str = "llm_knowledge"  # llm_knowledge, google, wikipedia
    max_concurrent_tasks: int = 1

# 任务状态存储
tasks: Dict[str, dict] = {}
uploaded_files: Dict[str, str] = {}

@app.get("/")
async def root():
    """根路径 - 检查服务状态"""
    return {
        "message": "InteractComp标注数据质量测试API",
        "version": "1.0.0",
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
    config: TestConfig,
    background_tasks: BackgroundTasks
):
    """开始测试任务"""
    # 验证文件
    for file_id in file_ids:
        if file_id not in uploaded_files:
            raise HTTPException(status_code=400, detail=f"文件{file_id}不存在")
    
    # 创建任务
    task_id = str(uuid.uuid4())
    task_info = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "created_at": datetime.now().isoformat(),
        "config": config.dict(),
        "file_ids": file_ids
    }
    tasks[task_id] = task_info
    
    # 启动后台任务
    background_tasks.add_task(run_test_with_existing_code, task_id, file_ids, config)
    
    logger.info(f"测试任务启动: {task_id}")
    
    return {"task_id": task_id, "status": "started"}

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
    
    # 查找生成的CSV文件
    log_path = f"workspace/web_test_{task_id}/"
    csv_files = list(Path(log_path).glob("*.csv"))
    
    if csv_files:
        # 返回最新的CSV文件
        latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
        return FileResponse(
            path=str(latest_csv),
            filename=f"interactcomp_test_results_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            media_type='text/csv'
        )
    else:
        # 如果没有CSV文件，生成一个简单的CSV
        import csv
        import tempfile
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
        
        writer = csv.writer(temp_file)
        writer.writerow(['question', 'correct_answer', 'predicted_answer', 'score', 'cost'])
        
        # 从failed_items写入数据
        for item in task.get("failed_items", []):
            writer.writerow([
                item.get("question", ""),
                item.get("expected_answer", ""),
                item.get("actual_answer", ""),
                0.0,  # 失败项目得分为0
                task.get("average_cost", 0.0)
            ])
        
        temp_file.close()
        
        return FileResponse(
            path=temp_file.name,
            filename=f"interactcomp_test_results_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            media_type='text/csv'
        )

@app.get("/test/{task_id}/download")
async def download_report(task_id: str):
    """下载JSON格式的测试报告（保留兼容性）"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="测试未完成")
    
    # 创建临时报告文件
    report = {
        "task_id": task_id,
        "results": task,
        "generated_at": datetime.now().isoformat()
    }
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(report, temp_file, ensure_ascii=False, indent=2)
    temp_file.close()
    
    return FileResponse(
        path=temp_file.name,
        filename=f"interactcomp_test_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        media_type='application/json'
    )

async def run_test_with_existing_code(task_id: str, file_ids: List[str], config: TestConfig):
    """使用现有的InteractCompAgent和InteractCompBenchmark运行测试"""
    task = tasks[task_id]
    
    try:
        task["status"] = "running"
        task["progress"] = 10
        
        # 1. 更新配置文件 (基于你的config2.yaml格式)
        await update_config_file(config)
        task["progress"] = 20
        
        # 2. 合并上传的数据文件
        combined_file_path = await merge_uploaded_files(file_ids, task_id)
        task["progress"] = 30

        # 3. 创建InteractCompAgent实例 (使用你的代码结构)
        agent = InteractCompAgent(
            name="WebTest",
            llm_config=config.llm_config,
            dataset="InteractComp",
            prompt="",  # 你的代码中prompt为空字符串
            max_turns=config.max_turns,
            search_engine_type=config.search_engine_type,
            user_config=config.user_config
        )
        task["progress"] = 40

        # 4. 创建InteractCompBenchmark实例
        log_path = f"workspace/web_test_{task_id}/"
        os.makedirs(log_path, exist_ok=True)

        benchmark = InteractCompBenchmark(
            name=f"WebTest_{task_id}",
            file_path=combined_file_path,
            log_path=log_path,
            grader_config=config.user_config
        )
        task["progress"] = 50
        
        # 5. 执行测试 (直接调用你的run_baseline方法)
        logger.info(f"开始执行InteractComp基准测试: {task_id}")

        average_score, average_cost, total_cost = await benchmark.run_baseline(
            agent,
            max_concurrent_tasks=config.max_concurrent_tasks
        )
        
        task["progress"] = 90
        
        # 6. 处理结果
        # 计算成功/失败数量 (基于你的逻辑：好的标注=模型答错)
        # 读取数据文件获取总问题数
        total_questions = 0
        with open(combined_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    total_questions += 1
        
        successful_tests = int(average_score * total_questions)  # 模型答错的数量
        failed_tests = total_questions - successful_tests  # 模型答对的数量(需要改进)
        
        # 7. 读取失败日志 (模型答对的案例)
        failed_items = []
        log_file = Path(log_path) / "log.json"
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    failed_logs = json.load(f)
                    for item in failed_logs[:10]:  # 最多10个
                        failed_items.append({
                            "question": item.get("question", ""),
                            "expected_answer": item.get("right_answer", ""),
                            "actual_answer": item.get("extracted_output", ""),
                            "reason": "模型找到了正确答案，建议增加问题难度"
                        })
            except Exception as e:
                logger.error(f"读取日志失败: {e}")
        
        # 8. 更新任务结果
        task.update({
            "status": "completed",
            "progress": 100,
            "total_questions": total_questions,
            "successful_tests": successful_tests,  # 好的标注数量
            "failed_tests": failed_tests,  # 需要改进的数量
            "average_score": average_score,  # 标注质量分
            "average_cost": average_cost,
            "total_cost": total_cost,
            "failed_items": failed_items,
            "completed_at": datetime.now().isoformat()
        })
        
        # 9. 清理临时文件
        if os.path.exists(combined_file_path):
            os.remove(combined_file_path)
        
        logger.info(f"测试完成: {task_id}, 质量分: {average_score:.3f}")
        
    except Exception as e:
        task.update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        })
        logger.error(f"测试失败: {task_id}, 错误: {e}")

async def update_config_file(config: TestConfig):
    """更新config2.yaml文件 (基于你的配置格式)"""
    import yaml
    
    config_data = {
        "models": {
            config.llm_config: {
                "api_type": "openai",
                "base_url": config.base_url,
                "api_key": config.api_key,
                "temperature": 0
            },
            config.user_config: {
                "api_type": "openai",
                "base_url": config.base_url, 
                "api_key": config.api_key,
                "temperature": 0
            }
        }
    }
    
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    with open(config_dir / "config2.yaml", 'w', encoding='utf-8') as f:
        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

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
    
    return output_path

if __name__ == "__main__":
    import uvicorn
    print("🚀 启动InteractComp标注质量测试平台API服务")
    print("🌐 API文档: http://localhost:8000/docs")
    print("📊 基于现有InteractCompAgent和InteractCompBenchmark")
    uvicorn.run(app, host="0.0.0.0", port=8000)