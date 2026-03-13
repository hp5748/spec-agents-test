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
    SkillStatus
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

__all__ = [
    # 基类
    'BaseSkill',
    'SkillConfig',
    'SkillContext',
    'SkillResult',
    'SkillStatus',

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
]

# 版本信息
__version__ = '1.1.0'
