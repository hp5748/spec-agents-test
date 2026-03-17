"""
商品咨询技能执行器
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

# 模拟商品数据
MOCK_PRODUCTS = {
    "手机": [
        {"name": "iPhone 15 Pro", "price": 8999, "stock": True, "desc": "最新款苹果手机，A17芯片"},
        {"name": "华为 Mate 60 Pro", "price": 6999, "stock": True, "desc": "麒麟9000S芯片，卫星通信"},
        {"name": "小米 14", "price": 3999, "stock": True, "desc": "骁龙8 Gen3，性价比之选"},
    ],
    "笔记本": [
        {"name": "MacBook Air M3", "price": 9499, "stock": True, "desc": "轻薄本，续航出色"},
        {"name": "ThinkPad X1 Carbon", "price": 12999, "stock": False, "desc": "商务旗舰，键盘手感极佳"},
    ]
}


def recommend_products(category: str, budget: int = None) -> str:
    """商品推荐"""
    products = MOCK_PRODUCTS.get(category, [])
    if not products:
        return f"暂无 {category} 类别的商品，请咨询客服了解详情。"

    result = f"【{category}推荐】\n"
    for p in products:
        if budget and p['price'] > budget:
            continue
        stock_status = "有货" if p['stock'] else "缺货"
        result += f"\n- {p['name']}\n"
        result += f"  价格：¥{p['price']}\n"
        result += f"  库存：{stock_status}\n"
        result += f"  介绍：{p['desc']}\n"
    return result


def query_price(product_name: str) -> str:
    """价格查询"""
    for category, products in MOCK_PRODUCTS.items():
        for p in products:
            if product_name.lower() in p['name'].lower():
                stock_status = "有货" if p['stock'] else "缺货"
                return f"{p['name']} 当前价格：¥{p['price']}，库存：{stock_status}"
    return f"未找到 {product_name} 的价格信息，请确认商品名称。"


@register_skill(config=SkillConfig(priority=10))
class ProductAssistantSkill(BaseSkill):
    """商品咨询技能"""
    name = "product_assistant"
    description = "专业的商品推荐和咨询服务"
    version = "1.0.0"
    supported_intents = ["product_consult"]

    def execute(self, context: SkillContext) -> SkillResult:
        try:
            user_input = context.user_input

            # 推荐类查询
            if "推荐" in user_input or "有什么" in user_input:
                for category in MOCK_PRODUCTS.keys():
                    if category in user_input:
                        return SkillResult(
                            success=True,
                            response=recommend_products(category),
                            used_tools=[]
                        )
                # 无匹配类别，使用 LLM 生成响应
                if self._llm:
                    response = self._llm.invoke(f"用户咨询商品推荐：{user_input}，请友好地引导用户提供更具体的需求。")
                    return SkillResult(success=True, response=response.content, used_tools=[])
                return SkillResult(success=True, response="请问您想了解哪类商品？如手机、笔记本等。", used_tools=[])

            # 价格查询
            if "多少钱" in user_input or "价格" in user_input:
                for category, products in MOCK_PRODUCTS.items():
                    for p in products:
                        if p['name'].split()[0] in user_input:
                            return SkillResult(
                                success=True,
                                response=query_price(p['name']),
                                used_tools=[]
                            )

            # 默认：使用 LLM
            if self._llm:
                response = self._llm.invoke(f"用户咨询：{user_input}，请提供专业的商品咨询服务。")
                return SkillResult(success=True, response=response.content, used_tools=[])

            return SkillResult(success=True, response="请问有什么可以帮您？", used_tools=[])

        except Exception as e:
            return SkillResult(success=False, response="", error=str(e))


SKILL_CLASS = ProductAssistantSkill
