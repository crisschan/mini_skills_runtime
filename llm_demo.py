#!/usr/bin/env python3
"""
LLM Skills Runtime Demo

Demonstrates Skills Runtime's LLM inference capabilities using LangChain + Ollama
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from skills_runtime import (
    SkillLoader,
    SkillRouter,
    LLMSkillRuntime,
    MetricsAggregator,
    TraceStorage,
    LLMConfig,
)


def print_section(title: str):
    """Print section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def check_ollama_running():
    """Check if Ollama is running locally"""
    try:
        import requests
        # Check local Ollama service
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            model_names = [m.get("name", "") for m in models if m.get("name")]
            # Only return True if we have actual local models
            if model_names:
                return True, model_names
    except:
        pass
    return False, []


def main():
    print_section("LLM Skills Runtime Demo")

    # Check Ollama
    print("Checking Ollama service...")
    ollama_running, models = check_ollama_running()

    if not ollama_running:
        print("Error: Ollama service is not running!")
        print("\nPlease start Ollama first:")
        print("  ollama serve")
        print("\nDownload default model (if not already):")
        print("  ollama pull qwen3:8b")
        return

    print(f"Ollama service running")
    print(f"Available models: {', '.join(models)}")

    # Configure LLM
    default_model = "qwen3:8b"
    if default_model in models:
        print(f"Using default model: {default_model}")
        llm_config = LLMConfig(model=default_model)
    else:
        # Use first available model
        selected_model = models[0] if models else default_model
        print(f"Using model: {selected_model}")
        llm_config = LLMConfig(model=selected_model)

    # Initialize components
    trace_storage = TraceStorage()
    runtime = LLMSkillRuntime(llm_config=llm_config, trace_storage=trace_storage)

    # print_section("1. Test Simple Chat (No Skill)")

    # print("User input: Hello, please introduce yourself")
    # try:
    #     response = runtime.simple_chat(
    #         user_input="Hello, please introduce yourself",
    #         system_prompt="You are a personal AI assistant named tinyO.",
    #     )
    #     print(f"AI response: {response}")
    # except Exception as e:
    #     print(f"LLM chat failed: {e}")
    #     print("Skipping LLM demo - continuing with basic Skills functionality...")
    #     print_section("2. Load Skills")
    #     # Skip to skills loading
    #     skills_dir = os.path.join(os.path.dirname(__file__), "skills")
    #     if not os.path.exists(skills_dir):
    #         print(f"Error: Skills directory not found: {skills_dir}")
    #         return

    #     skills = SkillLoader.load_from_directory(skills_dir)
    #     print(f"Loaded {len(skills)} skills:")
    #     for skill_id, skill in skills.items():
    #         print(f"  - {skill_id}: {skill.metadata.description}")

    #     print("\nNote: LLM features are not available. Run 'ollama serve' and pull a model to enable LLM demos.")
    #     return

    print_section("2. Load Skills")

    skills_dir = os.path.join(os.path.dirname(__file__), "skills")

    if not os.path.exists(skills_dir):
        print(f"Error: Skills directory not found: {skills_dir}")
        return

    skills = SkillLoader.load_from_directory(skills_dir)

    print(f"Loaded {len(skills)} skills:")
    for skill_id, skill in skills.items():
        print(f"  - {skill_id}: {skill.metadata.description}")

    # Initialize Router
    router = SkillRouter(skills)

    print_section("3. Demo 1: Use LLM to Count File Types")

    user_input_1 = "Please help me count file tpyes what types of files are in the current directory"
    print(f"User input: {user_input_1}\n")

    # Route
    router_result = router.route_single(user_input_1)
    if not router_result:
        print("No matching skill found")
        return

    print(f"Routed to: {router_result.skill_id} (confidence: {router_result.confidence:.2f})\n")

    # Execute
    skill_1 = skills[router_result.skill_id]
    inputs_1 = {}

    print("Executing skill...\n")
    result_1 = runtime.execute(skill_1, user_input_1, inputs_1)

    if result_1.success:
        print("Result:")
        print(result_1.output)

        # Show Trace
        trace_1 = trace_storage.get_trace(result_1.trace_id)
        if trace_1:
            print("\nExecution summary:")
            print(f"  Status: {trace_1.status}")
            print(f"  Number of steps: {len(trace_1.steps)}")

            # Show INFER step details
            for step in trace_1.steps:
                if step.state == 'INFER':
                    print(f"  Inference model: {step.metadata.get('model')}")
                    print(f"  Inference latency: {step.metadata.get('latency_ms', 0):.2f}ms")
                    print(f"  Tool calls: {step.metadata.get('tool_calls', 0)}")
    else:
        print(f"Error: {result_1.error}")

    print_section("4. Demo 2: Use LLM to Add File Prefix")

    # Create test directory
    test_dir = os.path.join(os.path.dirname(__file__), "llm_test_files")
    os.makedirs(test_dir, exist_ok=True)

    # Create test files
    test_files = ["document.txt", "code.py", "note.md"]
    for fname in test_files:
        with open(os.path.join(test_dir, fname), "w") as f:
            f.write("test content")

    user_input_2 = f"Please add the prefix backup_ to files in the {test_dir} directory"
    print(f"User input: {user_input_2}\n")

    # Route
    router_result_2 = router.route_single(user_input_2)
    if not router_result_2:
        print("No matching skill found")
        return

    print(f"Routed to: {router_result_2.skill_id} (confidence: {router_result_2.confidence:.2f})\n")

    # Execute
    skill_2 = skills[router_result_2.skill_id]
    inputs_2 = {}

    print("Executing skill...\n")
    result_2 = runtime.execute(skill_2, user_input_2, inputs_2)

    if result_2.success:
        print("Result:")
        print(result_2.output)

        # Show renamed files
        print("\nRenamed files:")
        for fname in os.listdir(test_dir):
            if os.path.isfile(os.path.join(test_dir, fname)):
                print(f"  - {fname}")
        
        # Show Trace
        trace_2 = trace_storage.get_trace(result_2.trace_id)
        if trace_2:
            print("\nExecution summary:")
            print(f"  Status: {trace_2.status}")
            print(f"  Number of steps: {len(trace_2.steps)}")

            # Show INFER step details
            for step in trace_2.steps:
                if step.state == 'INFER':
                    print(f"  Inference model: {step.metadata.get('model')}")
                    print(f"  Inference latency: {step.metadata.get('latency_ms', 0):.2f}ms")
                    print(f"  Tool calls: {step.metadata.get('tool_calls', 0)}")
    else:
        print(f"Error: {result_2.error}")

    print_section("5. Metrics Aggregation")

    print("Execution metrics for all skills:\n")
    metrics_aggregator = MetricsAggregator(trace_storage)
    all_metrics = metrics_aggregator.aggregate_all_skills()

    for skill_id, metrics in all_metrics.items():
        print(f"Skill: {skill_id}")
        print(f"  Calls: {metrics.calls}")
        print(f"  Success rate: {metrics.success_rate * 100:.1f}%")
        print(f"  Average latency: {metrics.avg_latency_ms:.2f} ms")
        if metrics.avg_tool_latency_ms:
            print(f"  Average tool latency: {metrics.avg_tool_latency_ms:.2f} ms")
        print()

    # Cleanup
    print_section("Cleanup")

    print("Removing test files...")
    import shutil
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    print("Done!")

    print_section("Demo Complete")

    print("Skills Runtime has successfully demonstrated:")
    print("  ✓ Using LangChain + Ollama for LLM inference")
    print("  ✓ LLM understands user intent and decides tool calls")
    print("  ✓ Shell and Python Skills execution")
    print("  ✓ Complete execution Trace recording")
    print("  ✓ Metrics aggregation analysis")
    print()


if __name__ == "__main__":
    main()
