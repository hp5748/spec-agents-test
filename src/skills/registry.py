"""
技能注册中心
管理所有技能的注册、发现和获取
支持从 SKILL.md 扫描元数据，从 skills.yaml 加载 quick_actions
"""
import importlib
import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type, Any, Tuple
from dataclasses import dataclass, field

from .base import (
    BaseSkill, SkillConfig, SkillStatus, SkillMatch,
    SkillResult, SkillContext
)
from .resource_loader import (
    SkillMetaParser, SkillMetadata, ResourceLoader
)

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
    metadata: SkillMetadata = None  # 从 SKILL.md 解析的元数据
    skill_dir: Path = None  # 技能目录路径


class SkillRegistry:
    """
    技能注册中心（单例模式）

    负责管理所有技能的注册、发现和实例化
    支持：
    - 从 SKILL.md 扫描元数据
    - 从 skills.yaml 加载 quick_actions
    - 多 Skill 匹配与置信度评估
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
        self._config_path: Optional[str] = None  # 保存配置文件路径
        self._quick_actions: Dict[str, List[Dict[str, str]]] = {}  # 快捷操作配置

    def register(
        self,
        skill_class: Type[BaseSkill],
        config: SkillConfig = None,
        metadata: SkillMetadata = None,
        skill_dir: Path = None
    ) -> bool:
        """
        注册技能

        Args:
            skill_class: 技能类
            config: 技能配置
            metadata: 从 SKILL.md 解析的元数据
            skill_dir: 技能目录路径

        Returns:
            注册是否成功
        """
        try:
            # 创建临时实例获取元信息
            temp_instance = skill_class(config)

            skill_name = temp_instance.name

            if skill_name in self._skills:
                logger.warning(f"技能 {skill_name} 已存在，将被覆盖")

            # 使用元数据更新配置（如果有的话）
            if metadata:
                config = config or SkillConfig()
                config.priority = metadata.priority
                config.timeout = metadata.timeout
                config.max_retries = metadata.max_retries
                config.retry_strategy = metadata.retry_strategy
                config.retry_base_delay = metadata.retry_base_delay
                config.fallback_strategy = metadata.fallback_strategy
                config.fallback_message = metadata.fallback_message
                config.validation_schema = metadata.validation_schema

            # 存储技能元信息
            self._skills[skill_name] = SkillMeta(
                skill_class=skill_class,
                config=config or SkillConfig(),
                status=SkillStatus.ENABLED,
                metadata=metadata,
                skill_dir=skill_dir
            )

            # 建立意图映射
            intents = metadata.intents if metadata else temp_instance.supported_intents
            for intent in intents:
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

    # ============================================================
    # 新增：多 Skill 匹配与置信度评估
    # ============================================================

    def find_matching_skills(
        self,
        intent: str,
        user_input: str,
        top_k: int = 3
    ) -> List[SkillMatch]:
        """
        多 Skill 匹配，返回带置信度的排序列表

        Args:
            intent: 用户意图
            user_input: 用户输入
            top_k: 返回的最大匹配数量

        Returns:
            匹配的技能列表（按置信度排序）
        """
        matches = []
        user_input_lower = user_input.lower()

        for skill_name, skill_meta in self._skills.items():
            if skill_meta.status == SkillStatus.DISABLED:
                continue

            confidence = 0.0
            matched_intents = []
            matched_keywords = []

            # 1. 意图匹配
            metadata = skill_meta.metadata
            intents = metadata.intents if metadata else []

            if intent in intents:
                confidence += 0.5  # 意图匹配贡献 50% 置信度
                matched_intents.append(intent)

            # 2. 关键词匹配
            keywords = metadata.keywords if metadata else []
            for keyword in keywords:
                if keyword.lower() in user_input_lower:
                    confidence += 0.1  # 每个关键词贡献 10%
                    matched_keywords.append(keyword)

            # 限制置信度上限
            confidence = min(confidence, 1.0)

            # 如果有匹配，添加到列表
            if confidence > 0:
                matches.append(SkillMatch(
                    skill_name=skill_name,
                    confidence=confidence,
                    matched_intents=matched_intents,
                    matched_keywords=matched_keywords,
                    priority=skill_meta.config.priority
                ))

        # 排序：先按置信度，再按优先级
        matches.sort(key=lambda m: (-m.confidence, -m.priority))

        return matches[:top_k]

    def select_best_skill(
        self,
        matches: List[SkillMatch],
        strategy: str = "confidence"
    ) -> Optional[SkillMatch]:
        """
        选择最佳 Skill

        Args:
            matches: 匹配的技能列表
            strategy: 选择策略 (confidence/priority/first)

        Returns:
            最佳匹配，如果没有匹配返回 None
        """
        if not matches:
            return None

        if strategy == "confidence":
            # 已经在 find_matching_skills 中按置信度排序
            return matches[0]

        elif strategy == "priority":
            # 按优先级排序
            sorted_matches = sorted(matches, key=lambda m: -m.priority)
            return sorted_matches[0]

        elif strategy == "first":
            return matches[0]

        return matches[0]

    # ============================================================
    # 原有方法
    # ============================================================

    def list_skills(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册技能

        Returns:
            技能信息列表
        """
        result = []
        for name, meta in self._skills.items():
            temp_instance = meta.skill_class(meta.config)

            # 合并快捷操作（从配置文件 + 元数据）
            quick_actions = meta.quick_actions or []
            if name in self._quick_actions:
                quick_actions = self._quick_actions[name]

            result.append({
                "name": temp_instance.name,
                "description": temp_instance.description,
                "version": temp_instance.version,
                "tags": temp_instance.tags,
                "supported_intents": temp_instance.supported_intents,
                "required_tools": temp_instance.required_tools,
                "status": meta.status.value,
                "priority": meta.config.priority,
                "quick_actions": quick_actions
            })
        return result

    def get_quick_actions(self) -> Dict[str, List[Dict[str, str]]]:
        """
        获取所有快捷操作配置

        Returns:
            技能名称 -> 快捷操作列表的映射
        """
        result = {}

        # 从配置文件加载的快捷操作
        result.update(self._quick_actions)

        # 补充技能本身的快捷操作
        for name, meta in self._skills.items():
            if name not in result and meta.quick_actions:
                result[name] = meta.quick_actions

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

        # 优先从配置文件重新加载（如果有保存的路径）
        if self._config_path and Path(self._config_path).exists():
            return self.load_from_config(self._config_path)

        # 降级到自动发现
        return self.auto_discover()

    def load_from_config(self, config_path: str = None) -> int:
        """
        从 YAML 配置文件加载技能

        新逻辑：
        1. 扫描 skills/ 目录下的所有 SKILL.md
        2. 从 SKILL.md 解析元数据
        3. 从 skills.yaml 读取 quick_actions 并合并

        Args:
            config_path: 配置文件路径，默认为项目根目录的 config/skills.yaml

        Returns:
            成功注册的技能数量
        """
        if not YAML_AVAILABLE:
            logger.error("PyYAML 未安装，无法加载配置文件")
            return 0

        # 确定配置文件路径
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            possible_paths = [
                project_root / "config" / "skills.yaml",   # 优先使用 config 目录
                project_root / "skills" / "skills.yaml",
                project_root / "skills" / "skills.yml",
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

        # 保存配置文件路径（用于后续重载）
        self._config_path = str(config_path)

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

        # 加载快捷操作配置
        self._quick_actions = config.get('quick_actions', {})

        # 技能目录
        project_root = config_path.parent.parent  # config/ -> project_root
        skills_dir = project_root / "skills"

        count = 0

        # 扫描 skills/ 目录下的所有技能
        for skill_folder in skills_dir.iterdir():
            if not skill_folder.is_dir():
                continue
            if skill_folder.name.startswith('_') or skill_folder.name.startswith('.'):
                continue

            skill_md_path = skill_folder / "SKILL.md"

            if not skill_md_path.exists():
                logger.debug(f"跳过无 SKILL.md 的目录: {skill_folder}")
                continue

            try:
                # 从 SKILL.md 解析元数据
                metadata = SkillMetaParser.parse_skill_metadata(skill_md_path)

                if not metadata or not metadata.name:
                    logger.warning(f"无法解析技能元数据: {skill_md_path}")
                    continue

                # 加载技能模块
                skill_class = self._load_skill_class(skill_folder, metadata)

                if skill_class:
                    # 构建 SkillConfig
                    skill_config = SkillConfig(
                        priority=metadata.priority,
                        enabled=True,
                        max_retries=metadata.max_retries,
                        timeout=metadata.timeout,
                        retry_strategy=metadata.retry_strategy,
                        retry_base_delay=metadata.retry_base_delay,
                        validation_schema=metadata.validation_schema,
                        fallback_strategy=metadata.fallback_strategy,
                        fallback_message=metadata.fallback_message
                    )

                    # 注册技能
                    if self.register(skill_class, skill_config, metadata, skill_folder):
                        # 设置快捷操作
                        skill_name = skill_class().name
                        if skill_name in self._skills:
                            # 优先使用配置文件中的快捷操作
                            folder_name = skill_folder.name
                            if folder_name in self._quick_actions:
                                self._skills[skill_name].quick_actions = self._quick_actions[folder_name]
                        count += 1

            except Exception as e:
                logger.error(f"加载技能 {skill_folder.name} 失败: {e}")

        logger.info(f"从配置文件加载完成，共注册 {count} 个技能")
        return count

    def _load_skill_resources(
        self,
        skill_dir: Path,
        load_references: bool = True,
        load_assets: bool = True
    ) -> Dict[str, Any]:
        """
        加载技能资源

        Args:
            skill_dir: 技能目录
            load_references: 是否加载参考资料
            load_assets: 是否加载模板资源

        Returns:
            资源字典
        """
        return ResourceLoader.load_skill_resources(
            skill_dir,
            load_references=load_references,
            load_assets=load_assets
        )

    def _load_skill_class(
        self,
        skill_dir: Path,
        metadata: SkillMetadata
    ) -> Optional[Type[BaseSkill]]:
        """
        加载技能类

        Args:
            skill_dir: 技能目录
            metadata: 技能元数据

        Returns:
            技能类，加载失败返回 None
        """
        executor_path = skill_dir / "scripts" / "executor.py"

        if not executor_path.exists():
            logger.warning(f"技能执行器不存在: {executor_path}")
            return None

        # 动态加载模块
        module_name = f"skills_dynamic.{metadata.name}"

        # 添加项目根目录到 sys.path
        project_root = skill_dir.parent.parent
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

            return skill_class

        except Exception as e:
            logger.error(f"加载技能模块失败: {metadata.name}, 错误: {e}")
            import traceback
            traceback.print_exc()
            return None

    def auto_discover_from_skill_md(self, skills_dir: Path = None) -> int:
        """
        从 SKILL.md 自动发现技能

        Args:
            skills_dir: 技能目录，默认为项目根目录的 skills/

        Returns:
            成功注册的技能数量
        """
        if skills_dir is None:
            project_root = Path(__file__).parent.parent.parent
            skills_dir = project_root / "skills"

        if not skills_dir.exists():
            logger.warning(f"技能目录不存在: {skills_dir}")
            return 0

        count = 0

        for skill_folder in skills_dir.iterdir():
            if not skill_folder.is_dir():
                continue
            if skill_folder.name.startswith('_') or skill_folder.name.startswith('.'):
                continue

            skill_md_path = skill_folder / "SKILL.md"

            if not skill_md_path.exists():
                continue

            try:
                metadata = SkillMetaParser.parse_skill_metadata(skill_md_path)

                if not metadata or not metadata.name:
                    continue

                skill_class = self._load_skill_class(skill_folder, metadata)

                if skill_class and self.register(skill_class, metadata=metadata, skill_dir=skill_folder):
                    count += 1

            except Exception as e:
                logger.error(f"发现技能失败 {skill_folder.name}: {e}")

        logger.info(f"从 SKILL.md 发现完成，共注册 {count} 个技能")
        return count

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
            config_path = project_root / "config" / "skills.yaml"
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
            'quick_actions': self._quick_actions
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
