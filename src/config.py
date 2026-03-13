"""
配置管理模块
管理环境变量和应用配置
"""
import os
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


# 意图类型枚举
class IntentType:
    """用户意图类型"""
    ORDER_QUERY = "order_query"      # 订单查询
    PRODUCT_CONSULT = "product_consult"  # 商品咨询
    COMPLAINT = "complaint"          # 投诉处理
    GENERAL_QA = "general_qa"        # 通用问答


# 意图中文名称映射
INTENT_NAMES = {
    IntentType.ORDER_QUERY: "订单查询",
    IntentType.PRODUCT_CONSULT: "商品咨询",
    IntentType.COMPLAINT: "投诉处理",
    IntentType.GENERAL_QA: "通用问答",
}
