"""
投诉处理技能执行器
"""
import re
import logging
from pathlib import Path
import sys
from datetime import datetime

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from skills.base import BaseSkill, SkillConfig, SkillContext, SkillResult
from skills.registry import register_skill

logger = logging.getLogger("skill_execution")

# 模拟工单存储
MOCK_TICKETS = {}
TICKET_COUNTER = 1000


def create_ticket(issue_type: str, description: str) -> str:
    """创建工单"""
    global TICKET_COUNTER
    TICKET_COUNTER += 1
    ticket_id = f"TK{datetime.now().strftime('%Y%m%d')}{TICKET_COUNTER}"

    MOCK_TICKETS[ticket_id] = {
        "ticket_id": ticket_id,
        "type": issue_type,
        "description": description,
        "status": "待处理",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    return f"""工单创建成功！

工单号：{ticket_id}
问题类型：{issue_type}
问题描述：{description}
状态：待处理
创建时间：{MOCK_TICKETS[ticket_id]['created_at']}

我们会尽快处理，处理结果将通过短信通知您。如有疑问，请拨打客服热线 400-123-4567。"""


def query_ticket(ticket_id: str) -> str:
    """查询工单状态"""
    ticket = MOCK_TICKETS.get(ticket_id)
    if ticket:
        return f"""工单查询结果：
工单号：{ticket['ticket_id']}
问题类型：{ticket['type']}
状态：{ticket['status']}
创建时间：{ticket['created_at']}"""
    return f"未找到工单 {ticket_id}，请检查工单号是否正确。"


@register_skill(config=SkillConfig(priority=10))
class ComplaintAssistantSkill(BaseSkill):
    """投诉处理技能"""
    name = "complaint_assistant"
    description = "专业的投诉处理和工单服务"
    version = "1.0.0"
    supported_intents = ["complaint"]

    def execute(self, context: SkillContext) -> SkillResult:
        try:
            user_input = context.user_input

            # 查询工单
            ticket_match = re.search(r'TK\d{12}', user_input)
            if ticket_match:
                ticket_id = ticket_match.group()
                return SkillResult(
                    success=True,
                    response=query_ticket(ticket_id),
                    used_tools=[]
                )

            # 创建工单
            if "投诉" in user_input or "反馈" in user_input or "问题" in user_input:
                # 判断问题类型
                issue_type = "其他问题"
                if "质量" in user_input:
                    issue_type = "质量问题"
                elif "服务" in user_input or "态度" in user_input:
                    issue_type = "服务投诉"
                elif "物流" in user_input or "快递" in user_input:
                    issue_type = "物流问题"
                elif "售后" in user_input:
                    issue_type = "售后问题"

                # 创建工单
                result = create_ticket(issue_type, user_input)
                return SkillResult(success=True, response=result, used_tools=[])

            # 默认：使用 LLM 引导
            if self._llm:
                response = self._llm.invoke(f"用户可能有投诉意向：{user_input}，请友好地了解用户的具体问题并引导其描述。")
                return SkillResult(success=True, response=response.content, used_tools=[])

            return SkillResult(
                success=True,
                response="请问您遇到了什么问题？请详细描述，我们会尽快为您处理。",
                used_tools=[]
            )

        except Exception as e:
            return SkillResult(success=False, response="", error=str(e))


SKILL_CLASS = ComplaintAssistantSkill
