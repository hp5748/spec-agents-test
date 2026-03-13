"""
订单助手技能
专业的订单查询和跟踪服务
"""
import re
from typing import Dict, Any

from skills.base import BaseSkill, SkillConfig, SkillContext, SkillResult
from skills.registry import register_skill
from skills.templates.skill_prompts import ORDER_ASSISTANT_PROMPT
from config import IntentType


@register_skill(config=SkillConfig(priority=10, stream_enabled=True))
class OrderAssistantSkill(BaseSkill):
    """订单助手技能"""

    # 元信息
    name = "order_assistant"
    description = "专业的订单查询和跟踪服务，帮助用户查询订单状态和物流信息"
    version = "1.0.0"
    tags = ["订单", "物流", "查询"]

    # 依赖配置
    required_tools = ["order_query"]
    supported_intents = [IntentType.ORDER_QUERY]

    def get_prompt_template(self) -> str:
        """获取提示词模板"""
        return ORDER_ASSISTANT_PROMPT

    def execute(self, context: SkillContext) -> SkillResult:
        """
        执行订单查询技能

        流程：
        1. 尝试从用户输入中提取订单号
        2. 如果找到订单号，直接查询
        3. 如果没找到，让 LLM 引导用户提供订单号
        """
        used_tools = []

        # 1. 尝试提取订单号
        order_id = self._extract_order_id(context.user_input)

        if order_id:
            # 2. 使用订单查询工具
            tool = self.get_tool("order_query")
            if tool:
                try:
                    tool_result = tool._run(order_id)
                    used_tools.append("order_query")
                    return SkillResult(
                        success=True,
                        response=tool_result,
                        data={"order_id": order_id},
                        used_tools=used_tools
                    )
                except Exception as e:
                    return SkillResult(
                        success=False,
                        response=f"查询订单时出错：{str(e)}",
                        error=str(e)
                    )

        # 3. 没有订单号，使用 LLM 引导用户
        prompt = ORDER_ASSISTANT_PROMPT.format(
            chat_history=context.chat_history,
            user_input=context.user_input
        )

        try:
            response = self._llm.invoke(prompt)
            return SkillResult(
                success=True,
                response=response.content,
                used_tools=used_tools
            )
        except Exception as e:
            return SkillResult(
                success=False,
                response=f"处理请求时出错：{str(e)}",
                error=str(e)
            )

    def _extract_order_id(self, text: str) -> str:
        """
        从文本中提取订单号

        订单号通常是8位数字
        """
        # 匹配8位数字
        match = re.search(r'\b(\d{8})\b', text)
        return match.group(1) if match else None
