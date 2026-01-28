"""
LLM Skill Runtime 状态机

使用 LangChain 和 Ollama 实现真正的 LLM 推理
"""

import time
from typing import Dict, Any, Optional, List
from skills_runtime.models import Skill, SkillResult
from skills_runtime.trace import TraceManager, TraceStorage
from skills_runtime.llm import LLMManager, LLMConfig, skill_tool


class LLMSkillRuntime:
    """LLM Skill Runtime 状态机"""

    def __init__(
        self,
        llm_config: Optional[LLMConfig] = None,
        trace_storage: Optional[TraceStorage] = None,
    ):
        """
        初始化 Runtime

        Args:
            llm_config: LLM 配置
            trace_storage: 可选的 Trace 存储（用于 Metrics）
        """
        self.llm_manager = LLMManager(llm_config)
        self.trace_manager = TraceManager()
        self.trace_storage = trace_storage or TraceStorage()
        self.state = "IDLE"

    def register_skill_tool(self, skill: Skill):
        """
        为 Skill 注册工具（此方法用于注册 Skill 内部定义的工具，如 shell, filesystem）

        Args:
            skill: Skill 定义
        """
        if skill.tools:
            for tool_def in skill.tools:
                self.llm_manager.register_tool(tool_def.name, self._create_generic_tool_func(tool_def))

    def _create_skill_execution_tool_func(self, skill: Skill) -> callable:
        """
        创建执行当前 Skill 的工具函数 (当LLM调用Skill本身时使用)

        Args:
            skill: Skill 定义

        Returns:
            可调用函数
        """
        from skills_runtime.executor import get_executor

        # This inner function will be the actual callable registered as a LangChain tool
        def skill_execution_tool_func(**kwargs):
            # The LLM has called the skill itself, with arguments in kwargs
            exec_type = skill.execution.mode if skill.execution else "python"
            executor_class = get_executor(exec_type)
            if not executor_class:
                return f"Error: No executor for type: {exec_type}"

            # Prepare inputs for the actual skill execution using the extracted kwargs
            skill_inputs = {}
            if skill.io and skill.io.inputs:
                for inp in skill.io.inputs:
                    if inp.name in kwargs:
                        skill_inputs[inp.name] = kwargs[inp.name]
                    elif inp.required:
                        return f"Error: Required input '{inp.name}' not provided by LLM."
            
            # Pass inputs to the executor. PythonExecutor expects inputs as { "1": value1, "2": value2 }
            # if the skill script uses sys.argv[1], sys.argv[2]
            indexed_inputs = {}
            if skill.io and skill.io.inputs:
                for i, inp_def in enumerate(skill.io.inputs):
                    if inp_def.name in skill_inputs:
                        indexed_inputs[str(i+1)] = skill_inputs[inp_def.name]
            else:
                # Fallback if no specific io.inputs are defined, pass kwargs directly as indexed
                indexed_inputs = {str(i+1): v for i, v in enumerate(kwargs.values())}


            executor = executor_class()
            result = executor.execute(skill, indexed_inputs, {}) # Context is empty for now

            if result.success:
                return result.stdout or result.output or "Success"
            else:
                return f"Error executing skill '{skill.metadata.name}': {result.error}"

        # Set the docstring for the tool, which LangChain uses for description
        # This will also define the expected arguments for the tool for the LLM
        # For simplicity, we just use the skill's description.
        # More advanced could dynamically generate schema from skill.io.inputs
        skill_execution_tool_func.__doc__ = skill.metadata.description or f"Executes the '{skill.metadata.name}' skill."
        
        # We need to explicitly add type hints for the kwargs for LangChain
        # This is where StructuredTool.from_function might be useful, but it requires
        # Pydantic model for args or type hints in func signature.
        # For this simple case, we rely on LLM understanding the docstring and description.

        return skill_execution_tool_func

    def _create_generic_tool_func(self, tool_def: 'ToolConfig') -> callable:
        """
        创建通用工具函数 (当LLM调用Skill内部定义的工具如shell, filesystem时使用)

        Args:
            tool_def: 工具的定义 (name, description, allowed_commands etc.)

        Returns:
            可调用函数
        """
        # This is where actual shell/filesystem operations would be implemented
        # For now, it's a placeholder. The LLM shouldn't call this directly for skill execution.
        def generic_tool_func(**kwargs):
            return f"Tool '{tool_def.name}' called with args: {kwargs}. (Not fully implemented yet)"

        generic_tool_func.__doc__ = tool_def.description or f"Executes the '{tool_def.name}' tool."
        return generic_tool_func

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
            trace_id = self.trace_manager.get_trace().trace_id if self.trace_manager.get_trace() else None

            # ROUTED
            self.state = "ROUTED"
            self.trace_manager.add_step(
                state="ROUTED",
                output={
                    "skill_id": skill.metadata.name,
                    "strategy": "llm-router",
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
            # 构建 Prompt
            prompt_text = self._build_prompt(skill, user_input, inputs)
            system_text = self._build_system_prompt(skill)

            self.trace_manager.add_step(
                state="PROMPTED",
                metadata={"prompt_tokens": len(prompt_text)},
            )

            # --- Dynamic Skill-as-Tool Registration for LLM ---
            # Create and register the current skill itself as a tool for the LLM
            # This allows the LLM to call the skill with its defined inputs
            skill_tool_name = skill.metadata.name
            skill_tool_description = skill.metadata.description

            # Temporarily register only this skill as a tool for the LLM
            # This restricts the LLM to calling this specific skill.
            temp_llm_manager_tools = self.llm_manager.tools.copy() # Save existing tools
            self.llm_manager.tools = {} # Clear for this execution

            # Register the skill as a tool
            self.llm_manager.register_tool(skill_tool_name, self._create_skill_execution_tool_func(skill))
            
            # Also register any internal tools defined by the skill (e.g., shell, filesystem)
            # These would be called by the skill itself, not directly by the LLM in this flow
            # However, if the LLM is expected to call them, they should be registered here too.
            # For this scenario, we only want the LLM to call the main skill.
            
            # So, only provide the current skill's tool to the LLM
            tools_for_llm = [skill_tool_name]
            # --- End Dynamic Registration ---

            # INFER - 使用 LLM 推理
            self.state = "INFER"
            infer_start = time.time()

            # 调用 LLM
            llm_result = self.llm_manager.invoke(
                prompt=prompt_text,
                system_prompt=system_text,
                tools=tools_for_llm, # Restrict LLM to only call the current skill
                max_iterations=skill.execution.max_steps if skill.execution else 5,
            )

            infer_latency_ms = (time.time() - infer_start) * 1000

            self.trace_manager.add_step(
                state="INFER",
                output={
                    "type": "llm_response" if not llm_result["tool_calls"] else "tool_call",
                    "response_preview": llm_result["response"][:200] if llm_result["response"] else "",
                },
                metadata={
                    "model": self.llm_manager.config.model,
                    "latency_ms": infer_latency_ms,
                    "tool_calls": len(llm_result["tool_calls"]),
                },
            )

            # If there are tool calls, these should be calls to the skill itself
            # The tool execution is handled by `_create_skill_execution_tool_func`
            if llm_result["tool_calls"]:
                tool_exec_metadata = []

                for tool_call in llm_result["tool_calls"]:
                    # TOOL_CALL
                    self.state = "TOOL_CALL"
                    self.trace_manager.add_step(
                        state="TOOL_CALL",
                        input={
                            "tool": tool_call["tool"],
                            "args": tool_call["args"],
                        },
                    )

                    # TOOL_EXEC - Tool execution for the skill itself is already done within _create_skill_execution_tool_func
                    # We just record metadata
                    tool_exec_metadata.append({
                        "tool": tool_call["tool"],
                        "args": tool_call["args"],
                        # "result": "handled_by_skill_executor", # Could add more detail here
                    })

                self.trace_manager.add_step(
                    state="TOOL_EXEC",
                    metadata={"tools_executed": len(tool_exec_metadata)},
                )
            else:
                # No tool calls (LLM returned direct text)
                self.trace_manager.add_step(
                    state="TOOL_EXEC",
                    metadata={"direct_llm_response": True},
                )

            # FINAL
            self.state = "FINAL"

            # 构建最终输出
            if llm_result.get("error"):
                final_output = {"error": llm_result["error"]}
                final_status = "FAILED"
            else:
                final_output = {"result": llm_result["response"]}
                final_status = "SUCCESS"

            self.trace_manager.finish_trace(
                status=final_status,
                output=final_output,
            )

            # Save Trace to storage
            trace = self.trace_manager.get_trace()
            if trace:
                self.trace_storage.add_trace(trace)

            final_skill_result = SkillResult(
                trace_id=trace_id,
                success=final_status == "SUCCESS",
                output=llm_result["response"],
                error=llm_result.get("error"),
                metadata={
                    "tool_calls": llm_result["tool_calls"],
                    "latency_ms": infer_latency_ms,
                },
            )
            return final_skill_result

        except Exception as e:
            # Error handling
            self.trace_manager.finish_trace(
                status="FAILED",
                output={"error": str(e)},
            )
            trace_id = self.trace_manager.get_trace().trace_id if self.trace_manager.get_trace() else None
            return SkillResult(
                trace_id=trace_id,
                success=False,
                error=str(e),
            )

        finally:
            self.state = "IDLE"
            # Restore original tools to LLMManager after execution
            self.llm_manager.tools = temp_llm_manager_tools

    def _build_prompt(self, skill: Skill, user_input: str, inputs: Dict[str, Any]) -> str:
        """
        构建 Prompt

        Args:
            skill: Skill 定义
            user_input: 用户输入
            inputs: 输入参数

        Returns:
            Prompt 文本
        """
        prompt_parts = [f"User Input: {user_input}"]

        # 添加输入参数
        if inputs:
            prompt_parts.append("\nInputs:")
            for key, value in inputs.items():
                prompt_parts.append(f"  - {key}: {value}")

        # 添加 Skill 步骤
        if skill.prompt and skill.prompt.steps:
            prompt_parts.append("\nSteps to follow:")
            for step in skill.prompt.steps:
                prompt_parts.append(f"  - {step}")

        return "\n".join(prompt_parts)

    def _build_system_prompt(self, skill: Skill) -> str:
        """
        构建系统 Prompt

        Args:
            skill: Skill 定义

        Returns:
            系统 Prompt
        """
        parts = [f"Skill: {skill.metadata.name}"]

        # 添加描述
        if skill.metadata.description:
            parts.append(f"Description: {skill.metadata.description}")

        # 添加系统提示
        if skill.prompt and skill.prompt.system:
            parts.append(f"\n{skill.prompt.system}")

        # 添加约束
        if skill.prompt and skill.prompt.constraints:
            parts.append("\nConstraints:")
            for constraint in skill.prompt.constraints:
                parts.append(f"  - {constraint}")

        return "\n".join(parts)

    def simple_chat(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        简单的聊天（不使用 Skill）

        Args:
            user_input: 用户输入
            system_prompt: 系统提示

        Returns:
            模型响应
        """
        return self.llm_manager.simple_invoke(user_input, system_prompt)

    def get_trace(self) -> Optional[Dict[str, Any]]:
        """获取当前 Trace"""
        return self.trace_manager.to_dict()

    def get_trace_json(self) -> Optional[str]:
        """获取当前 Trace JSON"""
        return self.trace_manager.to_json()
