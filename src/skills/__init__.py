"""
Skills 模块
专业技能系统，提供比 Tools 更高级的能力抽象
支持从 YAML 配置文件加载技能
"""

from .base import (
    BaseSkill,
    SkillConfig,
    SkillContext,
    SkillResult,
    SkillStatus,
    ExecutionStatus,
    SkillMatch,
    ValidationResult,
    RetryDecision,
    ExecutionTrace,
    ExecutionAttempt
)

from .registry import (
    SkillRegistry,
    skill_registry,
    register_skill
)

from .config import (
    SkillSettings,
    SkillDefinition,
    SkillConfigManager
)

from .hot_reload import (
    SkillHotReloader,
    init_hot_reloader,
    get_hot_reloader
)

from .resource_loader import (
    SkillMetadata,
    SkillMetaParser,
    ResourceLoader,
    ReferenceContent,
    AssetContent
)

from .validators import (
    ResultValidator,
    ValidationSchema,
    result_validator,
    validate_result
)

from .retry import (
    RetryManager,
    RetryConfig,
    RetryStrategy,
    RetryState,
    retry_manager,
    create_retry_manager
)

from .feedback import (
    ErrorFeedback,
    FeedbackGenerator,
    FeedbackLevel,
    FeedbackType,
    feedback_generator,
    generate_feedback,
    format_error_for_user
)

__all__ = [
    # 基类
    'BaseSkill',
    'SkillConfig',
    'SkillContext',
    'SkillResult',
    'SkillStatus',
    'ExecutionStatus',
    'SkillMatch',
    'ValidationResult',
    'RetryDecision',
    'ExecutionTrace',
    'ExecutionAttempt',

    # 注册中心
    'SkillRegistry',
    'skill_registry',
    'register_skill',

    # 配置
    'SkillSettings',
    'SkillDefinition',
    'SkillConfigManager',

    # 热加载
    'SkillHotReloader',
    'init_hot_reloader',
    'get_hot_reloader',

    # 资源加载
    'SkillMetadata',
    'SkillMetaParser',
    'ResourceLoader',
    'ReferenceContent',
    'AssetContent',

    # 验证器
    'ResultValidator',
    'ValidationSchema',
    'result_validator',
    'validate_result',

    # 重试
    'RetryManager',
    'RetryConfig',
    'RetryStrategy',
    'RetryState',
    'retry_manager',
    'create_retry_manager',

    # 反馈
    'ErrorFeedback',
    'FeedbackGenerator',
    'FeedbackLevel',
    'FeedbackType',
    'feedback_generator',
    'generate_feedback',
    'format_error_for_user',
]

# 版本信息
__version__ = '2.0.0'
