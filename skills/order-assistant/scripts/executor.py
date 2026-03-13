"""
订单助手技能执行器
"""
import re
import sys
import logging
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent  # skills/order-assistant/scripts -> 项目根
sys.path.insert(0, str(project_root / "src"))

from skills.base import BaseSkill, SkillConfig, SkillContext, SkillResult
from skills.registry import register_skill

# 技能内部日志
logger = logging.getLogger("skill_execution")


@register_skill(config=SkillConfig(
    priority=10,
    stream_enabled=True,
    max_retries=3
))
class OrderAssistantSkill(BaseSkill):
    """订单助手技能"""

    name = "order_assistant"
    description = "专业的订单查询和跟踪服务"
    version = "1.0.0"
    tags = ["订单", "物流", "查询"]

    required_tools = ["order_query"]
    supported_intents = ["order_query", "logistics_query"]

    def execute(self, context: SkillContext) -> SkillResult:
        """执行订单助手技能"""
        try:
            user_input = context.user_input
            intent = context.intent

            # 获取工具
            order_tool = self.get_tool("order_query")
            if not order_tool:
                return SkillResult(
                    success=False,
                    response="",
                    error="订单查询工具不可用"
                )

            # 根据意图分发
            if intent == "order_query":
                return self._handle_order_query(user_input, order_tool)
            elif intent == "logistics_query":
                return self._handle_logistics_query(user_input, order_tool)
            else:
                return SkillResult(
                    success=False,
                    response="",
                    error=f"不支持的意图: {intent}"
                )

        except Exception as e:
            return SkillResult(
                success=False,
                response="",
                error=f"技能执行异常: {str(e)}"
            )

    def _handle_order_query(self, user_input: str, order_tool) -> SkillResult:
        """处理订单查询"""
        logger.info(f"  [OrderAssistant] 开始处理订单查询")
        logger.info(f"  [OrderAssistant] 用户输入: {user_input}")

        # 尝试提取订单号
        order_id_match = re.search(r'(ORD\d{10}|\d{8})', user_input)
        logger.info(f"  [OrderAssistant] 订单号提取结果: {order_id_match}")

        if order_id_match:
            order_id = order_id_match.group()
            logger.info(f"  [OrderAssistant] 提取到订单号: {order_id}")
            logger.info(f"  [OrderAssistant] 调用 order_query 工具...")

            try:
                result = order_tool._run(order_id)
                logger.info(f"  [OrderAssistant] 工具返回成功")
                logger.info(f"  [OrderAssistant] 查询结果: {result[:100]}...")

                return SkillResult(
                    success=True,
                    response=result,
                    data={"order_id": order_id},
                    used_tools=["order_query"]
                )
            except Exception as e:
                logger.error(f"  [OrderAssistant] 工具调用失败: {e}")
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

    def _handle_logistics_query(self, user_input: str, order_tool) -> SkillResult:
        """处理物流查询"""
        return self._handle_order_query(user_input, order_tool)


# 导出技能类
SKILL_CLASS = OrderAssistantSkill
