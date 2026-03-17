"""
Prompt模板模块
定义各种场景的提示词模板
"""

# 系统角色设定
SYSTEM_PROMPT = """你是一个专业的电商智能客服助手。你的职责是：
1. 友好、专业地回答用户问题
2. 准确识别用户意图并提供相应服务
3. 在无法确定用户需求时，主动询问澄清
4. 保持对话礼貌、简洁、高效

请用中文回复用户。"""


def build_intent_classification_prompt(intents_config: dict, user_input: str) -> str:
    """
    动态生成意图识别 Prompt

    使用 examples 字段提供示例，引导 LLM 正确分类

    Args:
        intents_config: 意图配置字典 {code: {name, description, examples}}
        user_input: 用户输入

    Returns:
        生成的 Prompt 字符串
    """
    intent_sections = []

    for code, cfg in intents_config.items():
        # 构建每个意图的描述块
        section = f"【{cfg['name']}】({code})"
        section += f"\n  描述: {cfg['description']}"

        # 添加示例
        examples = cfg.get('examples', [])
        if examples:
            section += "\n  示例:"
            for ex in examples[:3]:  # 最多3个示例
                section += f"\n    - \"{ex}\""

        intent_sections.append(section)

    intent_list = "\n\n".join(intent_sections)

    return f"""请分析用户输入，判断用户的意图类型。

## 可选意图类型

{intent_list}

## 用户输入
{user_input}

## 要求
1. 仔细对比用户输入与各意图的描述和示例
2. 选择最匹配的意图类型
3. 只返回意图代码（如 order_query），不要返回其他内容

意图代码:"""


# 路由提示词模板（保留通用模板，用于 LLM 降级响应）
ROUTER_PROMPTS = {
    "default": """你是一个智能客服助手。请根据用户的问题提供专业、友好的回复。
当前对话历史：
{chat_history}

用户输入：{user_input}
请用中文回复用户。"""
}
