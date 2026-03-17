"""
技能资源加载器
解析 SKILL.md 元数据，加载 references 和 assets 资源
"""
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# 尝试导入 yaml
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("PyYAML 未安装，SKILL.md 元数据解析功能不可用")


@dataclass
class SkillMetadata:
    """技能元数据（从 SKILL.md 解析）"""
    # 基础信息
    name: str
    description: str = ""
    version: str = "1.0.0"
    priority: int = 10
    enabled: bool = True

    # 感知增强
    intents: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)

    # 执行配置
    timeout: int = 30
    stream_enabled: bool = True
    load_references: bool = True
    load_assets: bool = True

    # 验证配置
    validation_schema: Optional[str] = None
    required_fields: List[str] = field(default_factory=list)

    # 重试配置
    max_retries: int = 3
    retry_strategy: str = "exponential"  # exponential/linear/fixed
    retry_base_delay: float = 1.0
    retryable_errors: List[str] = field(default_factory=list)

    # 降级配置
    fallback_enabled: bool = True
    fallback_strategy: str = "llm_assist"  # llm_assist/default_message/none
    fallback_message: str = ""

    # 反馈配置
    error_templates: Dict[str, str] = field(default_factory=dict)


class SkillMetaParser:
    """
    SKILL.md 元数据解析器

    解析 YAML Front Matter 格式的技能元数据

    示例格式:
    ---
    name: order-assistant
    description: 订单查询服务
    version: 1.0.0
    priority: 10
    intents:
      - order_query
    keywords:
      - 订单
      - 查询
    ---
    """

    # YAML Front Matter 正则
    FRONT_MATTER_PATTERN = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n',
        re.DOTALL
    )

    @classmethod
    def parse_yaml_front_matter(cls, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        解析 SKILL.md 的 YAML Front Matter

        Args:
            file_path: SKILL.md 文件路径

        Returns:
            解析后的元数据字典，解析失败返回 None
        """
        if not YAML_AVAILABLE:
            logger.error("PyYAML 未安装，无法解析 SKILL.md")
            return None

        if not file_path.exists():
            logger.warning(f"SKILL.md 文件不存在: {file_path}")
            return None

        try:
            content = file_path.read_text(encoding='utf-8')

            # 匹配 Front Matter
            match = cls.FRONT_MATTER_PATTERN.match(content)
            if not match:
                logger.warning(f"SKILL.md 未找到 YAML Front Matter: {file_path}")
                return None

            yaml_content = match.group(1)

            # 解析 YAML
            metadata = yaml.safe_load(yaml_content)

            if not isinstance(metadata, dict):
                logger.warning(f"SKILL.md 元数据格式错误: {file_path}")
                return None

            return metadata

        except yaml.YAMLError as e:
            logger.error(f"YAML 解析错误 {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"读取 SKILL.md 失败 {file_path}: {e}")
            return None

    @classmethod
    def parse_skill_metadata(cls, file_path: Path) -> Optional[SkillMetadata]:
        """
        解析技能元数据并构建 SkillMetadata 对象

        Args:
            file_path: SKILL.md 文件路径

        Returns:
            SkillMetadata 对象，解析失败返回 None
        """
        raw_metadata = cls.parse_yaml_front_matter(file_path)
        if not raw_metadata:
            return None

        try:
            # 提取嵌套配置
            execution_config = raw_metadata.get('execution', {})
            validation_config = raw_metadata.get('validation', {})
            retry_config = raw_metadata.get('retry', {})
            fallback_config = raw_metadata.get('fallback', {})
            feedback_config = raw_metadata.get('feedback', {})

            return SkillMetadata(
                # 基础信息
                name=raw_metadata.get('name', ''),
                description=raw_metadata.get('description', ''),
                version=raw_metadata.get('version', '1.0.0'),
                priority=raw_metadata.get('priority', 10),

                # 感知增强
                intents=raw_metadata.get('intents', []),
                keywords=raw_metadata.get('keywords', []),
                examples=raw_metadata.get('examples', []),

                # 执行配置
                timeout=execution_config.get('timeout', 30),
                stream_enabled=execution_config.get('stream_enabled', True),
                load_references=execution_config.get('load_references', True),
                load_assets=execution_config.get('load_assets', True),

                # 验证配置
                validation_schema=validation_config.get('result_schema'),
                required_fields=validation_config.get('required_fields', []),

                # 重试配置
                max_retries=retry_config.get('max_attempts', 3),
                retry_strategy=retry_config.get('strategy', 'exponential'),
                retry_base_delay=retry_config.get('base_delay', 1.0),
                retryable_errors=retry_config.get('retryable_errors', []),

                # 降级配置
                fallback_enabled=True,
                fallback_strategy=fallback_config.get('strategy', 'llm_assist'),
                fallback_message=fallback_config.get('message', ''),

                # 反馈配置
                error_templates=feedback_config.get('error_templates', {}),
            )

        except Exception as e:
            logger.error(f"构建 SkillMetadata 失败 {file_path}: {e}")
            return None

    @classmethod
    def get_instruction_content(cls, file_path: Path) -> str:
        """
        获取 SKILL.md 中的指令内容（去除 Front Matter 后的部分）

        Args:
            file_path: SKILL.md 文件路径

        Returns:
            指令内容字符串
        """
        if not file_path.exists():
            return ""

        try:
            content = file_path.read_text(encoding='utf-8')

            # 移除 Front Matter
            match = cls.FRONT_MATTER_PATTERN.match(content)
            if match:
                return content[match.end():]

            return content

        except Exception as e:
            logger.error(f"读取 SKILL.md 指令内容失败 {file_path}: {e}")
            return ""


@dataclass
class ReferenceContent:
    """参考资料内容"""
    file_name: str
    file_path: Path
    content: str
    file_type: str  # md, txt, json, etc.


@dataclass
class AssetContent:
    """模板资源内容"""
    file_name: str
    file_path: Path
    content: bytes
    file_type: str  # png, jpg, html, etc.


class ResourceLoader:
    """
    技能资源加载器

    加载技能目录下的 references/ 和 assets/ 资源
    """

    # 支持的文本文件类型
    TEXT_EXTENSIONS = {'.md', '.txt', '.json', '.yaml', '.yml', '.xml', '.csv'}

    # 支持的二进制文件类型
    BINARY_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.html', '.css', '.js'}

    @classmethod
    def load_references(cls, skill_dir: Path) -> List[ReferenceContent]:
        """
        加载 references/ 目录下的参考资料

        Args:
            skill_dir: 技能目录路径

        Returns:
            参考资料内容列表
        """
        references_dir = skill_dir / "references"
        if not references_dir.exists():
            return []

        references = []

        for file_path in references_dir.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                try:
                    ext = file_path.suffix.lower()

                    if ext in cls.TEXT_EXTENSIONS:
                        content = file_path.read_text(encoding='utf-8')
                        references.append(ReferenceContent(
                            file_name=file_path.name,
                            file_path=file_path,
                            content=content,
                            file_type=ext[1:]  # 去掉点号
                        ))
                    else:
                        logger.debug(f"跳过不支持的参考文件类型: {file_path}")

                except Exception as e:
                    logger.warning(f"加载参考文件失败 {file_path}: {e}")

        return references

    @classmethod
    def load_assets(cls, skill_dir: Path) -> List[AssetContent]:
        """
        加载 assets/ 目录下的模板资源

        Args:
            skill_dir: 技能目录路径

        Returns:
            模板资源内容列表
        """
        assets_dir = skill_dir / "assets"
        if not assets_dir.exists():
            return []

        assets = []

        for file_path in assets_dir.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                try:
                    ext = file_path.suffix.lower()

                    if ext in cls.BINARY_EXTENSIONS or ext in cls.TEXT_EXTENSIONS:
                        if ext in cls.TEXT_EXTENSIONS:
                            content = file_path.read_text(encoding='utf-8').encode('utf-8')
                        else:
                            content = file_path.read_bytes()

                        assets.append(AssetContent(
                            file_name=file_path.name,
                            file_path=file_path,
                            content=content,
                            file_type=ext[1:]  # 去掉点号
                        ))

                except Exception as e:
                    logger.warning(f"加载资源文件失败 {file_path}: {e}")

        return assets

    @classmethod
    def load_skill_resources(
        cls,
        skill_dir: Path,
        load_references: bool = True,
        load_assets: bool = True
    ) -> Dict[str, Any]:
        """
        加载技能的所有资源

        Args:
            skill_dir: 技能目录路径
            load_references: 是否加载参考资料
            load_assets: 是否加载模板资源

        Returns:
            资源字典，包含 references 和 assets
        """
        resources = {
            'references': [],
            'assets': []
        }

        if load_references:
            resources['references'] = cls.load_references(skill_dir)

        if load_assets:
            resources['assets'] = cls.load_assets(skill_dir)

        return resources

    @classmethod
    def get_reference_text(cls, references: List[ReferenceContent]) -> str:
        """
        将参考资料合并为文本

        Args:
            references: 参考资料列表

        Returns:
            合并后的文本
        """
        if not references:
            return ""

        parts = []
        for ref in references:
            parts.append(f"### {ref.file_name}\n\n{ref.content}")

        return "\n\n---\n\n".join(parts)
