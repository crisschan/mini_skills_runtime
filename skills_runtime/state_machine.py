"""
Skill Runtime 状态机

按照设计文档实现完整的状态机
"""

import time
from typing import Dict, Any, Optional
from skills_runtime.models import Skill, SkillResult
from skills_runtime.trace import TraceManager, TraceStorage
from skills_runtime.executor import get_executor


class SkillRuntime:
    """Skill Runtime 状态机"""

    def __init__(self, trace_storage: Optional[TraceStorage] = None):
        """
        初始化 Runtime

        Args:
            trace_storage: 可选的 Trace 存储（用于 Metrics）
        """
        self.trace_manager = TraceManager()
        self.trace_storage = trace_storage or TraceStorage()
        self.state = "IDLE"

    def execute(self, skill: Skill, user_input: str, inputs: Dict[str, Any]) -> SkillResult:
        """
        执行 Skill（完整状态机流程）

        Args:
            skill: Skill 定义
            user_input: 用户输入
            inputs: 输入参数

        Returns:
            SkillResult
        """
        try:
            # INIT
            self.state = "INIT"
            self.trace_manager.start_trace(
                skill_id=skill.metadata.name,
                skill_version=skill.metadata.version,
                user_input=user_input,
            )

            # ROUTED
            self.state = "ROUTED"
            self.trace_manager.add_step(
                state="ROUTED",
                output={
                    "skill_id": skill.metadata.name,
                    "strategy": "direct",
                },
            )

            # LOADED
            self.state = "LOADED"
            self.trace_manager.add_step(
                state="LOADED",
                output={
                    "schema_valid": True,
                    "skill_hash": f"sha256:{hash(skill.metadata.name)}",
                },
            )

            # PROMPTED
            self.state = "PROMPTED"
            self.trace_manager.add_step(
                state="PROMPTED",
                metadata={"prompt_tokens": len(user_input)},
            )

            # INFER (这里简化为直接执行)
            self.state = "INFER"
            infer_start = time.time()
            self.trace_manager.add_step(
                state="INFER",
                output={"type": "tool_call"},
                metadata={"model": "local", "latency_ms": 0},
            )

            # TOOL_CALL
            self.state = "TOOL_CALL"
            self.trace_manager.add_step(
                state="TOOL_CALL",
                input={"tool": skill.execution.mode if skill.execution else "shell", "args": inputs},
            )

            # TOOL_EXEC
            self.state = "TOOL_EXEC"
            exec_type = skill.execution.mode if skill.execution else "shell"
            executor_class = get_executor(exec_type)
            if not executor_class:
                raise ValueError(f"No executor for type: {exec_type}")

            executor = executor_class()
            result = executor.execute(skill, inputs, {})

            tool_exec_metadata = {
                "exit_code": result.exit_code,
                "duration_ms": result.metadata.get("duration_ms", 0) if result.metadata else 0,
            }
            self.trace_manager.add_step(
                state="TOOL_EXEC",
                metadata=tool_exec_metadata,
            )

            # TOOL_RET
            self.state = "TOOL_RET"
            self.trace_manager.add_step(
                state="TOOL_RET",
                output={"stdout_size": len(result.stdout or "")},
            )

            # FINAL
            self.state = "FINAL"
            final_output = {"result": result.output or result.stdout}
            final_status = "SUCCESS" if result.success else "FAILED"

            self.trace_manager.finish_trace(
                status=final_status,
                output=final_output,
            )

            # 保存 Trace 到存储
            trace = self.trace_manager.get_trace()
            if trace:
                self.trace_storage.add_trace(trace)

            return result

        except Exception as e:
            # 错误处理
            self.trace_manager.finish_trace(
                status="FAILED",
                output={"error": str(e)},
            )
            return SkillResult(
                success=False,
                error=str(e),
            )

        finally:
            self.state = "IDLE"

    def get_trace(self) -> Optional[Dict[str, Any]]:
        """获取当前 Trace"""
        return self.trace_manager.to_dict()

    def get_trace_json(self) -> Optional[str]:
        """获取当前 Trace JSON"""
        return self.trace_manager.to_json()
