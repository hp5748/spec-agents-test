"""
技能配置管理模块
"""
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class SkillSettings:
    """技能系统全局设置"""

    # 是否启用技能系统
    enabled: bool = True

    # 技能配置文件路径
    config_file: str = "config/skills_config.json"

    # 是否启用热加载
    hot_reload_enabled: bool = True

    # 热加载检查间隔（秒）
    hot_reload_interval: int = 5

    # 技能目录
    skills_dir: str = "src/skills/implementations"

    # 默认技能配置
    default_priority: int = 10
    default_timeout: int = 30
    default_max_retries: int = 3

    # 降级配置
    fallback_to_tools: bool = True  # 技能不可用时是否降级到工具

    @classmethod
    def from_file(cls, file_path: str) -> 'SkillSettings':
        """从配置文件加载设置"""
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"配置文件不存在: {file_path}，使用默认配置")
            return cls()

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls(**data)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，使用默认配置")
            return cls()

    def to_file(self, file_path: str) -> bool:
        """保存设置到配置文件"""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False


@dataclass
class SkillDefinition:
    """技能定义（用于配置文件）"""

    name: str
    class_name: str
    module: str
    enabled: bool = True
    priority: int = 10
    config: Dict[str, Any] = field(default_factory=dict)


class SkillConfigManager:
    """技能配置管理器"""

    def __init__(self, config_file: str = "config/skills_config.json"):
        self.config_file = config_file
        self._skills: Dict[str, SkillDefinition] = {}
        self._settings: Optional[SkillSettings] = None
        self._load()

    def _load(self):
        """加载配置"""
        path = Path(self.config_file)
        if not path.exists():
            logger.info(f"技能配置文件不存在，将使用默认配置")
            self._settings = SkillSettings()
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 加载全局设置
            settings_data = {k: v for k, v in data.items() if k != 'skills'}
            self._settings = SkillSettings(**settings_data)

            # 加载技能定义
            for skill_data in data.get('skills', []):
                skill_def = SkillDefinition(**skill_data)
                self._skills[skill_def.name] = skill_def

            logger.info(f"成功加载 {len(self._skills)} 个技能配置")

        except Exception as e:
            logger.error(f"加载技能配置失败: {e}")
            self._settings = SkillSettings()

    def save(self):
        """保存配置"""
        data = asdict(self._settings)
        data['skills'] = [asdict(s) for s in self._skills.values()]

        path = Path(self.config_file)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_settings(self) -> SkillSettings:
        """获取全局设置"""
        return self._settings

    def get_skill_config(self, skill_name: str) -> Optional[SkillDefinition]:
        """获取指定技能的配置"""
        return self._skills.get(skill_name)

    def list_skills(self) -> List[SkillDefinition]:
        """列出所有技能配置"""
        return list(self._skills.values())

    def add_skill(self, skill_def: SkillDefinition):
        """添加技能配置"""
        self._skills[skill_def.name] = skill_def
        self.save()

    def remove_skill(self, skill_name: str) -> bool:
        """移除技能配置"""
        if skill_name in self._skills:
            del self._skills[skill_name]
            self.save()
            return True
        return False

    def update_skill(self, skill_name: str, **kwargs) -> bool:
        """更新技能配置"""
        if skill_name not in self._skills:
            return False

        skill_def = self._skills[skill_name]
        for key, value in kwargs.items():
            if hasattr(skill_def, key):
                setattr(skill_def, key, value)

        self.save()
        return True
