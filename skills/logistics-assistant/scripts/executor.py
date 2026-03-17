"""
物流助手技能执行器
"""
import re
import logging
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from skills.base import BaseSkill, SkillConfig, SkillContext, SkillResult
from skills.registry import register_skill

logger = logging.getLogger("skill_execution")

# 模拟物流数据
MOCK_LOGISTICS = {
    "SF1234567890": {
        "tracking_number": "SF1234567890",
        "carrier": "顺丰速运",
        "status": "运输中",
        "current_location": "北京分拣中心",
        "estimated_delivery": "明天 14:00",
        "timeline": [
            {"time": "2026-03-16 08:00", "event": "已发货"},
            {"time": "2026-03-16 10:30", "event": "到达北京转运中心"},
            {"time": "2026-03-16 14:00", "event": "运输中"},
        ]
    },
    "JD9876543210": {
        "tracking_number": "JD9876543210",
        "carrier": "京东物流",
        "status": "派送中",
        "current_location": "上海浦东站点",
        "estimated_delivery": "今天 18:00",
        "timeline": [
            {"time": "2026-03-15 20:00", "event": "已发货"},
            {"time": "2026-03-16 06:00", "event": "到达上海分拣中心"},
            {"time": "2026-03-16 10:00", "event": "派送中，快递员：张三 138****1234"},
        ]
    }
}


def query_logistics(tracking_number: str) -> str:
    """查询物流信息"""
    logistics = MOCK_LOGISTICS.get(tracking_number)
    if logistics:
        timeline_str = "\n".join([
            f"  - {t['time']}: {t['event']}"
            for t in logistics['timeline']
        ])
        return f"""物流查询结果：
物流单号：{logistics['tracking_number']}
承运商：{logistics['carrier']}
状态：{logistics['status']}
当前位置：{logistics['current_location']}
预计送达：{logistics['estimated_delivery']}

物流轨迹：
{timeline_str}"""
    return f"未找到物流单号 {tracking_number} 的信息，请检查单号是否正确。"


@register_skill(config=SkillConfig(priority=10))
class LogisticsAssistantSkill(BaseSkill):
    """物流助手技能"""
    name = "logistics_assistant"
    description = "专业的物流跟踪查询服务"
    version = "1.0.0"
    supported_intents = ["logistics_query"]

    def execute(self, context: SkillContext) -> SkillResult:
        try:
            user_input = context.user_input
            # 提取物流单号（SF/JD/EMS开头 + 数字）
            tracking_match = re.search(r'(SF|JD|EMS)\d{10,}', user_input)

            if tracking_match:
                tracking_number = tracking_match.group()
                result = query_logistics(tracking_number)
                return SkillResult(success=True, response=result, used_tools=[])
            else:
                return SkillResult(
                    success=True,
                    response="请提供您的物流单号，如：SF1234567890、JD9876543210",
                    used_tools=[]
                )
        except Exception as e:
            return SkillResult(success=False, response="", error=str(e))


SKILL_CLASS = LogisticsAssistantSkill
