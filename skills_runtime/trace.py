"""
Trace Manager

负责记录和过滤 Skill 执行 Trace
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from skills_runtime.models import (
    SkillExecutionTrace,
    TraceStep,
    TraceLevel,
)


class TraceManager:
    """Trace 管理器"""

    def __init__(self):
        self.current_trace: Optional[SkillExecutionTrace] = None
        self.step_counter = 0

    def start_trace(self, skill_id: str, skill_version: str, user_input: str) -> str:
        """
        开始一个新的 Trace

        Args:
            skill_id: Skill ID
            skill_version: Skill 版本
            user_input: 用户输入

        Returns:
            trace_id
        """
        trace_id = str(uuid.uuid4())
        request_id = str(uuid.uuid4())
        start_time = datetime.utcnow().isoformat() + "Z"

        self.current_trace = SkillExecutionTrace(
            trace_id=trace_id,
            request_id=request_id,
            skill_id=skill_id,
            skill_version=skill_version,
            start_time=start_time,
            status="INIT",
        )

        # 记录 INIT 步骤
        self.add_step(
            state="INIT",
            input={"user_input": user_input},
            output={"execution_context": "created"},
            level=TraceLevel.PROD,
        )

        return trace_id

    def add_step(
        self,
        state: str,
        input: Optional[Dict[str, Any]] = None,
        output: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        level: TraceLevel = TraceLevel.PROD,
    ) -> int:
        """
        添加一个 Trace 步骤

        Args:
            state: 状态名称
            input: 输入数据
            output: 输出数据
            metadata: 元数据
            level: Trace 级别

        Returns:
            step_id
        """
        if not self.current_trace:
            raise RuntimeError("No active trace. Call start_trace() first.")

        self.step_counter += 1
        step = TraceStep(
            step_id=self.step_counter,
            state=state,
            timestamp=datetime.utcnow().isoformat() + "Z",
            input=input,
            output=output,
            metadata=metadata or {},
            level=level,
        )

        self.current_trace.steps.append(step)
        return step.step_id

    def finish_trace(self, status: str, output: Optional[Dict[str, Any]] = None):
        """
        结束当前 Trace

        Args:
            status: 最终状态（SUCCESS, FAILED, TIMEOUT 等）
            output: 最终输出
        """
        if not self.current_trace:
            raise RuntimeError("No active trace. Call start_trace() first.")

        self.current_trace.end_time = datetime.utcnow().isoformat() + "Z"
        self.current_trace.status = status

        # 记录 FINAL 步骤
        self.add_step(
            state="FINAL",
            output=output or {},
            level=TraceLevel.PROD,
        )

    def get_trace(self) -> Optional[SkillExecutionTrace]:
        """获取当前 Trace"""
        return self.current_trace

    def filter_trace(self, level: TraceLevel) -> Optional[SkillExecutionTrace]:
        """
        过滤 Trace（根据安全级别）

        Args:
            level: 安全级别

        Returns:
            过滤后的 Trace
        """
        if not self.current_trace:
            return None

        level_order = [TraceLevel.PROD, TraceLevel.DEBUG, TraceLevel.AUDIT]
        current_level_index = level_order.index(level)

        filtered_steps = []
        for step in self.current_trace.steps:
            step_level_index = level_order.index(step.level)
            if step_level_index <= current_level_index:
                filtered_steps.append(step)

        return self.current_trace.copy(
            update={"steps": filtered_steps}
        )

    def to_dict(self) -> Optional[Dict[str, Any]]:
        """将 Trace 转换为字典"""
        if not self.current_trace:
            return None
        return self.current_trace.dict()

    def to_json(self, indent: int = 2) -> Optional[str]:
        """将 Trace 转换为 JSON 字符串"""
        trace_dict = self.to_dict()
        if trace_dict:
            return json.dumps(trace_dict, indent=indent)
        return None

    def reset(self):
        """重置 Trace 管理器"""
        self.current_trace = None
        self.step_counter = 0


class TraceStorage:
    """Trace 存储（用于 Metrics Aggregator）"""

    def __init__(self):
        self.traces: List[SkillExecutionTrace] = []

    def add_trace(self, trace: SkillExecutionTrace):
        """添加 Trace"""
        self.traces.append(trace)

    def get_traces_by_skill(self, skill_id: str) -> List[SkillExecutionTrace]:
        """获取指定 Skill 的所有 Trace"""
        return [t for t in self.traces if t.skill_id == skill_id]

    def get_all_traces(self) -> List[SkillExecutionTrace]:
        """获取所有 Trace"""
        return self.traces

    def get_trace(self, trace_id: str) -> Optional[SkillExecutionTrace]:
        """根据 trace_id 获取 Trace"""
        for trace in self.traces:
            if trace.trace_id == trace_id:
                return trace
        return None

    def clear(self):
        """清空所有 Trace"""
        self.traces = []
