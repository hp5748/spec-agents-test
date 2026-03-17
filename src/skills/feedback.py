"""
反馈生成器模块
生成结构化的错误反馈和用户友好的消息
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime

from .base import ExecutionTrace, SkillResult

logger = logging.getLogger(__name__)


class FeedbackLevel(Enum):
    """反馈级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class FeedbackType(Enum):
    """反馈类型"""
    VALIDATION_FAILED = "validation_failed"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    CONNECTION_ERROR = "connection_error"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    INTERNAL_ERROR = "internal_error"
    UNKNOWN_ERROR = "unknown_error"
    SUCCESS = "success"


@dataclass
class ErrorFeedback:
    """错误反馈"""
    feedback_id: str
    feedback_type: FeedbackType
    level: FeedbackLevel
    title: str
    message: str
    suggestion: str = ""
    technical_details: str = ""
    retry_possible: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # 附加信息
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "feedback_id": self.feedback_id,
            "feedback_type": self.feedback_type.value,
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "suggestion": self.suggestion,
            "retry_possible": self.retry_possible,
            "timestamp": self.timestamp
        }


# 默认错误模板
DEFAULT_ERROR_TEMPLATES: Dict[str, Dict[str, str]] = {
    "validation_failed": {
        "title": "数据验证失败",
        "message": "请求的数据格式不符合要求",
        "suggestion": "请检查输入信息是否正确"
    },
    "timeout": {
        "title": "请求超时",
        "message": "服务响应时间过长",
        "suggestion": "请稍后重试，或检查网络连接"
    },
    "rate_limit": {
        "title": "请求过于频繁",
        "message": "您发送的请求过于频繁",
        "suggestion": "请等待几秒后再试"
    },
    "connection_error": {
        "title": "连接失败",
        "message": "无法连接到服务",
        "suggestion": "请检查网络连接后重试"
    },
    "not_found": {
        "title": "未找到",
        "message": "请求的资源不存在",
        "suggestion": "请确认输入的信息是否正确"
    },
    "permission_denied": {
        "title": "权限不足",
        "message": "您没有权限执行此操作",
        "suggestion": "请联系客服获取帮助"
    },
    "internal_error": {
        "title": "服务异常",
        "message": "服务暂时不可用",
        "suggestion": "请稍后重试，或联系客服"
    },
    "unknown_error": {
        "title": "未知错误",
        "message": "发生了意外错误",
        "suggestion": "请稍后重试"
    }
}


