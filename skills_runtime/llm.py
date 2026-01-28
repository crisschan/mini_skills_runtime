"""
LLM 集成

使用 LangChain 和 Ollama 实现 LLM 推理
"""

import time
from typing import Any, Dict, Optional, List, Callable
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool


class LLMConfig:
    """LLM 配置"""

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        temperature: float = 0.7,
        base_url: Optional[str] = "http://localhost:11434",
    ):
        """
        初始化 LLM 配置

        Args:
            model: 模型名称（Ollama 格式）
            temperature: 温度参数
            base_url: Ollama API 地址（默认为本地 Ollama 服务）
        """
        self.model = model
        self.temperature = temperature
        self.base_url = base_url


class LLMManager:
    """LLM 管理器"""

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        初始化 LLM 管理器

        Args:
            config: LLM 配置
        """
        self.config = config or LLMConfig(model="qwen2.5:7b")
        self.llm = self._create_llm()
        self.tools: Dict[str, Callable] = {}

    def _create_llm(self):
        """创建 LangChain LLM 实例"""
        return ChatOllama(
            model=self.config.model,
            temperature=self.config.temperature,
            base_url=self.config.base_url,
        )

    def register_tool(self, name: str, tool_func: Callable):
        """
        注册工具

        Args:
            name: 工具名称
            tool_func: 工具函数
        """
        self.tools[name] = tool_func

    def create_langchain_tools(self) -> List:
        """
        创建 LangChain 工具列表

        Returns:
            LangChain 工具列表
        """
        from langchain_core.tools import StructuredTool

        langchain_tools = []
        for name, func in self.tools.items():
            tool = StructuredTool.from_function(
                func=func,
                name=name,
                description=func.__doc__ or f"Tool: {name}",
            )
            langchain_tools.append(tool)

        return langchain_tools

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[str]] = None,
        max_iterations: int = 5,
    ) -> Dict[str, Any]:
        """
        调用 LLM

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            tools: 可用的工具列表
            max_iterations: 最大迭代次数

        Returns:
            {
                "response": 模型响应,
                "tool_calls": 工具调用记录,
                "latency_ms": 延迟
            }
        """
        # 构建消息
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        messages.append(HumanMessage(content=prompt))

        # 准备工具
        available_tools = None
        if tools:
            # 只使用指定的工具
            # Debug: print tools type and content
            import sys
            print(f"[DEBUG] tools parameter type: {type(tools)}, value: {tools}", file=sys.stderr)
            langchain_tools_list = self.create_langchain_tools()
            print(f"[DEBUG] langchain tools count: {len(langchain_tools_list)}", file=sys.stderr)
            available_tools = []
            for t in langchain_tools_list:
                print(f"[DEBUG] langchain tool: {t}, has name: {hasattr(t, 'name')}, name: {t.name if hasattr(t, 'name') else 'N/A'}", file=sys.stderr)
                if hasattr(t, 'name') and t.name in tools:
                    available_tools.append(t)
        else:
            # 使用所有注册的工具
            available_tools = self.create_langchain_tools()

        # 绑定工具
        llm_with_tools = self.llm.bind_tools(available_tools) if available_tools else self.llm

        # 执行推理
        start_time = time.time()
        tool_calls = []

        try:
            if available_tools:
                # 使用工具调用
                iteration = 0
                current_messages = messages.copy()

                while iteration < max_iterations:
                    result = llm_with_tools.invoke(current_messages)
                    latency_ms = (time.time() - start_time) * 1000

                    # 检查是否有工具调用
                    if not hasattr(result, 'tool_calls') or not result.tool_calls:
                        # 没有更多工具调用，结束
                        break
                    
                    import sys
                    print(f"[DEBUG] LLM made {len(result.tool_calls)} tool calls", file=sys.stderr)
                    current_messages.append(result)

                    for tool_call in result.tool_calls:
                        tool_name = tool_call.get("name")
                        tool_args = tool_call.get("args", {})
                        tool_id = tool_call.get("id")
                        print(f"[DEBUG] tool_call: {tool_call}", file=sys.stderr)

                        if not tool_name or not tool_id:
                            print(f"[DEBUG] Invalid tool call object: {tool_call}", file=sys.stderr)
                            continue

                        tool_calls.append({
                            "tool": tool_name,
                            "args": tool_args,
                        })

                        # 执行工具
                        tool_func = self.tools.get(tool_name)
                        if tool_func:
                            try:
                                tool_output = tool_func(**tool_args)
                                current_messages.append(
                                    ToolMessage(
                                        content=str(tool_output),
                                        tool_call_id=tool_id,
                                    )
                                )
                            except Exception as e:
                                print(f"[DEBUG] Error executing tool {tool_name}: {e}", file=sys.stderr)
                                current_messages.append(
                                    ToolMessage(
                                        content=f"Error executing tool: {e}",
                                        tool_call_id=tool_id,
                                    )
                                )
                        else:
                            print(f"[DEBUG] tool_func not found for name: {tool_name}", file=sys.stderr)
                            current_messages.append(
                                ToolMessage(
                                    content=f"Tool '{tool_name}' not found.",
                                    tool_call_id=tool_id,
                                )
                            )
                    
                    iteration += 1
            else:
                # 不使用工具，直接推理
                result = self.llm.invoke(messages)
                latency_ms = (time.time() - start_time) * 1000

            return {
                "response": str(result.content) if hasattr(result, 'content') else str(result),
                "tool_calls": tool_calls,
                "latency_ms": latency_ms,
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {
                "response": None,
                "tool_calls": tool_calls,
                "latency_ms": latency_ms,
                "error": str(e),
            }

    def simple_invoke(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        简单的 LLM 调用（不带工具）

        Args:
            prompt: 提示文本
            system_prompt: 系统提示

        Returns:
            模型响应
        """
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        start_time = time.time()
        result = self.llm.invoke(messages)
        latency_ms = (time.time() - start_time) * 1000

        return str(result.content) if hasattr(result, 'content') else str(result)


# 预定义的工具装饰器
def skill_tool(name: str, description: str = ""):
    """
    Skill 工具装饰器

    Args:
        name: 工具名称
        description: 工具描述
    """
    def decorator(func):
        func.__doc__ = description
        return func
    return decorator
