#!/usr/bin/env python3
"""
Claude Skills 格式验证脚本

验证代码是否能够正确解析按照Claude Code的Skills格式
"""

import os
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

from skills_runtime.loader import SkillLoader
from skills_runtime.router import SkillRouter
from skills_runtime.executor import get_executor


def test_skill_loading():
    """测试Skill加载功能"""
    print("🔍 测试 Skill 加载功能...")

    try:
        # 加载Skills
        skills_dir = os.path.join(os.path.dirname(__file__), "skills")
        skills = SkillLoader.load_from_directory(skills_dir)

        print(f"✅ 成功加载 {len(skills)} 个 Skills:")
        for skill_id, skill in skills.items():
            print(f"   • {skill_id}: {skill.metadata.description}")

            # 验证Claude Skills格式字段
            assert skill.apiVersion == "skills.claude.compat/v1", f"apiVersion错误: {skill.apiVersion}"
            assert skill.kind == "Skill", f"kind错误: {skill.kind}"
            assert skill.metadata.name, "metadata.name缺失"
            assert skill.metadata.version, "metadata.version缺失"
            assert skill.metadata.description, "metadata.description缺失"
            assert skill.routing, "routing配置缺失"
            assert skill.prompt, "prompt配置缺失"
            assert skill.prompt.system, "prompt.system缺失"

        print("✅ 所有 Skills 都符合 Claude Skills 规范格式")
        return True

    except Exception as e:
        print(f"❌ Skill 加载测试失败: {e}")
        return False


def test_skill_routing():
    """测试Skill路由功能"""
    print("\n🔍 测试 Skill 路由功能...")

    try:
        # 加载Skills
        skills_dir = os.path.join(os.path.dirname(__file__), "skills")
        skills = SkillLoader.load_from_directory(skills_dir)

        # 初始化路由器
        router = SkillRouter(skills)

        # 测试英文路由
        test_cases = [
            ("count file types in directory", "dir_filetype_stats"),
            ("add prefix to files", "add_filename_prefix"),
        ]

        for user_input, expected_skill in test_cases:
            result = router.route_single(user_input)
            if result and result.skill_id == expected_skill:
                print(f"✅ 路由测试通过: '{user_input}' -> {result.skill_id} (confidence: {result.confidence:.2f})")
            else:
                actual = result.skill_id if result else "None"
                print(f"❌ 路由测试失败: '{user_input}' -> 期望: {expected_skill}, 实际: {actual}")
                return False

        print("✅ Skill 路由功能正常")
        return True

    except Exception as e:
        print(f"❌ Skill 路由测试失败: {e}")
        return False


def test_skill_execution():
    """测试Skill执行功能"""
    print("\n🔍 测试 Skill 执行功能...")

    try:
        # 加载Skills
        skills_dir = os.path.join(os.path.dirname(__file__), "skills")
        skills = SkillLoader.load_from_directory(skills_dir)

        # 测试执行器存在
        for skill_id, skill in skills.items():
            if skill.execution and skill.execution.mode:
                executor = get_executor(skill.execution.mode)
                if executor:
                    print(f"✅ 执行器存在: {skill.execution.mode} -> {executor.__class__.__name__}")
                else:
                    print(f"❌ 执行器不存在: {skill.execution.mode}")
                    return False

        print("✅ Skill 执行器配置正确")
        return True

    except Exception as e:
        print(f"❌ Skill 执行测试失败: {e}")
        return False


def test_claude_skills_compatibility():
    """测试Claude Skills兼容性"""
    print("\n🔍 测试 Claude Skills 兼容性...")

    try:
        # 验证我们的数据模型是否支持Claude Skills的所有字段
        from skills_runtime.models import Skill, SkillMetadata, Routing, IOConfig, PromptConfig, ToolConfig, ExecutionPolicy

        # 创建一个完整的Claude Skills示例
        sample_skill = Skill(
            apiVersion="skills.claude.compat/v1",
            kind="Skill",
            metadata=SkillMetadata(
                name="test_skill",
                version="1.0.0",
                description="Test skill for Claude compatibility",
                author="test",
                tags=["test", "demo"]
            ),
            routing=Routing(
                triggers=["test trigger"],
                embedding_hint="Test embedding hint"
            ),
            io=IOConfig(
                inputs=[
                    {"name": "input1", "type": "string", "required": True}
                ],
                outputs=[
                    {"name": "output1", "type": "string"}
                ]
            ),
            prompt=PromptConfig(
                system="You are a test assistant",
                steps=["Step 1", "Step 2"],
                constraints=["Constraint 1"]
            ),
            tools=[
                ToolConfig(
                    name="shell",
                    description="Shell tool",
                    allowed_commands=["ls", "pwd"]
                )
            ],
            execution=ExecutionPolicy(
                mode="shell",
                allow_tool_chain=True,
                max_steps=5,
                timeout_ms=30000
            )
        )

        # 验证序列化/反序列化
        import yaml
        yaml_str = yaml.dump(sample_skill.dict())
        loaded_skill = Skill(**yaml.safe_load(yaml_str))

        assert loaded_skill.apiVersion == sample_skill.apiVersion
        assert loaded_skill.metadata.name == sample_skill.metadata.name
        assert loaded_skill.routing.triggers == sample_skill.routing.triggers

        print("✅ 数据模型完全支持 Claude Skills 规范")
        return True

    except Exception as e:
        print(f"❌ Claude Skills 兼容性测试失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("Claude Skills 兼容性验证")
    print("=" * 60)

    tests = [
        test_skill_loading,
        test_skill_routing,
        test_skill_execution,
        test_claude_skills_compatibility,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！代码完全兼容 Claude Skills 格式")
        return 0
    else:
        print(f"⚠️  有 {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
