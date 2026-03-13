"""
商品专家技能
专业的商品咨询和推荐服务
"""
from typing import Dict, Any

from skills.base import BaseSkill, SkillConfig, SkillContext, SkillResult
from skills.registry import register_skill
from skills.templates.skill_prompts import PRODUCT_EXPERT_PROMPT
from config import IntentType


@register_skill(config=SkillConfig(priority=10, stream_enabled=True))
class ProductExpertSkill(BaseSkill):
    """商品专家技能"""

    # 元信息
    name = "product_expert"
    description = "专业的商品咨询和推荐服务，帮助用户了解商品信息并做出购买决策"
    version = "1.0.0"
    tags = ["商品", "推荐", "咨询"]

    # 依赖配置
    required_tools = ["product_search"]
    supported_intents = [IntentType.PRODUCT_CONSULT]

    def get_prompt_template(self) -> str:
        """获取提示词模板"""
        return PRODUCT_EXPERT_PROMPT

    def execute(self, context: SkillContext) -> SkillResult:
        """
        执行商品咨询技能

        流程：
        1. 使用商品搜索工具搜索相关商品
        2. 结合搜索结果和 LLM 生成专业建议
        """
        used_tools = []

        # 1. 搜索商品
        tool = self.get_tool("product_search")
        search_result = ""

        if tool:
            try:
                search_result = tool._run(keyword=context.user_input)
                used_tools.append("product_search")
            except Exception as e:
                search_result = f"搜索商品时出错：{str(e)}"

        # 2. 构建增强提示词
        enhanced_prompt = f"""{PRODUCT_EXPERT_PROMPT.format(
            chat_history=context.chat_history,
            user_input=context.user_input
        )}

以下是商品搜索结果：
{search_result}

请基于以上搜索结果，为用户提供专业的商品咨询和建议。"""

        # 3. 使用 LLM 生成响应
        try:
            response = self._llm.invoke(enhanced_prompt)
            return SkillResult(
                success=True,
                response=response.content,
                data={"search_result": search_result},
                used_tools=used_tools
            )
        except Exception as e:
            # 如果 LLM 失败，直接返回搜索结果
            if search_result and "出错" not in search_result:
                return SkillResult(
                    success=True,
                    response=search_result,
                    data={"search_result": search_result},
                    used_tools=used_tools
                )
            return SkillResult(
                success=False,
                response=f"处理请求时出错：{str(e)}",
                error=str(e)
            )
