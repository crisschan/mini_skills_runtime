# Skills Runtime

本地 Skill 执行运行时 - 完全对齐 Claude Code 的 Skills 组织方式

## 特性

- **Skill 定义**: 通过 SKILL.md 定义 Skill，支持结构化指令、输入输出、安全配置
- **Skill 路由**: 基于关键词匹配的智能路由系统（可扩展为 embedding 匹配）
- **Skill 执行**: 支持 Shell 和 Python 两种执行类型，可轻松扩展
- **LLM 推理**: 使用 LangChain + Ollama 实现真正的 LLM 推理和工具调用
- **完整 Trace**: 记录每次执行的完整状态转换，支持 DEBUG/AUDIT/PROD 三级过滤
- **指标聚合**: 自动从 Trace 中提取延迟、成功率、工具调用等指标

## 项目结构

```
skills_runtime/
├── skills_runtime/           # 核心包
│   ├── __init__.py          # 包导出
│   ├── models.py            # 数据模型
│   ├── loader.py            # Skill 加载器
│   ├── router.py            # Skill 路由器
│   ├── executor.py          # Skill 执行器
│   ├── trace.py             # Trace 管理器
│   ├── metrics.py           # 指标聚合器
│   ├── state_machine.py     # 状态机实现（基础版）
│   ├── llm.py              # LLM 管理器（LangChain + Ollama）
│   └── llm_state_machine.py # LLM 状态机（推理版）
├── skills/                  # Skills 目录
│   ├── dir_filetype_stats/  # Shell Skill 示例
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── count_filetypes.sh
│   └── add_filename_prefix/ # Python Skill 示例
│       ├── SKILL.md
│       └── scripts/
│           └── add_prefix.py
├── demo.py                  # 基础 demo（无 LLM）
├── llm_demo.py             # LLM demo（需要 Ollama）
├── requirements.txt
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 Ollama（用于 LLM 功能）

```bash
# 启动 Ollama 服务
ollama serve

# 在另一个终端下载模型
ollama pull qwen2.5:7b
```

### 3. 运行 Demo

#### 基础 Demo（无 LLM）

```bash
python demo.py
```

展示：
1. 加载 Skills
2. 路由用户输入到合适的 Skill
3. 执行 Shell 和 Python Skills（直接执行，无 LLM）
4. 查看完整执行 Trace
5. 聚合并显示指标

#### LLM Demo（需要 Ollama）

```bash
python llm_demo.py
```

展示：
1. 使用 LLM 进行简单对话
2. 加载 Skills
3. LLM 理解用户意图并路由到合适的 Skill
4. LLM 决定是否使用工具以及如何调用
5. 执行工具并返回结果
6. 完整的执行 Trace（包含 LLM 推理）
7. 指标聚合分析

## LLM 集成

### LLM 配置

```python
from skills_runtime import LLMConfig, LLMSkillRuntime

# 创建 LLM 配置
llm_config = LLMConfig(
    model="qwen2.5:7b",  # Ollama 模型名称
    temperature=0.7,          # 温度参数
    base_url=None,             # Ollama API 地址（默认 localhost:11434）
)

# 创建 LLM Runtime
runtime = LLMSkillRuntime(llm_config=llm_config)
```

### 简单对话

```python
# 不使用 Skill 的简单对话
response = runtime.simple_chat(
    user_input="你好，请介绍一下自己",
    system_prompt="你是一个有帮助的 AI 助手。"
)
print(response)
```

### Skill 执行（带 LLM 推理）

```python
from skills_runtime import SkillLoader, LLMSkillRuntime

# 加载 Skills
skills = SkillLoader.load_from_directory("skills/")

# 创建 LLM Runtime
runtime = LLMSkillRuntime()

# 执行 Skill（LLM 会决定如何处理）
skill = skills["dir_filetype_stats"]
result = runtime.execute(
    skill=skill,
    user_input="请帮我统计当前目录下的文件类型",
    inputs={"dir": "/path/to/directory"}
)
```

### 工具调用

LLM Runtime 支持工具调用。当 Skill 定义了 `tools` 配置时，LLM 可以：

1. 理解用户意图
2. 决定是否需要使用工具
3. 自动调用工具并传递参数
4. 处理工具返回的结果
5. 生成最终回复

## 如何创建自定义 Skill

### 1. 创建目录结构

```bash
mkdir -p skills/my_skill/scripts
```

### 2. 编写 SKILL.md

```markdown
# Skill: my_skill

## Description
一句话描述 Skill 做什么

## When to Use
明确的使用场景

## When NOT to Use
明确的禁止场景

## Inputs
- param1: 参数1描述

## Outputs
- result1: 输出1描述

## Execution
- type: shell|python
- entry: scripts/my_script.py

## Safety
- side_effects: none|filesystem|network|system
- requires_confirmation: true|false
```

### 3. 编写脚本

根据 `type` 选择 Shell 或 Python 脚本，放在 `scripts/` 目录下。

### 4. 重新加载 Skills

Runtime 会在运行时自动加载新 Skills。

## 状态机

### 基础状态机（无 LLM）

```
INIT → ROUTED → LOADED → PROMPTED → INFER → TOOL_CALL → TOOL_EXEC → TOOL_RET → INFER → FINAL
```

### LLM 状态机（带推理）

```
INIT → ROUTED → LOADED → PROMPTED → INFER（LLM 推理） → [工具调用循环] → FINAL
```

每个状态都会记录 Trace，可用于调试、审计和指标分析。

## Trace 级别

- **PROD**: 生产最小集，记录状态、时间、结果摘要
- **DEBUG**: 开发调试，记录 Prompt 元信息、模型选择
- **AUDIT**: 合规审计，记录 Tool 调用、参数 hash

## 指标

Metrics Aggregator 自动从 Trace 中提取：

- **Latency**: 总延迟、推理延迟、工具执行延迟
- **Model**: 模型调用次数、成功率
- **Tool**: 工具调用次数、成功率、P95 延迟
- **Reliability**: 成功率、错误率、超时率

## 扩展新 Skill 类型

1. 在 `executor.py` 中创建新的 Executor 类
2. 实现 `execute` 方法
3. 注册到 `EXECUTOR_REGISTRY`

```python
EXECUTOR_REGISTRY["my_type"] = MyTypeExecutor
```

无需修改 Routing、Trace 或 Metrics 的任何逻辑。

## 技术栈

- **LangChain**: LLM 框架，提供统一的 LLM 接口
- **Ollama**: 本地 LLM 推理引擎
- **Pydantic**: 数据验证和序列化
- **Python 3.8+**: 运行时要求

## 默认模型

- **qwen2.5:7b**: 默认推荐模型，平衡性能和资源消耗

可通过 `LLMConfig` 修改为其他 Ollama 模型，如：
- llama3:8b
- mistral:7b
- codellama:7b
- 等
