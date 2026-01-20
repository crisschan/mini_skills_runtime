"""
Skills Runtime - 本地 Skill 执行运行时

完全对齐 Claude Code 的 Skills 组织方式，支持：
- Skill 路由
- Skill 执行
- 完整的 Trace 记录
- 指标聚合
"""

__version__ = "1.0.0"

from skills_runtime.models import (
    SkillExecutionTrace,
    TraceStep,
    TraceLevel,
    SkillMetrics,
    ModelEvaluation,
    Skill,
    SkillMetadata,
    Routing,
    IOConfig,
    PromptConfig,
    ToolConfig,
    ExecutionPolicy,
    SkillResult,
)
from skills_runtime.loader import SkillLoader
from skills_runtime.executor import (
    SkillExecutor,
    ShellExecutor,
    PythonExecutor,
    EXECUTOR_REGISTRY,
)
from skills_runtime.router import SkillRouter
from skills_runtime.trace import TraceManager, TraceStorage
from skills_runtime.state_machine import SkillRuntime
from skills_runtime.metrics import MetricsAggregator

__all__ = [
    # Models
    "SkillExecutionTrace",
    "TraceStep",
    "TraceLevel",
    "SkillMetrics",
    "ModelEvaluation",
    "Skill",
    "SkillMetadata",
    "Routing",
    "IOConfig",
    "PromptConfig",
    "ToolConfig",
    "ExecutionPolicy",
    "SkillResult",
    # Loader
    "SkillLoader",
    # Executor
    "SkillExecutor",
    "ShellExecutor",
    "PythonExecutor",
    "EXECUTOR_REGISTRY",
    # Router
    "SkillRouter",
    # Trace
    "TraceManager",
    "TraceStorage",
    # State Machine
    "SkillRuntime",
    # Metrics
    "MetricsAggregator",
]
