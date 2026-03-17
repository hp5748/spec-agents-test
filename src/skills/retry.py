"""
重试管理器模块
管理技能执行的重试策略和延迟计算
"""
import logging
import random
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Any
from enum import Enum

from .base import RetryDecision, SkillResult

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """重试策略"""
    FIXED = "fixed"           # 固定延迟
    LINEAR = "linear"         # 线性递增
    EXPONENTIAL = "exponential"  # 指数递增
    EXPONENTIAL_JITTER = "exponential_jitter"  # 指数递增 + 抖动


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 30.0
    jitter_factor: float = 0.1  # 抖动因子 (0-1)

    # 可重试的错误类型
    retryable_errors: List[str] = field(default_factory=lambda: [
        "timeout",
        "rate_limit",
        "connection_error",
        "temporary_failure"
    ])

    # 不可重试的错误类型（立即失败）
    non_retryable_errors: List[str] = field(default_factory=lambda: [
        "invalid_input",
        "authentication_error",
        "permission_denied"
    ])


@dataclass
class RetryState:
    """重试状态"""
    attempt: int = 0
    last_error: Optional[str] = None
    total_delay: float = 0.0
    errors: List[str] = field(default_factory=list)


class RetryManager:
    """
    重试管理器

    管理技能执行的重试逻辑，包括：
    - 判断是否应该重试
    - 计算重试延迟
    - 追踪重试状态
    """

    def __init__(self, config: RetryConfig = None):
        """
        初始化重试管理器

        Args:
            config: 重试配置
        """
        self._config = config or RetryConfig()

    def should_retry(
        self,
        attempt: int,
        error: str,
        state: RetryState = None
    ) -> RetryDecision:
        """
        判断是否应该重试

        Args:
            attempt: 当前尝试次数
            error: 错误信息
            state: 重试状态

        Returns:
            重试决策
        """
        # 检查是否达到最大尝试次数
        if attempt >= self._config.max_attempts:
            return RetryDecision(
                should_retry=False,
                delay=0,
                reason="已达到最大重试次数",
                max_attempts_reached=True
            )

        # 检查是否为不可重试的错误
        error_lower = error.lower()
        for non_retryable in self._config.non_retryable_errors:
            if non_retryable.lower() in error_lower:
                return RetryDecision(
                    should_retry=False,
                    delay=0,
                    reason=f"不可重试的错误类型: {non_retryable}"
                )

        # 检查是否为可重试的错误
        is_retryable = False
        for retryable in self._config.retryable_errors:
            if retryable.lower() in error_lower:
                is_retryable = True
                break

        # 默认情况下，未知的错误也可以重试
        if not is_retryable:
            # 如果错误类型未知，允许重试
            is_retryable = True

        if is_retryable:
            delay = self.calculate_delay(attempt)
            return RetryDecision(
                should_retry=True,
                delay=delay,
                reason=f"可重试错误，等待 {delay:.2f}s 后重试"
            )

        return RetryDecision(
            should_retry=False,
            delay=0,
            reason="错误类型不支持重试"
        )

    def calculate_delay(self, attempt_number: int) -> float:
        """
        计算重试延迟

        Args:
            attempt_number: 当前尝试次数（从1开始）

        Returns:
            延迟秒数
        """
        base_delay = self._config.base_delay
        strategy = self._config.strategy

        if strategy == RetryStrategy.FIXED:
            delay = base_delay

        elif strategy == RetryStrategy.LINEAR:
            delay = base_delay * attempt_number

        elif strategy == RetryStrategy.EXPONENTIAL:
            delay = base_delay * (2 ** (attempt_number - 1))

        elif strategy == RetryStrategy.EXPONENTIAL_JITTER:
            # 指数递增 + 随机抖动
            exponential_delay = base_delay * (2 ** (attempt_number - 1))
            jitter = exponential_delay * self._config.jitter_factor * random.random()
            delay = exponential_delay + jitter

        else:
            delay = base_delay

        # 限制最大延迟
        return min(delay, self._config.max_delay)

    def create_state(self) -> RetryState:
        """创建新的重试状态"""
        return RetryState()

    def update_state(
        self,
        state: RetryState,
        error: str,
        delay: float
    ) -> None:
        """
        更新重试状态

        Args:
            state: 重试状态
            error: 错误信息
            delay: 延迟时间
        """
        state.attempt += 1
        state.last_error = error
        state.total_delay += delay
        state.errors.append(error)

    def execute_with_retry(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        on_retry: Callable[[int, float, str], None] = None,
        on_success: Callable[[Any], None] = None,
        on_failure: Callable[[str], None] = None
    ) -> Any:
        """
        使用重试机制执行函数

        Args:
            func: 要执行的函数
            args: 函数参数
            kwargs: 函数关键字参数
            on_retry: 重试回调
            on_success: 成功回调
            on_failure: 失败回调

        Returns:
            函数执行结果
        """
        if kwargs is None:
            kwargs = {}

        state = self.create_state()
        last_error = None

        while state.attempt < self._config.max_attempts:
            state.attempt += 1

            try:
                result = func(*args, **kwargs)

                # 检查是否为 SkillResult 且执行失败
                if isinstance(result, SkillResult) and not result.success:
                    raise Exception(result.error or "执行失败")

                if on_success:
                    on_success(result)

                return result

            except Exception as e:
                last_error = str(e)
                state.errors.append(last_error)

                # 判断是否重试
                decision = self.should_retry(state.attempt, last_error, state)

                if decision.should_retry:
                    logger.info(
                        f"重试 {state.attempt}/{self._config.max_attempts}: "
                        f"{decision.reason}"
                    )

                    if on_retry:
                        on_retry(state.attempt, decision.delay, last_error)

                    import time
                    time.sleep(decision.delay)
                else:
                    break

        # 所有重试都失败
        if on_failure:
            on_failure(last_error or "未知错误")

        raise Exception(f"重试 {state.attempt} 次后仍然失败: {last_error}")


# 全局重试管理器实例
retry_manager = RetryManager()


def create_retry_manager(
    max_attempts: int = 3,
    strategy: str = "exponential",
    base_delay: float = 1.0,
    max_delay: float = 30.0
) -> RetryManager:
    """
    创建重试管理器

    Args:
        max_attempts: 最大尝试次数
        strategy: 重试策略 (fixed/linear/exponential/exponential_jitter)
        base_delay: 基础延迟
        max_delay: 最大延迟

    Returns:
        RetryManager 实例
    """
    strategy_map = {
        "fixed": RetryStrategy.FIXED,
        "linear": RetryStrategy.LINEAR,
        "exponential": RetryStrategy.EXPONENTIAL,
        "exponential_jitter": RetryStrategy.EXPONENTIAL_JITTER
    }

    config = RetryConfig(
        max_attempts=max_attempts,
        strategy=strategy_map.get(strategy, RetryStrategy.EXPONENTIAL),
        base_delay=base_delay,
        max_delay=max_delay
    )

    return RetryManager(config)
