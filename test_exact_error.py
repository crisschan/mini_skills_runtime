#!/usr/bin/env python3
"""
精确重现用户遇到的错误
"""

import sys
sys.path.insert(0, '.')

from skills_runtime.loader import SkillLoader
from skills_runtime.llm_state_machine import LLMSkillRuntime
from skills_runtime.llm import LLMConfig

def test_exact_error():
    """精确重现错误"""
    print("Testing exact error reproduction...")

    try:
        # 加载Skills
        skills = SkillLoader.load_from_directory("skills")
        skill = skills["dir_filetype_stats"]

        print(f"Loaded skill: {skill.metadata.name}")
        print(f"Skill tools type: {type(skill.tools)}")
        if skill.tools:
            print(f"First tool type: {type(skill.tools[0])}")
            print(f"First tool: {skill.tools[0]}")

        # 创建LLM配置 - 使用实际可用的模型
        llm_config = LLMConfig(model="qwen3:8b")

        # 创建Runtime
        runtime = LLMSkillRuntime(llm_config=llm_config)

        # 注册工具
        print("Registering skill tools...")
        runtime.register_skill_tool(skill)
        print("Skill tools registered successfully")

        # 测试执行 - 使用与llm_demo.py相同的输入
        inputs = {"dir": "/Users/crisschan/workspace/claude_code_space"}
        user_input = "Please help me count file tpyes what types of files are in the current directory"

        print(f"Executing with input: {user_input}")
        print(f"Inputs: {inputs}")

        result = runtime.execute(skill, user_input, inputs)

        print(f"Execution result: {result.success}")
        if not result.success:
            print(f"Error: {result.error}")

    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_exact_error()
