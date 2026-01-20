# mini Skills Runtime

本地 Skill 执行运行时 - 完全对齐 Claude Code 的 Skills 组织方式

## 特性

- **Skill 定义**: 通过 SKILL.md 定义 Skill，支持结构化指令、输入输出、安全配置
- **Skill 路由**: 基于关键词匹配的智能路由系统（可扩展为 embedding 匹配）
- **Skill 执行**: 支持 Shell 和 Python 两种执行类型，可轻松扩展
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
│   └── state_machine.py     # 状态机实现
├── skills/                  # Skills 目录
│   ├── dir_filetype_stats/  # Shell Skill 示例
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── count_filetypes.sh
│   └── add_filename_prefix/ # Python Skill 示例
│       ├── SKILL.md
│       └── scripts/
│           └── add_prefix.py
├── demo.py                  # 主程序 demo
├── requirements.txt
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行 Demo

```bash
python demo.py
```

Demo 将展示：
1. 加载 Skills
2. 路由用户输入到合适的 Skill
3. 执行 Shell 和 Python Skills
4. 查看完整执行 Trace
5. 聚合并显示指标

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

Skill Runtime 使用完整的状态机管理执行流程：

```
INIT → ROUTED → LOADED → PROMPTED → INFER → TOOL_CALL → TOOL_EXEC → TOOL_RET → INFER → FINAL
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
