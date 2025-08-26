#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   run_baseline.py
@Time    :   2025/08/11
@Author  :   Deng Mingyi1
"""

import asyncio
from utils.logs import logger

from benchmarks.InteractComp import InteractCompBenchmark
from workflow.InteractComp import InteractCompAgent, create_multi_model_agent_factory

# 评估模型配置
SINGLE_MODEL_CONFIGS = [
    "gpt-5-mini",
    "gpt-5", 
    "claude-4-sonnet"
]

MULTI_MODEL_CONFIGS = [
    "gpt-5-mini",
    "gpt-5", 
    "claude-4-sonnet"
]

async def run_single_model_evaluation():
    """运行单模型评估（原有模式）"""
    dataset_path = "data/data.jsonl"
    log_path = "workspace/"
    prompt = ""
    
    results_summary = []
    
    for model_config in SINGLE_MODEL_CONFIGS:
        print(f"\n🚀 Running single model evaluation: {model_config}")
        
        # 创建单个Agent
        agent = InteractCompAgent(
            name=f"SingleAgent_{model_config}",
            llm_config=model_config,
            dataset="InteractComp",
            prompt=prompt,
            max_turns=5,
            search_engine_type="google",
            user_config="gpt-4o"
        )

        # 创建单模型基准测试
        benchmark = InteractCompBenchmark(
            name=f"SingleModel_{model_config}", 
            file_path=dataset_path, 
            log_path=f"{log_path}/single_{model_config}/",
            grader_config="gpt-4o"
            # 不传入models参数，使用单模型模式
        )

        # 运行评估
        avg_score, avg_cost, total_cost = await benchmark.run_baseline(agent, max_concurrent_tasks=1)
        
        results_summary.append({
            "model": model_config,
            "mode": "single",
            "avg_score": avg_score,
            "avg_cost": avg_cost,
            "total_cost": total_cost
        })
        
        print(f"🎯 {model_config} - Average Score: {avg_score:.3f} ({avg_score*100:.1f}%)")
        print(f"💰 {model_config} - Average Cost: ${avg_cost:.4f}")
        print(f"💰 {model_config} - Total Cost: ${total_cost:.4f}")
    
    return results_summary

async def run_multi_model_evaluation():
    """运行多模型评估（新模式）"""
    dataset_path = "data/data.jsonl"
    log_path = "workspace/multi_model/"
    
    print(f"\n🤖 Running multi-model evaluation: {MULTI_MODEL_CONFIGS}")
    
    # 创建Agent工厂
    agent_factory = create_multi_model_agent_factory(
        max_turns=5,  # 多模型时减少轮数节省成本
        search_engine_type="google",
        user_config="gpt-4o"
    )

    # 创建多模型基准测试
    benchmark = InteractCompBenchmark(
        name="MultiModelEvaluation", 
        file_path=dataset_path, 
        log_path=log_path,
        grader_config="gpt-4o",
        models=MULTI_MODEL_CONFIGS  # 传入模型列表启用多模型模式
    )

    # 运行多模型评估
    results = await benchmark.run_multi_model_evaluation(
        agent_factory, 
        max_concurrent_tasks=1
    )
    
    print(f"\n🎯 Multi-Model Evaluation Results:")
    print(f"📊 Total Questions: {results['total_questions']}")
    print(f"❌ Quality Failed: {results['quality_failed_count']} ({results['avg_quality_failed_rate']*100:.1f}%)")
    print(f"✅ Quality Passed: {results['total_questions'] - results['quality_failed_count']} ({(1-results['avg_quality_failed_rate'])*100:.1f}%)")
    print(f"💰 Total Cost: ${results['total_cost']:.4f}")
    print(f"💰 Average Cost: ${results['avg_cost']:.4f}")
    
    # 显示质量不合格的问题
    failed_items = [item for item in results['detailed_results'] if item['quality_failed']]
    if failed_items:
        print(f"\n⚠️  Quality Failed Items (first 5):")
        for i, item in enumerate(failed_items[:5], 1):
            print(f"{i}. Q: {item['question'][:100]}...")
            print(f"   Correct models: {item['correct_models_count']}/{len(MULTI_MODEL_CONFIGS)}")
    
    return results

async def run_comparison():
    """运行单模型vs多模型对比评估"""
    print("=" * 80)
    print("🔬 InteractComp Evaluation - Single Model vs Multi Model Comparison")
    print("=" * 80)
    
    # 运行单模型评估
    print("\n📋 Phase 1: Single Model Evaluations")
    single_results = await run_single_model_evaluation()
    
    # 运行多模型评估
    print("\n📋 Phase 2: Multi Model Evaluation")
    multi_results = await run_multi_model_evaluation()
    
    # 对比结果
    print("\n" + "=" * 80)
    print("📊 COMPARISON RESULTS")
    print("=" * 80)
    
    print("\n🔍 Single Model Results:")
    total_single_cost = 0
    for result in single_results:
        print(f"  {result['model']}: Score={result['avg_score']:.3f}, Cost=${result['total_cost']:.4f}")
        total_single_cost += result['total_cost']
    
    print(f"\n🤖 Multi Model Results:")
    print(f"  Quality Failed Rate: {multi_results['avg_quality_failed_rate']:.3f}")
    print(f"  Total Cost: ${multi_results['total_cost']:.4f}")
    
    print(f"\n💰 Cost Comparison:")
    print(f"  Single Models Total: ${total_single_cost:.4f}")
    print(f"  Multi Model: ${multi_results['total_cost']:.4f}")
    print(f"  Cost Ratio: {multi_results['total_cost']/total_single_cost:.2f}x")
    
    print("\n✨ Evaluation Logic:")
    print("  Single Model: Model wrong = Good annotation quality")  
    print("  Multi Model: 2+ models correct = Poor annotation quality")
    
    return {
        "single_results": single_results,
        "multi_results": multi_results
    }

async def main():
    """主函数 - 支持不同的评估模式"""
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        mode = "multi"  # 默认使用多模型评估
    
    if mode == "single":
        print("🔬 Running Single Model Evaluation Mode")
        return await run_single_model_evaluation()
    elif mode == "multi":
        print("🔬 Running Multi Model Evaluation Mode") 
        return await run_multi_model_evaluation()
    elif mode == "comparison":
        print("🔬 Running Comparison Mode")
        return await run_comparison()
    else:
        print("❌ Unknown mode. Use: single, multi, or comparison")
        print("Usage: python run_baseline.py [single|multi|comparison]")
        return None

if __name__ == "__main__":
    asyncio.run(main())