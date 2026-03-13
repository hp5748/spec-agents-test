"""
Skills 基类模块
定义技能的核心抽象和数据结构
"""
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, AsyncGenerator
from enum import Enum

# 技能执行日志器
skill_logger = logging.getLogger("skill_execution")


class SkillStatus(Enum):
    """技能状态"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class SkillConfig:
    """技能配置"""
    priority: int = 10  # 优先级，数值越大优先级越高
    enabled: bool = True
    max_retries: int = 3
    timeout: int = 30  # 超时时间（秒）
    fallback_enabled: bool = True  # 是否启用降级
    stream_enabled: bool = True  # 是否支持流式输出
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillContext:
    """技能执行上下文"""
    session_id: str
    user_input: str
    intent: str
    chat_history: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 运行时注入的依赖
    tools: Dict[str, Any] = field(default_factory=dict)
    llm: Any = None

    def get_tool(self, tool_name: str) -> Optional[Any]:
        """获取指定工具"""
        return self.tools.get(tool_name)


@dataclass
class SkillResult:
    """技能执行结果"""
    success: bool
    response: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    used_tools: List[str] = field(default_factory=list)


class BaseSkill(ABC):
    """
    技能基类

    所有技能都需要继承此类并实现 execute 方法。
    技能是可以组合多个工具、包含专业知识、支持多步骤的复杂能力。
    """

    # ===== 元信息（子类必须覆盖）=====
    name: str = "base_skill"
    description: str = "基础技能"
    version: str = "1.0.0"
    tags: List[str] = []

    # ===== 依赖配置（子类必须覆盖）=====
    required_tools: List[str] = []  # 必需的工具名称
    supported_intents: List[str] = []  # 支持的意图类型

    # ===== 内部状态 =====
    _tools: Dict[str, Any] = {}
    _llm: Any = None
    _config: SkillConfig = None

    def __init__(self, config: SkillConfig = None):
        """初始化技能"""
        self._config = config or SkillConfig()

    def set_tools(self, tools: Dict[str, Any]) -> None:
        """设置可用工具"""
        self._tools = tools
        # 验证必需工具
        missing_tools = set(self.required_tools) - set(tools.keys())
        if missing_tools:
            raise ValueError(f"技能 {self.name} 缺少必需工具: {missing_tools}")

    def set_llm(self, llm: Any) -> None:
        """设置 LLM 实例"""
        self._llm = llm

    def get_config(self) -> SkillConfig:
        """获取技能配置"""
        return self._config

    def get_prompt_template(self) -> str:
        """
        获取技能专属提示词模板
        子类可以覆盖此方法提供自定义模板
        """
        return ""

    def execute_with_logging(self, context: SkillContext) -> SkillResult:
        """
        带日志的技能执行（包装器）

        Args:
            context: 技能执行上下文

        Returns:
            技能执行结果
        """
        start_time = time.time()

        # 记录执行开始
        skill_logger.info(f"\n{'='*60}")
        skill_logger.info(f"[SKILL START] {self.name} v{self.version}")
        skill_logger.info(f"{'='*60}")
        skill_logger.info(f"  Session ID: {context.session_id}")
        skill_logger.info(f"  Intent: {context.intent}")
        skill_logger.info(f"  User Input: {context.user_input[:100]}...")
        skill_logger.info(f"  Required Tools: {self.required_tools}")
        skill_logger.info(f"  Available Tools: {list(self._tools.keys())}")
        skill_logger.info(f"  LLM Available: {self._llm is not None}")

        try:
            # 执行技能
            result = self.execute(context)

            # 计算耗时
            elapsed = time.time() - start_time

            # 记录执行结果
            skill_logger.info(f"\n{'-'*60}")
            skill_logger.info(f"[SKILL END] {self.name}")
            skill_logger.info(f"{'-'*60}")
            skill_logger.info(f"  Success: {result.success}")
            skill_logger.info(f"  Used Tools: {result.used_tools}")
            skill_logger.info(f"  Response Length: {len(result.response)} chars")
            if result.error:
                skill_logger.info(f"  Error: {result.error}")
            if result.data:
                skill_logger.info(f"  Data: {result.data}")
            skill_logger.info(f"  Elapsed: {elapsed:.3f}s")
            skill_logger.info(f"{'='*60}\n")

            return result

        except Exception as e:
            elapsed = time.time() - start_time
            skill_logger.error(f"\n[SKILL ERROR] {self.name}")
            skill_logger.error(f"  Exception: {type(e).__name__}: {e}")
            skill_logger.error(f"  Elapsed: {elapsed:.3f}s")
            skill_logger.error(f"{'='*60}\n")

            return SkillResult(
                success=False,
                response="",
                error=f"技能执行异常: {str(e)}"
            )

    @abstractmethod
    def execute(self, context: SkillContext) -> SkillResult:
        """
        执行技能（子类实现）

        Args:
            context: 技能执行上下文

        Returns:
            技能执行结果
        """
        pass

    def execute_stream(self, context: SkillContext) -> AsyncGenerator[str, None]:
        """
        流式执行技能

        子类可以覆盖此方法实现流式输出。
        默认实现将 execute 结果分块输出。

        Args:
            context: 技能执行上下文

        Yields:
            流式响应的文本块
        """
        # 默认实现：将结果分块输出
        result = self.execute(context)
        if result.success:
            response = result.response
            # 每 10 个字符作为一个块
            for i in range(0, len(response), 10):
                yield response[i:i + 10]
        else:
            yield f"技能执行失败: {result.error}"

    def validate_context(self, context: SkillContext) -> bool:
        """
        验证执行上下文

        子类可以覆盖此方法添加自定义验证逻辑
        """
        if not context.user_input:
            return False
        if not self._llm and self.requires_llm():
            return False
        return True

    def requires_llm(self) -> bool:
        """是否需要 LLM"""
        return True  # 大多数技能都需要 LLM

    def can_handle_intent(self, intent: str) -> bool:
        """检查是否能处理指定意图"""
        return intent in self.supported_intents

    def get_tool(self, tool_name: str) -> Optional[Any]:
        """获取指定工具"""
        return self._tools.get(tool_name)

    def __repr__(self) -> str:
        return f"<Skill {self.name} v{self.version}>"
