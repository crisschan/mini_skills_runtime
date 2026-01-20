#!/usr/bin/env python3
"""
Skills Runtime Demo

演示如何使用 Skills Runtime 执行 Skills 并查看 Trace 和 Metrics
"""

import os
import json
from skills_runtime import (
    SkillLoader,
    SkillRouter,
    SkillRuntime,
    MetricsAggregator,
    TraceStorage,
)


def print_section(title: str):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def main():
    # 初始化组件
    trace_storage = TraceStorage()
    runtime = SkillRuntime(trace_storage=trace_storage)

    print_section("Skills Runtime Demo")

    # 1. 加载 Skills
    print("1. Loading Skills from ./skills/ directory...\n")
    skills_dir = os.path.join(os.path.dirname(__file__), "skills")

    if not os.path.exists(skills_dir):
        print(f"Error: Skills directory not found: {skills_dir}")
        return

    skills = SkillLoader.load_from_directory(skills_dir)

    print(f"Loaded {len(skills)} skills:")
    for skill_id, skill in skills.items():
        print(f"  - {skill_id}: {skill.metadata.description}")

    # 2. 初始化 Router
    print("\n2. Initializing Skill Router...\n")
    router = SkillRouter(skills)

    # 3. Demo 1: dir_filetype_stats (Shell Skill)
    print_section("Demo 1: Directory File Type Statistics (Shell Skill)")

    user_input_1 = "统计 /Users/crisschan/workspace/claude_code_space 目录下的文件类型"
    print(f"User Input: {user_input_1}\n")

    # 路由
    router_result = router.route_single(user_input_1)
    if not router_result:
        print("No matching skill found.")
        return

    print(f"Routed to: {router_result.skill_id} (confidence: {router_result.confidence:.2f})\n")

    # 执行
    skill_1 = skills[router_result.skill_id]
    inputs_1 = {"1": "/Users/crisschan/workspace/claude_code_space"}

    print("Executing skill...\n")
    result_1 = runtime.execute(skill_1, user_input_1, inputs_1)

    if result_1.success:
        print("Result:")
        print(result_1.output or result_1.stdout)
    else:
        print(f"Error: {result_1.error}")

    # 显示 Trace
    trace_1 = runtime.get_trace()
    if trace_1:
        print("\nExecution Trace:")
        print(json.dumps(trace_1, indent=2))

    # 4. Demo 2: add_filename_prefix (Python Skill)
    print_section("Demo 2: Add Filename Prefix (Python Skill)")

    # 创建测试目录
    test_dir = os.path.join(os.path.dirname(__file__), "test_files")
    os.makedirs(test_dir, exist_ok=True)

    # 创建一些测试文件
    test_files = ["file1.txt", "file2.py", "file3.md"]
    for fname in test_files:
        with open(os.path.join(test_dir, fname), "w") as f:
            f.write("test content")

    user_input_2 = "给 test_files 目录下的文件添加前缀 v1_"
    print(f"User Input: {user_input_2}\n")

    # 路由
    router_result_2 = router.route_single(user_input_2)
    if not router_result_2:
        print("No matching skill found.")
        return

    print(f"Routed to: {router_result_2.skill_id} (confidence: {router_result_2.confidence:.2f})\n")

    # 执行
    skill_2 = skills[router_result_2.skill_id]
    inputs_2 = {"1": "v1_", "2": test_dir}

    print("Executing skill...\n")
    result_2 = runtime.execute(skill_2, user_input_2, inputs_2)

    if result_2.success:
        print("Result:")
        print(result_2.output or result_2.stdout)

        # 显示重命名后的文件
        print("\nFiles in test directory after renaming:")
        for fname in os.listdir(test_dir):
            if os.path.isfile(os.path.join(test_dir, fname)):
                print(f"  - {fname}")
    else:
        print(f"Error: {result_2.error}")

    # 5. 查看 Metrics
    print_section("3. Metrics Aggregation")

    metrics_aggregator = MetricsAggregator(trace_storage)

    print("All Skill Metrics:\n")
    all_metrics = metrics_aggregator.aggregate_all_skills()
    for skill_id, metrics in all_metrics.items():
        print(f"Skill: {skill_id}")
        print(f"  Calls: {metrics.calls}")
        print(f"  Success Rate: {metrics.success_rate * 100:.1f}%")
        print(f"  Avg Latency: {metrics.avg_latency_ms:.2f} ms")
        if metrics.avg_tool_latency_ms:
            print(f"  Avg Tool Latency: {metrics.avg_tool_latency_ms:.2f} ms")
        print()

    # 6. 清理
    print_section("Cleanup")
    print("Removing test files...")
    import shutil
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    print("Done!")

    print_section("Demo Complete")
    print("Skills Runtime has successfully:")
    print("  ✓ Loaded Skills from SKILL.md files")
    print("  ✓ Routed user inputs to appropriate Skills")
    print("  ✓ Executed Shell and Python Skills")
    print("  ✓ Recorded complete execution Traces")
    print("  ✓ Aggregated metrics from Traces")
    print("\n")


if __name__ == "__main__":
    main()
