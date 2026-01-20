"""
Metrics Aggregator

负责从 Trace 中提取和聚合指标
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from skills_runtime.models import (
    SkillExecutionTrace,
    SkillMetrics,
    TraceLevel,
)
from skills_runtime.trace import TraceStorage


class MetricsAggregator:
    """指标聚合器"""

    def __init__(self, trace_storage: TraceStorage):
        """
        初始化聚合器

        Args:
            trace_storage: Trace 存储
        """
        self.trace_storage = trace_storage

    def aggregate_skill_metrics(
        self,
        skill_id: str,
        window_start: Optional[str] = None,
        window_end: Optional[str] = None,
    ) -> SkillMetrics:
        """
        聚合 Skill 指标

        Args:
            skill_id: Skill ID
            window_start: 时间窗口开始（ISO 格式）
            window_end: 时间窗口结束（ISO 格式）

        Returns:
            SkillMetrics
        """
        traces = self.trace_storage.get_traces_by_skill(skill_id)

        # 过滤时间窗口
        if window_start or window_end:
            traces = self._filter_by_window(traces, window_start, window_end)

        # 过滤 PROD 级 Trace
        traces = [t for t in traces if self._is_prod_trace(t)]

        if not traces:
            # 返回空指标
            return SkillMetrics(
                skill_id=skill_id,
                window_start=window_start or "",
                window_end=window_end or "",
                calls=0,
                success_rate=0.0,
                avg_latency_ms=0.0,
                avg_infer_latency_ms=None,
                avg_tool_latency_ms=None,
                avg_prompt_tokens=None,
            )

        # 计算指标
        calls = len(traces)
        successful_traces = [t for t in traces if t.status == "SUCCESS"]
        success_rate = len(successful_traces) / calls

        # 计算延迟
        latencies = []
        infer_latencies = []
        tool_latencies = []

        for trace in traces:
            # 总延迟
            if trace.start_time and trace.end_time:
                start = datetime.fromisoformat(trace.start_time.replace("Z", ""))
                end = datetime.fromisoformat(trace.end_time.replace("Z", ""))
                latencies.append((end - start).total_seconds() * 1000)

            # INFER 延迟
            for step in trace.steps:
                if step.state == "INFER" and "latency_ms" in step.metadata:
                    infer_latencies.append(step.metadata["latency_ms"])
                elif step.state == "TOOL_EXEC" and "duration_ms" in step.metadata:
                    tool_latencies.append(step.metadata["duration_ms"])

        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        avg_infer_latency = sum(infer_latencies) / len(infer_latencies) if infer_latencies else None
        avg_tool_latency = sum(tool_latencies) / len(tool_latencies) if tool_latencies else None

        # 计算 prompt tokens
        prompt_tokens = []
        for trace in traces:
            for step in trace.steps:
                if step.state == "PROMPTED" and "prompt_tokens" in step.metadata:
                    prompt_tokens.append(step.metadata["prompt_tokens"])
        avg_prompt_tokens = sum(prompt_tokens) / len(prompt_tokens) if prompt_tokens else None

        return SkillMetrics(
            skill_id=skill_id,
            window_start=window_start or "",
            window_end=window_end or "",
            calls=calls,
            success_rate=success_rate,
            avg_latency_ms=avg_latency,
            avg_infer_latency_ms=avg_infer_latency,
            avg_tool_latency_ms=avg_tool_latency,
            avg_prompt_tokens=avg_prompt_tokens,
        )

    def aggregate_all_skills(self) -> Dict[str, SkillMetrics]:
        """
        聚合所有 Skill 的指标

        Returns:
            {skill_id: SkillMetrics} 字典
        """
        metrics = {}

        # 获取所有唯一的 skill_id
        skill_ids = set()
        for trace in self.trace_storage.get_all_traces():
            skill_ids.add(trace.skill_id)

        for skill_id in skill_ids:
            metrics[skill_id] = self.aggregate_skill_metrics(skill_id)

        return metrics

    def _filter_by_window(
        self,
        traces: List[SkillExecutionTrace],
        window_start: Optional[str],
        window_end: Optional[str],
    ) -> List[SkillExecutionTrace]:
        """过滤时间窗口内的 Trace"""
        filtered = traces

        if window_start:
            start = datetime.fromisoformat(window_start.replace("Z", ""))
            filtered = [
                t for t in filtered
                if t.start_time and datetime.fromisoformat(t.start_time.replace("Z", "")) >= start
            ]

        if window_end:
            end = datetime.fromisoformat(window_end.replace("Z", ""))
            filtered = [
                t for t in filtered
                if t.start_time and datetime.fromisoformat(t.start_time.replace("Z", "")) <= end
            ]

        return filtered

    def _is_prod_trace(self, trace: SkillExecutionTrace) -> bool:
        """检查是否为 PROD 级 Trace"""
        # Metrics 只依赖 PROD 视图
        for step in trace.steps:
            if step.level == TraceLevel.DEBUG or step.level == TraceLevel.AUDIT:
                return False
        return True

    def get_model_metrics(self, skill_id: str, model: str) -> Dict[str, Any]:
        """
        获取特定模型的指标

        Args:
            skill_id: Skill ID
            model: 模型名称

        Returns:
            模型指标字典
        """
        traces = self.trace_storage.get_traces_by_skill(skill_id)

        # 过滤使用该模型的 Trace
        model_traces = []
        for trace in traces:
            for step in trace.steps:
                if step.state == "INFER" and step.metadata.get("model") == model:
                    model_traces.append(trace)
                    break

        if not model_traces:
            return {
                "skill_id": skill_id,
                "model": model,
                "calls": 0,
                "success_rate": 0.0,
            }

        calls = len(model_traces)
        successful = sum(1 for t in model_traces if t.status == "SUCCESS")
        success_rate = successful / calls

        # 计算 P95 延迟
        latencies = []
        for trace in model_traces:
            if trace.start_time and trace.end_time:
                start = datetime.fromisoformat(trace.start_time.replace("Z", ""))
                end = datetime.fromisoformat(trace.end_time.replace("Z", ""))
                latencies.append((end - start).total_seconds() * 1000)

        latencies.sort()
        p95_index = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_index] if latencies else 0.0

        return {
            "skill_id": skill_id,
            "model": model,
            "calls": calls,
            "success_rate": success_rate,
            "p95_latency_ms": p95_latency,
        }

    def get_tool_metrics(self, tool_name: str) -> Dict[str, Any]:
        """
        获取工具指标

        Args:
            tool_name: 工具名称

        Returns:
            工具指标字典
        """
        traces = self.trace_storage.get_all_traces()

        tool_calls = 0
        tool_successes = 0
        tool_latencies = []

        for trace in traces:
            for step in trace.steps:
                if step.state == "TOOL_CALL" and step.input and step.input.get("tool") == tool_name:
                    tool_calls += 1

                    # 查找对应的 TOOL_EXEC 步骤
                    exec_step = next(
                        (s for s in trace.steps if s.step_id == step.step_id + 1 and s.state == "TOOL_EXEC"),
                        None
                    )
                    if exec_step:
                        if exec_step.metadata.get("exit_code") == 0:
                            tool_successes += 1
                        if "duration_ms" in exec_step.metadata:
                            tool_latencies.append(exec_step.metadata["duration_ms"])

        success_rate = tool_successes / tool_calls if tool_calls > 0 else 0.0

        # 计算 P95 延迟
        tool_latencies.sort()
        p95_index = int(len(tool_latencies) * 0.95)
        p95_latency = tool_latencies[p95_index] if tool_latencies else 0.0

        return {
            "tool": tool_name,
            "calls": tool_calls,
            "success_rate": success_rate,
            "p95_latency_ms": p95_latency,
        }
