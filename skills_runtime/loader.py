"""
Skill 加载器

负责从 SKILL.md 加载 Skill 定义
支持 Claude Skills 规范的 YAML 格式
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from skills_runtime.models import Skill, SkillMetadata, ExecutionPolicy


class SkillLoader:
    """Skill 加载器"""

    @staticmethod
    def load_from_markdown(skill_path: str) -> Skill:
        """
        从 SKILL.md 加载 Skill 定义
        支持 Claude Skills 规范的 YAML 格式和旧的 Markdown 格式

        Args:
            skill_path: Skill 目录路径（包含 SKILL.md）

        Returns:
            Skill 对象
        """
        skill_md_path = os.path.join(skill_path, "SKILL.md")

        if not os.path.exists(skill_md_path):
            raise FileNotFoundError(f"SKILL.md not found in {skill_path}")

        with open(skill_md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 检测格式：如果以 apiVersion 开头，则是 YAML 格式
        if content.strip().startswith("apiVersion:"):
            return SkillLoader._load_from_yaml(content, skill_path)
        else:
            return SkillLoader._load_from_legacy_markdown(content, skill_path)

    @staticmethod
    def _load_from_yaml(content: str, skill_path: str) -> Skill:
        """从 YAML 格式加载 Skill"""
        try:
            from skills_runtime.models import InputOutputField, PromptConfig, ExecutionPolicy, Routing, IOConfig, ToolConfig

            data = yaml.safe_load(content)

            # 手动转换嵌套对象以确保Pydantic正确解析
            if 'metadata' in data and data['metadata']:
                data['metadata'] = SkillMetadata(**data['metadata'])

            if 'tools' in data and data['tools']:
                data['tools'] = [ToolConfig(**tool) for tool in data['tools']]

            if 'io' in data and data['io']:
                inputs = []
                outputs = []
                if 'inputs' in data['io'] and data['io']['inputs']:
                    inputs = [InputOutputField(**inp) for inp in data['io']['inputs']]
                if 'outputs' in data['io'] and data['io']['outputs']:
                    outputs = [InputOutputField(**out) for out in data['io']['outputs']]
                data['io'] = IOConfig(inputs=inputs, outputs=outputs)

            if 'routing' in data and data['routing']:
                data['routing'] = Routing(**data['routing'])

            if 'prompt' in data and data['prompt']:
                data['prompt'] = PromptConfig(**data['prompt'])

            if 'execution' in data and data['execution']:
                data['execution'] = ExecutionPolicy(**data['execution'])

            skill = Skill(**data)
            skill.skill_path = skill_path
            return skill
        except Exception as e:
            raise ValueError(f"Failed to parse YAML Skill definition: {e}")

    @staticmethod
    def _load_from_legacy_markdown(content: str, skill_path: str) -> Skill:
        """从旧的 Markdown 格式加载 Skill（向后兼容）"""
        # 解析 Skill ID (从文件名或 SKILL.md)
        skill_id = os.path.basename(os.path.normpath(skill_path))

        # 解析各个部分
        description = SkillLoader._parse_section(content, "Description")
        when_to_use = SkillLoader._parse_section(content, "When to Use")
        when_not_to_use = SkillLoader._parse_section(content, "When NOT to Use")

        # 解析 Inputs/Outputs
        inputs_text = SkillLoader._parse_section(content, "Inputs")
        outputs_text = SkillLoader._parse_section(content, "Outputs")

        inputs = SkillLoader._parse_io_fields(inputs_text) if inputs_text else []
        outputs = SkillLoader._parse_io_fields(outputs_text) if outputs_text else []

        # 解析 Execution
        execution_text = SkillLoader._parse_section(content, "Execution")
        execution = SkillLoader._parse_execution(execution_text) if execution_text else None

        # 解析 Safety
        safety_text = SkillLoader._parse_section(content, "Safety")
        safety = SkillLoader._parse_safety(safety_text) if safety_text else {}

        # 解析触发词（从 When to Use 中提取关键词）
        triggers = SkillLoader._parse_triggers(when_to_use) if when_to_use else []

        # 构建 Skill
        skill = Skill(
            apiVersion="skills.claude.compat/v1",
            kind="Skill",
            metadata=SkillMetadata(
                name=skill_id,
                version="1.0.0",
                description=description or "",
            ),
            routing={
                "triggers": triggers,
                "embedding_hint": when_to_use or "",
            },
            io={
                "inputs": inputs,
                "outputs": outputs,
            },
            prompt={
                "system": f"Skill: {skill_id}\n\nDescription: {description}",
                "steps": [when_to_use] if when_to_use else [],
                "constraints": [when_not_to_use] if when_not_to_use else [],
            },
            execution=execution,
            skill_path=skill_path,
        )

        # 添加 safety 到 metadata
        skill.metadata.tags = safety.get("tags", [])

        return skill

    @staticmethod
    def _parse_section(content: str, section_name: str) -> Optional[str]:
        """解析指定部分"""
        pattern = rf"## {section_name}\s*\n(.*?)(?=\n## |$)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def _parse_io_fields(text: str) -> list:
        """解析输入输出字段"""
        fields = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                field_text = line[2:].strip()
                if ":" in field_text:
                    name, description = field_text.split(":", 1)
                    fields.append({
                        "name": name.strip(),
                        "type": "string",
                        "required": True,
                    })
        return fields

    @staticmethod
    def _parse_triggers(text: str) -> list:
        """
        解析触发词（从 When to Use 中提取关键词）

        对于中文，提取关键短语（前 4-6 个字符）
        """
        triggers = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                # 移除 bullet 点
                trigger = line[2:].strip()
                # 提取关键短语（前几个字符）
                if trigger:
                    # 对于中文，提取 4-6 个字作为触发词
                    key_phrase = trigger[:6] if len(trigger) > 6 else trigger
                    triggers.append(key_phrase)
        return triggers if triggers else [text]  # 如果没有列表，使用整个文本

    @staticmethod
    def _parse_execution(text: str) -> Optional[ExecutionPolicy]:
        """解析 Execution 配置"""
        exec_type = None
        entry = None

        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("- type:"):
                exec_type = line.split(":", 1)[1].strip()
            elif line.startswith("- entry:"):
                entry = line.split(":", 1)[1].strip()

        if exec_type and entry:
            return ExecutionPolicy(
                mode=exec_type,
                timeout_ms=30000,
            )
        return None

    @staticmethod
    def _parse_safety(text: str) -> Dict[str, Any]:
        """解析 Safety 配置"""
        safety = {}
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("- side_effects:"):
                side_effects = line.split(":", 1)[1].strip()
                safety["side_effects"] = side_effects
            elif line.startswith("- requires_confirmation:"):
                requires = line.split(":", 1)[1].strip().lower()
                safety["requires_confirmation"] = requires == "true"
        return safety

    @staticmethod
    def load_from_directory(skills_dir: str) -> Dict[str, Skill]:
        """
        从目录加载所有 Skills

        Args:
            skills_dir: Skills 根目录

        Returns:
            {skill_id: Skill} 字典
        """
        skills = {}
        skills_path = Path(skills_dir)

        for skill_dir in skills_path.iterdir():
            if skill_dir.is_dir():
                try:
                    skill = SkillLoader.load_from_markdown(str(skill_dir))
                    skills[skill.metadata.name] = skill
                except Exception as e:
                    print(f"Warning: Failed to load skill from {skill_dir}: {e}")

        return skills
