"""
配置管理模块
管理环境变量和应用配置
"""
import os
import yaml
from typing import Dict, List, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """应用配置类"""

    # 硅基流动 API 配置
    API_KEY: str = os.getenv("SILICONFLOW_API_KEY", "")
    BASE_URL: str = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    MODEL_NAME: str = os.getenv("SILICONFLOW_MODEL", "deepseek-ai/DeepSeek-V3.2")

    # 服务配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # 模型参数
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 2000

    # 记忆配置
    MEMORY_WINDOW: int = 5  # 保留最近5轮对话

    # Skills 配置
    SKILLS_ENABLED: bool = True  # 是否启用技能系统
    SKILLS_HOT_RELOAD: bool = True  # 是否启用技能热加载

    @classmethod
    def validate(cls) -> bool:
        """验证必要配置是否存在"""
        if not cls.API_KEY:
            raise ValueError("SILICONFLOW_API_KEY 未设置，请在 .env 文件中配置")
        return True


class IntentManager:
    """
    意图管理器 - 从配置文件加载

    单例模式，管理意图类型、名称、描述和示例
    """

    _instance: Optional['IntentManager'] = None
    _intents: Dict[str, dict] = {}  # code -> {name, description, examples}
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def load(cls, config_path: str) -> int:
        """
        从 YAML 加载意图配置

        Args:
            config_path: 配置文件路径

        Returns:
            加载的意图数量
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        cls._intents = config.get('intents', {})
        cls._initialized = True

        return len(cls._intents)

    @classmethod
    def get_intents(cls) -> List[str]:
        """获取所有意图代码列表"""
        return list(cls._intents.keys())

    @classmethod
    def get_intent_config(cls, intent: str) -> Optional[dict]:
        """获取意图完整配置"""
        return cls._intents.get(intent)

    @classmethod
    def get_intent_name(cls, intent: str) -> str:
        """获取意图中文名"""
        cfg = cls._intents.get(intent)
        return cfg.get('name', intent) if cfg else intent

    @classmethod
    def get_intent_description(cls, intent: str) -> str:
        """获取意图描述"""
        cfg = cls._intents.get(intent)
        return cfg.get('description', '') if cfg else ''

    @classmethod
    def get_intent_examples(cls, intent: str) -> List[str]:
        """获取意图示例"""
        cfg = cls._intents.get(intent)
        return cfg.get('examples', []) if cfg else []

    @classmethod
    def get_all_configs(cls) -> Dict[str, dict]:
        """获取所有意图配置（用于生成 Prompt）"""
        return cls._intents
