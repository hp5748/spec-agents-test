"""
智能客服Agent模块
主Agent：意图识别 + 路由 + 响应生成
使用硅基流动的 DeepSeek-V3.2 模型
集成 Skills 技能系统
"""
import json
from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI

from config import Config, IntentType, INTENT_NAMES
from prompts import ROUTER_PROMPTS
from tools import get_tools, TOOL_MAP
from memory import conversation_memory

# Skills 集成
from skills import skill_registry, SkillContext


class CustomerServiceAgent:
    """智能客服Agent"""

    # 类级别的技能初始化标记
    _skills_initialized = False

    def __init__(self, session_id: str = "default"):
        """初始化Agent"""
        Config.validate()  # 验证配置

        self.session_id = session_id

        # 使用硅基流动的 OpenAI 兼容接口
        self.llm = ChatOpenAI(
            model=Config.MODEL_NAME,
            api_key=Config.API_KEY,
            base_url=Config.BASE_URL,
            temperature=Config.TEMPERATURE,
            max_tokens=Config.MAX_TOKENS,
            request_timeout=120,  # 请求超时 120 秒
            max_retries=1,        # 最多重试 1 次
        )
        self.tools = get_tools()
        self.memory = conversation_memory

        # 初始化技能系统（只执行一次）
        self._init_skills()

    @classmethod
    def _init_skills(cls):
        """初始化技能系统"""
        if cls._skills_initialized:
            return

        if Config.SKILLS_ENABLED:
            try:
                # 自动发现并注册技能
                count = skill_registry.auto_discover()
                print(f"[OK] 成功注册 {count} 个技能")
                cls._skills_initialized = True
            except Exception as e:
                print(f"[WARN] 技能系统初始化失败: {e}，将使用降级模式")

    def classify_intent(self, user_input: str) -> str:
        """识别用户意图"""
        from prompts import INTENT_CLASSIFICATION_PROMPT
        prompt = INTENT_CLASSIFICATION_PROMPT.format(user_input=user_input)

        try:
            response = self.llm.invoke(prompt).content.strip().lower()

            # 验证返回的意图是否有效
            valid_intents = [
                IntentType.ORDER_QUERY,
                IntentType.PRODUCT_CONSULT,
                IntentType.COMPLAINT,
                IntentType.GENERAL_QA
            ]

            if response in valid_intents:
                return response

            # 如果LLM返回的不是有效意图，使用默认值
            return IntentType.GENERAL_QA

        except Exception as e:
            print(f"意图识别错误: {e}")
            return IntentType.GENERAL_QA

    def get_tool_by_intent(self, intent: str):
        """根据意图获取对应工具"""
        intent_tool_map = {
            IntentType.ORDER_QUERY: "order_query",
            IntentType.PRODUCT_CONSULT: "product_search",
            IntentType.COMPLAINT: "create_ticket",
        }
        tool_name = intent_tool_map.get(intent)
        return TOOL_MAP.get(tool_name) if tool_name else None

    def process_with_skill(self, user_input: str, intent: str) -> str:
        """
        使用技能处理请求

        Args:
            user_input: 用户输入
            intent: 识别的意图

        Returns:
            技能处理结果
        """
        if not Config.SKILLS_ENABLED:
            return None

        try:
            # 构建技能上下文
            context = SkillContext(
                session_id=self.session_id,
                user_input=user_input,
                intent=intent,
                chat_history=self.memory.get_history_text(self.session_id),
                tools=TOOL_MAP,
                llm=self.llm
            )

            # 根据意图获取技能
            skill = skill_registry.get_skill_by_intent(
                intent,
                tools=TOOL_MAP,
                llm=self.llm
            )

            if skill:
                print(f"[DEBUG] 使用技能: {skill.name}")
                result = skill.execute_with_logging(context)
                if result.success:
                    return result.response
                else:
                    print(f"[WARN] 技能执行失败: {result.error}")

        except Exception as e:
            print(f"[ERROR] 技能处理出错: {e}")

        return None

    def process_with_tool(self, user_input: str, intent: str) -> str:
        """使用工具处理请求"""
        tool = self.get_tool_by_intent(intent)

        if not tool:
            return self.generate_response(user_input, intent)

        # 获取对话历史
        chat_history = self.memory.get_history_text(self.session_id)

        # 根据意图选择提示词模板
        router_prompt = ROUTER_PROMPTS.get(intent, ROUTER_PROMPTS[IntentType.GENERAL_QA])
        prompt = router_prompt.format(
            chat_history=chat_history,
            user_input=user_input
        )

        try:
            # 简化的工具调用逻辑
            if intent == IntentType.ORDER_QUERY:
                # 尝试提取订单号
                import re
                order_match = re.search(r'\d{8}', user_input)
                if order_match:
                    return tool._run(order_match.group())
                else:
                    # 让LLM生成回复
                    response = self.llm.invoke(prompt)
                    return response.content

            elif intent == IntentType.PRODUCT_CONSULT:
                # 搜索商品
                return tool._run(keyword=user_input)

            elif intent == IntentType.COMPLAINT:
                # 创建工单
                return tool._run(issue_type="用户投诉", description=user_input)

            response = self.llm.invoke(prompt)
            return response.content

        except Exception as e:
            return f"处理请求时出现错误：{str(e)}，请稍后重试。"

    def generate_response(self, user_input: str, intent: str) -> str:
        """生成响应（不使用工具）"""
        chat_history = self.memory.get_history_text(self.session_id)
        router_prompt = ROUTER_PROMPTS.get(intent, ROUTER_PROMPTS[IntentType.GENERAL_QA])

        prompt = router_prompt.format(
            chat_history=chat_history,
            user_input=user_input
        )

        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            return f"抱歉，处理您的请求时出现错误：{str(e)}"

    def chat(self, user_input: str) -> Dict[str, str]:
        """
        主对话入口

        Args:
            user_input: 用户输入

        Returns:
            包含意图和响应的字典
        """
        # 1. 记录用户消息
        self.memory.add_message(self.session_id, "user", user_input)

        # 2. 识别意图
        intent = self.classify_intent(user_input)
        intent_name = INTENT_NAMES.get(intent, "通用问答")

        print(f"[DEBUG] 识别意图: {intent} ({intent_name})")

        # 3. 根据意图处理（优先使用 Skills）
        response = None

        # 3.1 尝试使用技能
        if Config.SKILLS_ENABLED:
            response = self.process_with_skill(user_input, intent)

        # 3.2 降级到工具
        if response is None and intent in [IntentType.ORDER_QUERY, IntentType.PRODUCT_CONSULT, IntentType.COMPLAINT]:
            response = self.process_with_tool(user_input, intent)

        # 3.3 最后使用通用响应
        if response is None:
            response = self.generate_response(user_input, intent)

        # 4. 记录助手回复
        self.memory.add_message(self.session_id, "assistant", response)

        return {
            "intent": intent,
            "intent_name": intent_name,
            "response": response
        }

    def chat_stream(self, user_input: str):
        """
        流式对话入口

        Args:
            user_input: 用户输入

        Yields:
            流式响应的文本块
        """
        # 1. 记录用户消息
        self.memory.add_message(self.session_id, "user", user_input)

        # 2. 识别意图
        intent = self.classify_intent(user_input)
        intent_name = INTENT_NAMES.get(intent, "通用问答")

        print(f"[DEBUG] 识别意图: {intent} ({intent_name})")

        # 先发送意图信息
        yield f"data: {json.dumps({'type': 'intent', 'intent': intent, 'intent_name': intent_name})}\n\n"

        # 3. 根据意图处理
        if intent in [IntentType.ORDER_QUERY, IntentType.PRODUCT_CONSULT, IntentType.COMPLAINT]:
            # 工具调用场景暂时用非流式
            response = self.process_with_tool(user_input, intent)
            yield f"data: {json.dumps({'type': 'content', 'content': response})}\n\n"
        else:
            # 流式生成响应
            chat_history = self.memory.get_history_text(self.session_id)
            router_prompt = ROUTER_PROMPTS.get(intent, ROUTER_PROMPTS[IntentType.GENERAL_QA])
            prompt = router_prompt.format(
                chat_history=chat_history,
                user_input=user_input
            )

            response = ""
            try:
                for chunk in self.llm.stream(prompt):
                    if chunk.content:
                        response += chunk.content
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk.content})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        # 4. 记录助手回复
        self.memory.add_message(self.session_id, "assistant", response)

        # 发送结束信号
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    def chat_stream_simple(self, user_input: str):
        """
        简化流式对话（用于工具调用场景）

        Yields:
            流式响应的文本块
        """
        import json
        # 1. 记录用户消息
        self.memory.add_message(self.session_id, "user", user_input)

        # 2. 识别意图
        intent = self.classify_intent(user_input)
        intent_name = INTENT_NAMES.get(intent, "通用问答")

        print(f"[DEBUG] 识别意图: {intent} ({intent_name})")

        # 先发送意图信息
        yield f"data: {json.dumps({'type': 'intent', 'intent': intent, 'intent_name': intent_name})}\n\n"

        # 3. 根据意图处理（优先使用 Skills）
        full_response = ""

        # 3.1 尝试使用技能
        if Config.SKILLS_ENABLED:
            skill_response = self.process_with_skill(user_input, intent)
            if skill_response:
                full_response = skill_response
                # 模拟流式输出
                for i in range(0, len(full_response), 10):
                    chunk = full_response[i:i+10]
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"

                # 记录助手回复
                self.memory.add_message(self.session_id, "assistant", full_response)
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

        # 3.2 降级到工具或流式生成
        if intent in [IntentType.ORDER_QUERY, IntentType.PRODUCT_CONSULT, IntentType.COMPLAINT]:
            # 工具调用场景
            full_response = self.process_with_tool(user_input, intent)
            # 模拟流式输出
            for i in range(0, len(full_response), 10):
                chunk = full_response[i:i+10]
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
        else:
            # 流式生成响应
            chat_history = self.memory.get_history_text(self.session_id)
            router_prompt = ROUTER_PROMPTS.get(intent, ROUTER_PROMPTS[IntentType.GENERAL_QA])
            prompt = router_prompt.format(
                chat_history=chat_history,
                user_input=user_input
            )

            try:
                for chunk in self.llm.stream(prompt):
                    if chunk.content:
                        full_response += chunk.content
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk.content})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        # 4. 记录助手回复
        self.memory.add_message(self.session_id, "assistant", full_response)

        # 发送结束信号
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    def get_history(self) -> List[Dict[str, str]]:
        """获取当前会话的对话历史"""
        return self.memory.get_history(self.session_id)

    def clear_history(self) -> None:
        """清空当前会话的对话历史"""
        self.memory.clear_session(self.session_id)


# 便捷函数
def create_agent(session_id: str = "default") -> CustomerServiceAgent:
    """创建Agent实例"""
    return CustomerServiceAgent(session_id=session_id)
