#!/usr/bin/env python3
"""
测试Skill加载功能
"""

import sys
sys.path.insert(0, '.')

from skills_runtime.loader import SkillLoader

def test_skill_loading():
    """测试Skill加载"""
    print("Testing Skill loading...")

    try:
        # 加载Skills
        skills = SkillLoader.load_from_directory("skills")

        for skill_id, skill in skills.items():
            print(f"\nSkill: {skill_id}")
            print(f"  Description: {skill.metadata.description}")
            print(f"  Tools: {skill.tools}")

            if skill.tools:
                for i, tool in enumerate(skill.tools):
                    print(f"    Tool {i}: {type(tool)} - {tool}")
                    if hasattr(tool, 'name'):
                        print(f"      Name: {tool.name}")
                    else:
                        print(f"      Keys: {tool.keys() if isinstance(tool, dict) else 'Not a dict'}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_skill_loading()
