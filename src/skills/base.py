"""
Skills 基类模块
定义技能的核心抽象和数据结构
"""
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, AsyncGenerator, Tuple
from enum import Enum

# 技能执行日志器
skill_logger = logging.getLogger("skill_execution")


class SkillStatus(Enum):
    """技能状态"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    FALLBACK = "fallback"


# ============================================================
# 核心数据类
# ============================================================

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

    # 新增：重试策略配置
    retry_strategy: str = "exponential"  # exponential/linear/fixed
    retry_base_delay: float = 1.0

    # 新增：验证配置
    validation_schema: Optional[str] = None

    # 新增：降级配置
    fallback_strategy: str = "llm_assist"  # llm_assist/default_message/none
    fallback_message: str = ""


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

    # 新增：技能资源
    references: List[Any] = field(default_factory=list)  # ReferenceContent 列表
    assets: List[Any] = field(default_factory=list)  # AssetContent 列表
    instruction: str = ""  # SKILL.md 中的指令内容

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

    # 新增：验证信息
    validation_passed: bool = True
    validation_errors: List[str] = field(default_factory=list)


# ============================================================
# 新增数据类：技能匹配与执行追踪
# ============================================================

@dataclass
class SkillMatch:
    """技能匹配结果"""
    skill_name: str
    confidence: float  # 0.0 - 1.0
    matched_intents: List[str] = field(default_factory=list)
    matched_keywords: List[str] = field(default_factory=list)
    priority: int = 10

    def __lt__(self, other: 'SkillMatch') -> bool:
        """用于排序，优先级高的排前面"""
        if self.confidence != other.confidence:
            return self.confidence > other.confidence
        return self.priority > other.priority


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    score: float = 1.0  # 质量评分 0-1
    warnings: List[str] = field(default_factory=list)


@dataclass
class RetryDecision:
    """重试决策"""
    should_retry: bool
    delay: float
    reason: str
    max_attempts_reached: bool = False


@dataclass
class ExecutionAttempt:
    """单次执行尝试记录"""
    attempt_number: int
    start_time: float
    end_time: float
    success: bool
    error: Optional[str] = None
    response: str = ""
    validation_passed: bool = True


@dataclass
class ExecutionTrace:
    """执行追踪记录"""
    trace_id: str
    skill_name: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    attempts: List[ExecutionAttempt] = field(default_factory=list)
    final_result: Optional[SkillResult] = None
    fallback_used: bool = False
    total_elapsed: float = 0.0

    @classmethod
    def create(cls, skill_name: str) -> 'ExecutionTrace':
        """创建新的执行追踪"""
        return cls(
            trace_id=str(uuid.uuid4())[:8],
            skill_name=skill_name
        )

    def add_attempt(self, attempt: ExecutionAttempt) -> None:
        """添加执行尝试记录"""
        self.attempts.append(attempt)

    def get_last_attempt(self) -> Optional[ExecutionAttempt]:
        """获取最后一次尝试"""
        return self.attempts[-1] if self.attempts else None


# ============================================================
# 技能基类
# ============================================================

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

    # ============================================================
    # 新增：验证与重试方法
    # ============================================================

    def validate_result(self, result: SkillResult) -> ValidationResult:
        """
        验证执行结果

        子类可以覆盖此方法添加自定义验证逻辑

        Args:
            result: 技能执行结果

        Returns:
            验证结果
        """
        errors = []
        warnings = []

        # 基本验证
        if not result.success:
            errors.append(f"执行失败: {result.error}")

        if not result.response or not result.response.strip():
            errors.append("响应内容为空")

        # 如果有配置验证 schema，进行额外验证
        if self._config.validation_schema:
            # 这里可以扩展具体的 schema 验证逻辑
            pass

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            score=1.0 if len(errors) == 0 else 0.0
        )

    def execute_with_retry(
        self,
        context: SkillContext,
        on_retry: callable = None
    ) -> Tuple[SkillResult, ExecutionTrace]:
        """
        带重试的执行

        Args:
            context: 技能执行上下文
            on_retry: 重试回调函数

        Returns:
            (执行结果, 执行追踪)
        """
        trace = ExecutionTrace.create(self.name)
        trace.status = ExecutionStatus.RUNNING

        max_attempts = self._config.max_retries + 1  # 初始尝试 + 重试次数

        for attempt_num in range(1, max_attempts + 1):
            attempt_start = time.time()

            try:
                # 执行技能
                result = self.execute(context)
                attempt_end = time.time()

                # 记录尝试
                attempt = ExecutionAttempt(
                    attempt_number=attempt_num,
                    start_time=attempt_start,
                    end_time=attempt_end,
                    success=result.success,
                    error=result.error,
                    response=result.response[:100] if result.response else "",
                    validation_passed=True
                )
                trace.add_attempt(attempt)

                # 验证结果
                validation = self.validate_result(result)
                result.validation_passed = validation.is_valid
                result.validation_errors = validation.errors

                if result.success and validation.is_valid:
                    trace.status = ExecutionStatus.SUCCESS
                    trace.final_result = result
                    trace.total_elapsed = attempt_end - trace.attempts[0].start_time
                    return result, trace

                # 需要重试
                if attempt_num < max_attempts:
                    trace.status = ExecutionStatus.RETRYING

                    # 计算延迟
                    delay = self._calculate_retry_delay(attempt_num)

                    if on_retry:
                        on_retry(attempt_num, delay, result.error or "验证失败")

                    time.sleep(delay)

            except Exception as e:
                attempt_end = time.time()
                attempt = ExecutionAttempt(
                    attempt_number=attempt_num,
                    start_time=attempt_start,
                    end_time=attempt_end,
                    success=False,
                    error=str(e)
                )
                trace.add_attempt(attempt)

                if attempt_num < max_attempts:
                    trace.status = ExecutionStatus.RETRYING
                    delay = self._calculate_retry_delay(attempt_num)

                    if on_retry:
                        on_retry(attempt_num, delay, str(e))

                    time.sleep(delay)

        # 所有尝试都失败
        trace.status = ExecutionStatus.FAILED
        last_attempt = trace.get_last_attempt()
        trace.final_result = SkillResult(
            success=False,
            response="",
            error=last_attempt.error if last_attempt else "所有重试均失败"
        )
        trace.total_elapsed = time.time() - trace.attempts[0].start_time

        return trace.final_result, trace

    def _calculate_retry_delay(self, attempt_number: int) -> float:
        """
        计算重试延迟

        Args:
            attempt_number: 当前尝试次数

        Returns:
            延迟秒数
        """
        base_delay = self._config.retry_base_delay
        strategy = self._config.retry_strategy

        if strategy == "fixed":
            return base_delay
        elif strategy == "linear":
            return base_delay * attempt_number
        elif strategy == "exponential":
            return base_delay * (2 ** (attempt_number - 1))
        else:
            return base_delay

    def fallback(self, context: SkillContext, error: str) -> SkillResult:
        """
        降级处理

        当技能执行失败且重试用尽时调用

        Args:
            context: 技能执行上下文
            error: 错误信息

        Returns:
            降级结果
        """
        strategy = self._config.fallback_strategy

        if strategy == "none":
            return SkillResult(
                success=False,
                response="",
                error=error
            )

        elif strategy == "default_message":
            message = self._config.fallback_message or f"抱歉，{self.description}暂时不可用，请稍后重试。"
            return SkillResult(
                success=True,
                response=message,
                data={"fallback": True, "original_error": error}
            )

        elif strategy == "llm_assist":
            # 使用 LLM 生成降级响应
            if self._llm:
                try:
                    fallback_prompt = f"""用户请求: {context.user_input}

原始处理失败: {error}

请用友好的方式回复用户，说明无法处理的原因，并建议用户可以：
1. 稍后重试
2. 提供更多信息
3. 联系人工客服"""

                    response = self._llm.invoke(fallback_prompt)
                    return SkillResult(
                        success=True,
                        response=response.content,
                        data={"fallback": True, "original_error": error}
                    )
                except Exception as e:
                    # LLM 也失败，返回默认消息
                    return SkillResult(
                        success=True,
                        response=self._config.fallback_message or f"抱歉，服务暂时不可用，请稍后重试。",
                        data={"fallback": True, "original_error": error, "llm_error": str(e)}
                    )

            # 没有 LLM，返回默认消息
            return SkillResult(
                success=True,
                response=self._config.fallback_message or f"抱歉，{self.description}暂时不可用，请稍后重试。",
                data={"fallback": True, "original_error": error}
            )

        # 默认返回错误
        return SkillResult(
            success=False,
            response="",
            error=error
        )

    # ============================================================
    # 原有方法
    # ============================================================

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
