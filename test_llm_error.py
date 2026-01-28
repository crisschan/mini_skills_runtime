#!/usr/bin/env python3
"""
测试LLM错误重现
"""

import sys
sys.path.insert(0, '.')

from skills_runtime.loader import SkillLoader
from skills_runtime.llm_state_machine import LLMSkillRuntime
from skills_runtime.llm import LLMConfig

def test_llm_error():
    """测试LLM错误重现"""
    print("Testing LLM error reproduction...")

    try:
        # 加载Skills
        skills = SkillLoader.load_from_directory("skills")
        skill = skills["dir_filetype_stats"]

        print(f"Loaded skill: {skill.metadata.name}")
        print(f"Tools: {skill.tools}")

        # 创建LLM配置 - 使用一个不存在的模型来触发错误
        llm_config = LLMConfig(model="nonexistent-model")

        # 创建Runtime
        runtime = LLMSkillRuntime(llm_config=llm_config)

        # 注册工具
        runtime.register_skill_tool(skill)

        print("Skill tool registered successfully")

        # 测试执行
        inputs = {"dir": "."}
        result = runtime.execute(skill, "count file types", inputs)

        print(f"Execution result: {result.success}")
        if not result.success:
            print(f"Error: {result.error}")

    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm_error()
