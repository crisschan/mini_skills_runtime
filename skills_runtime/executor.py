"""
Skill Executor

支持不同类型的 Skill 执行：Shell, Python
"""

import os
import subprocess
import time
from typing import Dict, Any, Optional
from skills_runtime.models import Skill, SkillResult


EXECUTOR_REGISTRY = {}


class SkillExecutor:
    """Skill 执行器基类（协议）"""

    def execute(self, skill: Skill, inputs: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        """
        执行 Skill

        Args:
            skill: Skill 定义
            inputs: 输入参数
            context: 执行上下文

        Returns:
            SkillResult
        """
        raise NotImplementedError


class ShellExecutor(SkillExecutor):
    """Shell Script 执行器"""

    def execute(self, skill: Skill, inputs: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        """
        执行 Shell Script

        Args:
            skill: Skill 定义
            inputs: 输入参数
            context: 执行上下文

        Returns:
            SkillResult
        """
        if not skill.skill_path:
            return SkillResult(
                success=False,
                error="Skill path not found",
            )

        # 查找脚本路径
        if skill.execution and skill.execution.mode == "shell":
            script_path = os.path.join(skill.skill_path, "scripts")
            script_files = os.listdir(script_path)
            if script_files:
                script_file = os.path.join(script_path, script_files[0])
            else:
                return SkillResult(
                    success=False,
                    error="No script file found",
                )
        else:
            # 默认查找 SKILL.md 中的 entry
            entry = skill.execution.mode if skill.execution else "script.sh"
            script_file = os.path.join(skill.skill_path, entry)

        if not os.path.exists(script_file):
            return SkillResult(
                success=False,
                error=f"Script not found: {script_file}",
            )

        # 构建命令参数
        args = [inputs.get(str(i), "") for i in range(1, len(inputs) + 1)]
        if not args:
            # 如果没有明确索引，使用值列表
            args = list(inputs.values())

        cmd = [script_file] + [str(arg) for arg in args]

        # 执行脚本
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=skill.execution.timeout_ms / 1000 if skill.execution else 30,
            )
            duration_ms = (time.time() - start_time) * 1000

            return SkillResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.stderr else None,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                metadata={
                    "duration_ms": duration_ms,
                    "cmd": " ".join(cmd),
                },
            )
        except subprocess.TimeoutExpired:
            return SkillResult(
                success=False,
                error="Script execution timeout",
            )
        except Exception as e:
            return SkillResult(
                success=False,
                error=str(e),
            )


class PythonExecutor(SkillExecutor):
    """Python Code 执行器"""

    def execute(self, skill: Skill, inputs: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        """
        执行 Python Script

        Args:
            skill: Skill 定义
            inputs: 输入参数
            context: 执行上下文

        Returns:
            SkillResult
        """
        if not skill.skill_path:
            return SkillResult(
                success=False,
                error="Skill path not found",
            )

        # 查找脚本路径
        script_path = os.path.join(skill.skill_path, "scripts")
        script_files = os.listdir(script_path)
        if script_files:
            script_file = os.path.join(script_path, script_files[0])
        else:
            return SkillResult(
                success=False,
                error="No script file found",
            )

        if not os.path.exists(script_file):
            return SkillResult(
                success=False,
                error=f"Script not found: {script_file}",
            )

        # 构建命令参数
        args = [inputs.get(str(i), "") for i in range(1, len(inputs) + 1)]
        if not args:
            args = list(inputs.values())

        cmd = ["python3", script_file] + [str(arg) for arg in args]

        # 执行脚本
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=skill.execution.timeout_ms / 1000 if skill.execution else 30,
                cwd=skill.skill_path,
            )
            duration_ms = (time.time() - start_time) * 1000

            return SkillResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.stderr else None,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                metadata={
                    "duration_ms": duration_ms,
                    "cmd": " ".join(cmd),
                },
            )
        except subprocess.TimeoutExpired:
            return SkillResult(
                success=False,
                error="Script execution timeout",
            )
        except Exception as e:
            return SkillResult(
                success=False,
                error=str(e),
            )


# 注册执行器
EXECUTOR_REGISTRY["shell"] = ShellExecutor
EXECUTOR_REGISTRY["python"] = PythonExecutor


def get_executor(execution_type: str) -> Optional[SkillExecutor]:
    """根据类型获取执行器"""
    return EXECUTOR_REGISTRY.get(execution_type)
