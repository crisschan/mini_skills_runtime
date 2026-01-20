"""
核心数据模型定义

严格按照设计文档实现的数据模型
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Protocol
from pydantic import BaseModel, Field


class TraceLevel(str, Enum):
    """Trace 安全分级"""
    PROD = "prod"     # 生产最小集
    DEBUG = "debug"   # 开发调试
    AUDIT = "audit"   # 合规审计


class TraceStep(BaseModel):
    """Trace 步骤"""
    step_id: int
    state: str
    timestamp: str

    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    level: TraceLevel = TraceLevel.PROD


class SkillExecutionTrace(BaseModel):
    """Skill 执行 Trace"""
    trace_id: str
    request_id: str

    skill_id: str
    skill_version: str

    start_time: str
    end_time: Optional[str] = None
    status: str

    steps: List[TraceStep] = []


class SkillMetadata(BaseModel):
    """Skill 元数据"""
    name: str
    version: str
    description: str
    author: Optional[str] = None
    tags: Optional[List[str]] = None


class Routing(BaseModel):
    """Routing 配置"""
    triggers: List[str] = []
    embedding_hint: Optional[str] = None


class InputOutputField(BaseModel):
    """输入输出字段"""
    name: str
    type: str
    required: bool = False


class IOConfig(BaseModel):
    """IO 配置"""
    inputs: List[InputOutputField] = []
    outputs: List[InputOutputField] = []


class PromptConfig(BaseModel):
    """Prompt 配置"""
    system: str
    steps: Optional[List[str]] = None
    constraints: Optional[List[str]] = None


class ToolConfig(BaseModel):
    """工具配置"""
    name: str
    description: Optional[str] = None
    read_only: bool = False
    allowed_commands: Optional[List[str]] = None


class ExecutionPolicy(BaseModel):
    """执行策略"""
    mode: str = "single-shot"
    allow_tool_chain: bool = True
    max_steps: int = 5
    timeout_ms: int = 30000


class Skill(BaseModel):
    """Skill 定义"""
    apiVersion: str = "skills.claude.compat/v1"
    kind: str = "Skill"
    metadata: SkillMetadata
    routing: Optional[Routing] = None
    io: Optional[IOConfig] = None
    prompt: Optional[PromptConfig] = None
    tools: Optional[List[ToolConfig]] = None
    execution: Optional[ExecutionPolicy] = None

    # 文件路径
    skill_path: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class SkillResult(BaseModel):
    """Skill 执行结果"""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelEvaluation(BaseModel):
    """模型评估结果"""
    skill_id: str
    model: str
    success_rate: float
    p95_latency_ms: float
    avg_cost: float


class SkillMetrics(BaseModel):
    """Skill 指标"""
    skill_id: str
    window_start: str
    window_end: str

    calls: int
    success_rate: float
    avg_latency_ms: float

    avg_infer_latency_ms: Optional[float]
    avg_tool_latency_ms: Optional[float]
    avg_prompt_tokens: Optional[float]