class FeedbackGenerator:
    """
    反馈生成器

    根据错误类型和上下文生成结构化的错误反馈
    """

    def __init__(self, custom_templates: Dict[str, Dict[str, str]] = None):
        """
        初始化反馈生成器

        Args:
            custom_templates: 自定义错误模板
        """
        self._templates = DEFAULT_ERROR_TEMPLATES.copy()
        if custom_templates:
            self._templates.update(custom_templates)

        # 技能特定的错误模板
        self._skill_templates: Dict[str, Dict[str, Dict[str, str]]] = {}

    def register_template(
        self,
        error_type: str,
        title: str,
        message: str,
        suggestion: str = ""
    ) -> None:
        """注册错误模板"""
        self._templates[error_type] = {
            "title": title,
            "message": message,
            "suggestion": suggestion
        }

    def register_skill_templates(
        self,
        skill_name: str,
        templates: Dict[str, Dict[str, str]]
    ) -> None:
        """注册技能特定的错误模板"""
        self._skill_templates[skill_name] = templates

    def generate(
        self,
        error: str,
        context: Dict[str, Any] = None,
        trace: ExecutionTrace = None,
        skill_name: str = None
    ) -> ErrorFeedback:
        """
        生成错误反馈

        Args:
            error: 错误信息
            context: 执行上下文
            trace: 执行追踪
            skill_name: 技能名称

        Returns:
            错误反馈
        """
        context = context or {}

        # 分析错误类型
        feedback_type = self._analyze_error_type(error)
        level = self._determine_level(feedback_type)

        # 获取模板
        template = self._get_template(feedback_type.value, skill_name)

        # 生成反馈 ID
        import uuid
        feedback_id = str(uuid.uuid4())[:8]

        # 构建消息
        message = template.get("message", "发生错误")
        suggestion = template.get("suggestion", "")

        # 如果有追踪信息，添加更多上下文
        technical_details = ""
        if trace:
            technical_details = self._build_technical_details(trace, error)

        return ErrorFeedback(
            feedback_id=feedback_id,
            feedback_type=feedback_type,
            level=level,
            title=template.get("title", "错误"),
            message=message,
            suggestion=suggestion,
            technical_details=technical_details,
            retry_possible=self._is_retry_possible(feedback_type),
            metadata={
                "skill_name": skill_name,
                "attempt_count": len(trace.attempts) if trace else 0
            }
        )

    def _analyze_error_type(self, error: str) -> FeedbackType:
        """分析错误类型"""
        error_lower = error.lower()

        if "timeout" in error_lower or "超时" in error:
            return FeedbackType.TIMEOUT

        if "rate limit" in error_lower or "频繁" in error:
            return FeedbackType.RATE_LIMIT

        if "connection" in error_lower or "连接" in error_lower:
            return FeedbackType.CONNECTION_ERROR

        if "not found" in error_lower or "未找到" in error_lower or "不存在" in error_lower:
            return FeedbackType.NOT_FOUND

        if "permission" in error_lower or "权限" in error_lower:
            return FeedbackType.PERMISSION_DENIED

        if "validation" in error_lower or "验证" in error_lower:
            return FeedbackType.VALIDATION_FAILED

        if "internal" in error_lower or "内部" in error_lower:
            return FeedbackType.INTERNAL_ERROR

        return FeedbackType.UNKNOWN_ERROR

    def _determine_level(self, feedback_type: FeedbackType) -> FeedbackLevel:
        """确定反馈级别"""
        if feedback_type == FeedbackType.SUCCESS:
            return FeedbackLevel.SUCCESS

        if feedback_type in [FeedbackType.VALIDATION_FAILED, FeedbackType.NOT_FOUND]:
            return FeedbackLevel.WARNING

        return FeedbackLevel.ERROR

    def _get_template(
        self,
        error_type: str,
        skill_name: str = None
    ) -> Dict[str, str]:
        """获取错误模板"""
        # 优先使用技能特定的模板
        if skill_name and skill_name in self._skill_templates:
            skill_templates = self._skill_templates[skill_name]
            if error_type in skill_templates:
                return skill_templates[error_type]

        # 使用通用模板
        return self._templates.get(error_type, self._templates["unknown_error"])

    def _is_retry_possible(self, feedback_type: FeedbackType) -> bool:
        """判断是否可以重试"""
        retryable_types = {
            FeedbackType.TIMEOUT,
            FeedbackType.RATE_LIMIT,
            FeedbackType.CONNECTION_ERROR,
            FeedbackType.INTERNAL_ERROR
        }
        return feedback_type in retryable_types

    def _build_technical_details(
        self,
        trace: ExecutionTrace,
        error: str
    ) -> str:
        """构建技术细节"""
        parts = [f"追踪ID: {trace.trace_id}"]

        if trace.attempts:
            parts.append(f"尝试次数: {len(trace.attempts)}")
            last_attempt = trace.attempts[-1]
            parts.append(f"最后状态: {'成功' if last_attempt.success else '失败'}")

        parts.append(f"错误: {error}")

        return " | ".join(parts)

    def format_for_user(self, feedback: ErrorFeedback) -> str:
        """
        格式化为用户友好的消息

        Args:
            feedback: 错误反馈

        Returns:
            用户友好的消息
        """
        parts = [feedback.message]

        if feedback.suggestion:
            parts.append(feedback.suggestion)

        if feedback.retry_possible:
            parts.append("您可以稍后重试。")

        return " ".join(parts)

    def format_for_log(self, feedback: ErrorFeedback) -> str:
        """
        格式化为日志消息

        Args:
            feedback: 错误反馈

        Returns:
            日志消息
        """
        return (
            f"[{feedback.level.value.upper()}] "
            f"{feedback.feedback_type.value}: "
            f"{feedback.title} - {feedback.message}"
            f" | {feedback.technical_details}"
        )


# 全局反馈生成器实例
feedback_generator = FeedbackGenerator()


def generate_feedback(
    error: str,
    context: Dict[str, Any] = None,
    trace: ExecutionTrace = None,
    skill_name: str = None
) -> ErrorFeedback:
    """
    便捷函数：生成错误反馈

    Args:
        error: 错误信息
        context: 执行上下文
        trace: 执行追踪
        skill_name: 技能名称

    Returns:
        错误反馈
    """
    return feedback_generator.generate(error, context, trace, skill_name)


def format_error_for_user(
    error: str,
    skill_name: str = None
) -> str:
    """
    便捷函数：格式化错误为用户友好消息

    Args:
        error: 错误信息
        skill_name: 技能名称

    Returns:
        用户友好的消息
    """
    feedback = feedback_generator.generate(error, skill_name=skill_name)
    return feedback_generator.format_for_user(feedback)
