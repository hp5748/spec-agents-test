"""
技能注册中心
管理所有技能的注册、发现和获取
支持从 YAML 配置文件加载技能
"""
import importlib
import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
from dataclasses import dataclass

from .base import BaseSkill, SkillConfig, SkillStatus

logger = logging.getLogger(__name__)

# 尝试导入 yaml
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("PyYAML 未安装，配置文件加载功能不可用。请运行: pip install pyyaml")


@dataclass
class SkillMeta:
    """技能元信息"""
    skill_class: Type[BaseSkill]
    config: SkillConfig
    status: SkillStatus = SkillStatus.ENABLED
    quick_actions: List[Dict[str, str]] = None  # 快捷操作配置


class SkillRegistry:
    """
    技能注册中心（单例模式）

    负责管理所有技能的注册、发现和实例化
    """

    _instance: Optional['SkillRegistry'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._skills: Dict[str, SkillMeta] = {}
        self._intent_map: Dict[str, str] = {}  # intent -> skill_name

    def register(
        self,
        skill_class: Type[BaseSkill],
        config: SkillConfig = None
    ) -> bool:
        """
        注册技能

        Args:
            skill_class: 技能类
            config: 技能配置

        Returns:
            注册是否成功
        """
        try:
            # 创建临时实例获取元信息
            temp_instance = skill_class(config)

            skill_name = temp_instance.name

            if skill_name in self._skills:
                logger.warning(f"技能 {skill_name} 已存在，将被覆盖")

            # 存储技能元信息
            self._skills[skill_name] = SkillMeta(
                skill_class=skill_class,
                config=config or SkillConfig(),
                status=SkillStatus.ENABLED
            )

            # 建立意图映射
            for intent in temp_instance.supported_intents:
                # 检查是否已有技能处理该意图
                if intent in self._intent_map:
                    existing_skill = self._intent_map[intent]
                    existing_meta = self._skills.get(existing_skill)
                    if existing_meta and existing_meta.config.priority >= (config.priority if config else 10):
                        logger.info(f"意图 {intent} 已由 {existing_skill} 处理（优先级更高）")
                        continue
                self._intent_map[intent] = skill_name

            logger.info(f"成功注册技能: {skill_name} (v{temp_instance.version})")
            return True

        except Exception as e:
            logger.error(f"注册技能失败: {e}")
            return False

    def unregister(self, skill_name: str) -> bool:
        """
        注销技能

        Args:
            skill_name: 技能名称

        Returns:
            注销是否成功
        """
        if skill_name not in self._skills:
            logger.warning(f"技能 {skill_name} 不存在")
            return False

        # 获取技能支持的意图
        skill_meta = self._skills[skill_name]
        temp_instance = skill_meta.skill_class(skill_meta.config)

        # 移除意图映射
        for intent in temp_instance.supported_intents:
            if self._intent_map.get(intent) == skill_name:
                del self._intent_map[intent]

        # 移除技能
        del self._skills[skill_name]

        logger.info(f"成功注销技能: {skill_name}")
        return True

    def get_skill(
        self,
        skill_name: str,
        tools: Dict[str, Any] = None,
        llm: Any = None
    ) -> Optional[BaseSkill]:
        """
        获取技能实例

        Args:
            skill_name: 技能名称
            tools: 可用工具字典
            llm: LLM 实例

        Returns:
            技能实例，如果不存在返回 None
        """
        if skill_name not in self._skills:
            logger.warning(f"技能 {skill_name} 不存在")
            return None

        skill_meta = self._skills[skill_name]

        if skill_meta.status == SkillStatus.DISABLED:
            logger.info(f"技能 {skill_name} 已禁用")
            return None

        try:
            # 创建技能实例
            instance = skill_meta.skill_class(skill_meta.config)

            # 注入依赖
            if tools:
                instance.set_tools(tools)
            if llm:
                instance.set_llm(llm)

            return instance

        except Exception as e:
            logger.error(f"创建技能实例失败: {skill_name}, 错误: {e}")
            return None

    def get_skill_by_intent(
        self,
        intent: str,
        tools: Dict[str, Any] = None,
        llm: Any = None
    ) -> Optional[BaseSkill]:
        """
        根据意图获取技能实例

        Args:
            intent: 用户意图
            tools: 可用工具字典
            llm: LLM 实例

        Returns:
            技能实例，如果没有匹配的技能返回 None
        """
        logger.info(f"[SkillRegistry] 查找意图映射: intent={intent}")
        logger.info(f"[SkillRegistry] 当前意图映射表: {self._intent_map}")

        skill_name = self._intent_map.get(intent)
        if not skill_name:
            logger.info(f"[SkillRegistry] 未找到匹配的技能: intent={intent}")
            return None

        logger.info(f"[SkillRegistry] 匹配到技能: {skill_name}")
        return self.get_skill(skill_name, tools, llm)

    def list_skills(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册技能

        Returns:
            技能信息列表
        """
        result = []
        for name, meta in self._skills.items():
            temp_instance = meta.skill_class(meta.config)
            result.append({
                "name": temp_instance.name,
                "description": temp_instance.description,
                "version": temp_instance.version,
                "tags": temp_instance.tags,
                "supported_intents": temp_instance.supported_intents,
                "required_tools": temp_instance.required_tools,
                "status": meta.status.value,
                "priority": meta.config.priority,
                "quick_actions": meta.quick_actions or []  # 快捷操作
            })
        return result

    def auto_discover(self, package_path: str = None) -> int:
        """
        自动发现并注册技能

        Args:
            package_path: 技能包路径，默认为 skills/implementations

        Returns:
            成功注册的技能数量
        """
        if package_path is None:
            # 默认在 implementations 目录下查找
            current_dir = Path(__file__).parent / "implementations"
        else:
            current_dir = Path(package_path)

        if not current_dir.exists():
            logger.warning(f"技能目录不存在: {current_dir}")
            return 0

        count = 0
        for py_file in current_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            module_name = py_file.stem
            try:
                # 动态导入模块
                module = importlib.import_module(
                    f"skills.implementations.{module_name}"
                )

                # 查找所有 BaseSkill 子类
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                        issubclass(obj, BaseSkill) and
                        obj != BaseSkill):

                        # 检查是否有 register_skill 装饰器的配置
                        config = getattr(obj, '_skill_config', None)

                        if self.register(obj, config):
                            count += 1

            except Exception as e:
                logger.error(f"导入技能模块失败: {module_name}, 错误: {e}")

        logger.info(f"自动发现完成，共注册 {count} 个技能")
        return count

    def reload_all(self) -> int:
        """
        重新加载所有技能

        Returns:
            成功注册的技能数量
        """
        # 清空现有注册
        self._skills.clear()
        self._intent_map.clear()

        # 重新发现
        return self.auto_discover()

    def load_from_config(self, config_path: str = None) -> int:
        """
        从 YAML 配置文件加载技能

        Args:
            config_path: 配置文件路径，默认为项目根目录的 skills/skills.yaml

        Returns:
            成功注册的技能数量
        """
        if not YAML_AVAILABLE:
            logger.error("PyYAML 未安装，无法加载配置文件")
            return 0

        # 确定配置文件路径
        if config_path is None:
            # 尝试几个默认位置
            project_root = Path(__file__).parent.parent.parent
            possible_paths = [
                project_root / "skills" / "skills.yaml",
                project_root / "skills" / "skills.yml",
                project_root / "config" / "skills.yaml",
            ]
            config_path = None
            for p in possible_paths:
                if p.exists():
                    config_path = p
                    break

            if config_path is None:
                logger.warning("未找到技能配置文件")
                return 0
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            logger.error(f"配置文件不存在: {config_path}")
            return 0

        # 读取配置
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"读取配置文件失败: {e}")
            return 0

        # 检查全局开关
        global_config = config.get('global', {})
        if not global_config.get('enabled', True):
            logger.info("技能系统已禁用")
            return 0

        # 加载技能
        skills_config = config.get('skills', {})
        count = 0

        for skill_name, skill_def in skills_config.items():
            if not skill_def.get('enabled', True):
                logger.info(f"技能 {skill_name} 已禁用，跳过")
                continue

            try:
                # 加载技能模块
                skill_instance = self._load_skill_from_definition(
                    skill_name, skill_def, config_path.parent
                )
                if skill_instance:
                    count += 1
            except Exception as e:
                logger.error(f"加载技能 {skill_name} 失败: {e}")

        logger.info(f"从配置文件加载完成，共注册 {count} 个技能")
        return count

    def _load_skill_from_definition(
        self,
        skill_name: str,
        skill_def: Dict[str, Any],
        skills_dir: Path
    ) -> Optional[BaseSkill]:
        """
        根据技能定义加载技能

        新目录结构:
        skills/
        ├── skills.yaml
        └── skill-name/
            ├── SKILL.md
            └── scripts/
                └── executor.py

        Args:
            skill_name: 技能名称
            skill_def: 技能定义（来自 YAML）
            skills_dir: 技能根目录

        Returns:
            技能实例
        """
        # 新结构：技能目录下的 scripts/executor.py
        skill_dir = skills_dir / skill_name
        executor_path = skill_dir / "scripts" / "executor.py"

        if not executor_path.exists():
            logger.error(f"技能执行器不存在: {executor_path}")
            return None

        # 动态加载模块
        module_name = f"skills_dynamic.{skill_name}"

        # 添加项目根目录到 sys.path
        project_root = skills_dir.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        try:
            # 使用 importlib 加载
            spec = importlib.util.spec_from_file_location(module_name, executor_path)
            if spec is None or spec.loader is None:
                logger.error(f"无法创建模块规范: {executor_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # 查找技能类
            skill_class = None

            # 优先查找 SKILL_CLASS 导出
            if hasattr(module, 'SKILL_CLASS'):
                skill_class = module.SKILL_CLASS
            else:
                # 遍历查找 BaseSkill 子类
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                        issubclass(obj, BaseSkill) and
                        obj != BaseSkill):
                        skill_class = obj
                        break

            if skill_class is None:
                logger.error(f"在模块中未找到技能类")
                return None

            # 构建配置
            config_dict = skill_def.get('config', {})
            config = SkillConfig(
                priority=skill_def.get('priority', 10),
                enabled=skill_def.get('enabled', True),
                max_retries=config_dict.get('max_retries', 3),
                timeout=config_dict.get('timeout', 30),
                stream_enabled=config_dict.get('stream_enabled', True),
            )

            # 检查是否有装饰器配置
            decorator_config = getattr(skill_class, '_skill_config', None)
            if decorator_config:
                config = decorator_config

            # 注册技能
            if self.register(skill_class, config):
                # 保存快捷操作配置到元信息
                quick_actions = skill_def.get('quick_actions', [])
                # 使用技能实例的 name 作为 key（与 register 方法一致）
                temp_instance = skill_class(config)
                skill_key = temp_instance.name
                if skill_key in self._skills:
                    self._skills[skill_key].quick_actions = quick_actions
                return skill_class

            return None

        except Exception as e:
            logger.error(f"加载技能模块失败: {skill_name}, 错误: {e}")
            import traceback
            traceback.print_exc()
            return None

    def save_config(self, config_path: str = None) -> bool:
        """
        保存当前技能配置到 YAML 文件

        Args:
            config_path: 配置文件路径

        Returns:
            是否成功
        """
        if not YAML_AVAILABLE:
            logger.error("PyYAML 未安装，无法保存配置文件")
            return False

        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "skills" / "skills.yaml"
        else:
            config_path = Path(config_path)

        # 构建配置数据
        config = {
            'global': {
                'enabled': True,
                'hot_reload': True,
                'default_timeout': 30,
                'default_retries': 3
            },
            'skills': {}
        }

        for name, meta in self._skills.items():
            temp_instance = meta.skill_class(meta.config)
            config['skills'][name] = {
                'name': temp_instance.name,
                'description': temp_instance.description,
                'version': temp_instance.version,
                'enabled': meta.status == SkillStatus.ENABLED,
                'priority': meta.config.priority,
                'intents': temp_instance.supported_intents,
                'required_tools': temp_instance.required_tools,
                'config': {
                    'max_retries': meta.config.max_retries,
                    'timeout': meta.config.timeout,
                    'stream_enabled': meta.config.stream_enabled
                }
            }

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            logger.info(f"配置已保存到: {config_path}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def enable_skill(self, skill_name: str) -> bool:
        """启用技能"""
        if skill_name not in self._skills:
            return False
        self._skills[skill_name].status = SkillStatus.ENABLED
        return True

    def disable_skill(self, skill_name: str) -> bool:
        """禁用技能"""
        if skill_name not in self._skills:
            return False
        self._skills[skill_name].status = SkillStatus.DISABLED
        return True


def register_skill(config: SkillConfig = None):
    """
    技能注册装饰器

    使用方式:
        @register_skill(config=SkillConfig(priority=10))
        class MySkill(BaseSkill):
            ...
    """
    def decorator(cls):
        # 存储配置到类属性
        cls._skill_config = config
        return cls
    return decorator


# 全局技能注册中心实例
skill_registry = SkillRegistry()
