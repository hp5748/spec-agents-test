"""
投诉处理技能
专业的投诉接收和处理服务
"""
from typing import Dict, Any

from skills.base import BaseSkill, SkillConfig, SkillContext, SkillResult
from skills.registry import register_skill
from skills.templates.skill_prompts import COMPLAINT_HANDLER_PROMPT
from config import IntentType


@register_skill(config=SkillConfig(priority=10, stream_enabled=True))
class ComplaintHandlerSkill(BaseSkill):
    """投诉处理技能"""

    # 元信息
    name = "complaint_handler"
    description = "专业的投诉处理服务，倾听用户反馈并提供解决方案"
    version = "1.0.0"
    tags = ["投诉", "反馈", "客服"]

    # 依赖配置
    required_tools = ["create_ticket"]
    supported_intents = [IntentType.COMPLAINT]

    def get_prompt_template(self) -> str:
        """获取提示词模板"""
        return COMPLAINT_HANDLER_PROMPT

    def execute(self, context: SkillContext) -> SkillResult:
        """
        执行投诉处理技能

        流程：
        1. 使用 LLM 分析投诉内容
        2. 创建工单记录投诉
        3. 生成友好的响应
        """
        used_tools = []

        # 1. 分析投诉内容
        analysis_prompt = f"""分析以下用户投诉内容，提取关键信息：

用户输入：{context.user_input}

请提取：
1. 问题类型（如：质量问题、物流问题、服务态度、价格问题等）
2. 问题严重程度（1-5分）
3. 是否需要紧急处理

请以JSON格式返回结果。"""

        issue_type = "用户投诉"
        severity = 3
        urgent = False

        try:
            analysis = self._llm.invoke(analysis_prompt)
            # 简单解析（实际项目中应该更健壮）
            if "质量问题" in analysis.content:
                issue_type = "质量问题"
            elif "物流" in analysis.content:
                issue_type = "物流问题"
            elif "服务" in analysis.content:
                issue_type = "服务问题"
        except Exception:
            pass  # 使用默认值

        # 2. 创建工单
        tool = self.get_tool("create_ticket")
        ticket_result = ""

        if tool:
            try:
                ticket_result = tool._run(
                    issue_type=issue_type,
                    description=context.user_input
                )
                used_tools.append("create_ticket")
            except Exception as e:
                ticket_result = f"创建工单时出错：{str(e)}"

        # 3. 生成响应
        enhanced_prompt = f"""{COMPLAINT_HANDLER_PROMPT.format(
            chat_history=context.chat_history,
            user_input=context.user_input
        )}

工单创建结果：
{ticket_result}

请根据以上信息，以真诚、负责的态度回复用户。"""

        try:
            response = self._llm.invoke(enhanced_prompt)
            return SkillResult(
                success=True,
                response=response.content,
                data={
                    "issue_type": issue_type,
                    "ticket_result": ticket_result
                },
                used_tools=used_tools
            )
        except Exception as e:
            # 如果 LLM 失败，返回工单结果
            if ticket_result:
                return SkillResult(
                    success=True,
                    response=f"感谢您的反馈！{ticket_result}",
                    data={"ticket_result": ticket_result},
                    used_tools=used_tools
                )
            return SkillResult(
                success=False,
                response=f"处理请求时出错：{str(e)}",
                error=str(e)
            )
