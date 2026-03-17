"""
订单助手技能执行器

工具逻辑内聚到 Skill 内部，不依赖外部 tools.py
"""
import re
import logging
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent  # skills/order-assistant/scripts -> 项目根
sys.path.insert(0, str(project_root / "src"))

from skills.base import BaseSkill, SkillConfig, SkillContext, SkillResult
from skills.registry import register_skill

# 技能内部日志
logger = logging.getLogger("skill_execution")


# ============================================
# 内聚的工具逻辑 - 模拟订单数据
# ============================================
MOCK_ORDERS = {
    "12345678": {
        "order_id": "12345678",
        "status": "已发货",
        "tracking_number": "SF1234567890",
        "estimated_delivery": "明天",
        "items": ["iPhone 15 Pro", "手机壳"],
        "total": 8999
    },
    "87654321": {
        "order_id": "87654321",
        "status": "待发货",
        "tracking_number": None,
        "estimated_delivery": "3天后",
        "items": ["MacBook Air"],
        "total": 7999
    },
    "11111111": {
        "order_id": "11111111",
        "status": "已送达",
        "tracking_number": "JD9876543210",
        "estimated_delivery": "已送达",
        "items": ["AirPods Pro"],
        "total": 1899
    }
}


def query_order(order_id: str) -> str:
    """
    查询订单信息（内聚工具函数）

    Args:
        order_id: 订单号

    Returns:
        订单查询结果文本
    """
    order = MOCK_ORDERS.get(order_id)
    if order:
        return f"""订单查询结果：
订单号：{order['order_id']}
状态：{order['status']}
物流单号：{order['tracking_number'] or '暂无'}
预计送达：{order['estimated_delivery']}
商品：{', '.join(order['items'])}
金额：¥{order['total']}"""
    return f"未找到订单号为 {order_id} 的订单，请检查订单号是否正确。"


@register_skill(config=SkillConfig(
    priority=10,
    stream_enabled=True,
    max_retries=3
))
class OrderAssistantSkill(BaseSkill):
    """订单助手技能"""

    name = "order_assistant"
    description = "专业的订单查询服务"
    version = "1.0.0"
    tags = ["订单", "查询"]

    # 只处理订单查询，物流查询已独立为 logistics-assistant
    supported_intents = ["order_query"]

    def execute(self, context: SkillContext) -> SkillResult:
        """执行订单助手技能"""
        try:
            user_input = context.user_input
            return self._handle_order_query(user_input)
        except Exception as e:
            return SkillResult(
                success=False,
                response="",
                error=f"技能执行异常: {str(e)}"
            )

    def _handle_order_query(self, user_input: str) -> SkillResult:
        """处理订单查询"""
        logger.info(f"  [OrderAssistant] 开始处理订单查询")
        logger.info(f"  [OrderAssistant] 用户输入: {user_input}")

        # 尝试提取订单号
        order_id_match = re.search(r'(ORD\d{10}|\d{8})', user_input)
        logger.info(f"  [OrderAssistant] 订单号提取结果: {order_id_match}")

        if order_id_match:
            order_id = order_id_match.group()
            logger.info(f"  [OrderAssistant] 提取到订单号: {order_id}")
            logger.info(f"  [OrderAssistant] 调用内聚的查询函数...")

            try:
                # 使用内聚的查询函数
                result = query_order(order_id)
                logger.info(f"  [OrderAssistant] 查询返回成功")

                return SkillResult(
                    success=True,
                    response=result,
                    data={"order_id": order_id},
                    used_tools=[]  # 不再使用外部工具
                )
            except Exception as e:
                logger.error(f"  [OrderAssistant] 查询失败: {e}")
                return SkillResult(
                    success=False,
                    response="",
                    error=f"查询失败: {str(e)}"
                )
        else:
            logger.info(f"  [OrderAssistant] 未提取到订单号，使用 LLM 生成引导")
            # 没有订单号，提示用户
            if self._llm:
                prompt = f"""用户想查询订单，但未提供有效的订单号。
请友好地引导用户提供订单号。

用户输入: {user_input}

请生成一个简短的回复："""
                response = self._llm.invoke(prompt)
                logger.info(f"  [OrderAssistant] LLM 生成响应: {response.content[:50]}...")
                return SkillResult(
                    success=True,
                    response=response.content,
                    used_tools=[]
                )

            logger.info(f"  [OrderAssistant] 无 LLM，返回默认提示")
            return SkillResult(
                success=True,
                response="请提供您的订单号，格式如：ORD1234567890 或 8位纯数字",
                used_tools=[]
            )


# 导出技能类
SKILL_CLASS = OrderAssistantSkill
