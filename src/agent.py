"""
智能客服Agent模块
主Agent：意图识别 + 路由 + 响应生成
使用硅基流动的 DeepSeek-V3.2 模型
集成 Skills 技能系统

架构：Agent → Skills → LLM（二级处理链）
增强：Agent 驱动 Skill 执行闭环
"""
import json
from typing import Dict, List, Optional, Tuple
from langchain_openai import ChatOpenAI

from config import Config, IntentManager
from prompts import build_intent_classification_prompt, ROUTER_PROMPTS
from memory import conversation_memory

# Skills 集成
from skills import (
    skill_registry, SkillContext, SkillResult,
    ExecutionTrace, SkillMatch, ExecutionStatus,
    feedback_generator, generate_feedback
)


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
                # 检查是否已有技能注册（可能已从配置文件加载）
                existing_skills = skill_registry.list_skills()
                if existing_skills:
                    print(f"[OK] 技能系统已初始化，共 {len(existing_skills)} 个技能")
                else:
                    # 没有技能时才自动发现
                    count = skill_registry.auto_discover()
                    print(f"[OK] 成功注册 {count} 个技能")
                cls._skills_initialized = True
            except Exception as e:
                print(f"[WARN] 技能系统初始化失败: {e}，将使用降级模式")

    def classify_intent(self, user_input: str) -> str:
        """
        识别用户意图

        使用动态生成的 Prompt 进行意图识别
        """
        # 获取意图配置
        intents_config = IntentManager.get_all_configs()

        # 动态生成 Prompt
        prompt = build_intent_classification_prompt(intents_config, user_input)

        try:
            response = self.llm.invoke(prompt).content.strip().lower()

            # 验证返回的意图是否有效
            valid_intents = IntentManager.get_intents()

            if response in valid_intents:
                return response

            # 如果LLM返回的不是有效意图，使用默认值
            return "general_qa"

        except Exception as e:
            print(f"意图识别错误: {e}")
            return "general_qa"

    # ============================================================
    # 新增：Agent 驱动 Skill 执行闭环
    # ============================================================

    def process_with_skill_enhanced(
        self,
        user_input: str,
        intent: str
    ) -> Tuple[Optional[str], ExecutionTrace]:
        """
        完整的技能执行闭环

        流程:
        1. 感知：多 Skill 匹配 + 置信度评估
        2. 规划：选择最佳 Skill + 准备降级方案
        3. 执行：资源加载 + 执行 + 状态追踪
        4. 观察：结果验证 + 决策
        5. 反馈：成功返回 / 重试 / 降级

        Args:
            user_input: 用户输入
            intent: 识别的意图

        Returns:
            (响应文本, 执行追踪)
        """
        trace = ExecutionTrace.create("unknown")

        if not Config.SKILLS_ENABLED:
            return None, trace

        try:
            # ===== 阶段 1: 感知 - 多 Skill 匹配 =====
            print(f"[DEBUG] 开始技能匹配: intent={intent}")

            matches = skill_registry.find_matching_skills(
                intent=intent,
                user_input=user_input,
                top_k=3
            )

            if not matches:
                print(f"[DEBUG] 未找到匹配的技能")
                return None, trace

            # ===== 阶段 2: 规划 - 选择最佳 Skill =====
            best_match = skill_registry.select_best_skill(matches, strategy="confidence")

            if not best_match:
                return None, trace

            print(f"[DEBUG] 选择技能: {best_match.skill_name} (置信度: {best_match.confidence:.2f})")

            # 获取技能实例
            skill = skill_registry.get_skill(
                best_match.skill_name,
                tools={},
                llm=self.llm
            )

            if not skill:
                return None, trace

            # 更新追踪信息
            trace.skill_name = skill.name
            trace.status = ExecutionStatus.RUNNING

            # ===== 阶段 3: 执行 - 加载资源并执行 =====

            # 获取技能元信息和资源
            skill_meta = skill_registry._skills.get(skill.name)

            # 构建增强的上下文
            context = SkillContext(
                session_id=self.session_id,
                user_input=user_input,
                intent=intent,
                chat_history=self.memory.get_history_text(self.session_id),
                tools={},
                llm=self.llm
            )

            # 加载技能资源（如果有）
            if skill_meta and skill_meta.skill_dir:
                metadata = skill_meta.metadata
                if metadata:
                    # 加载指令内容
                    skill_md_path = skill_meta.skill_dir / "SKILL.md"
                    from skills.resource_loader import SkillMetaParser
                    context.instruction = SkillMetaParser.get_instruction_content(skill_md_path)

                    # 加载 references 和 assets
                    if metadata.load_references or metadata.load_assets:
                        resources = skill_registry._load_skill_resources(
                            skill_meta.skill_dir,
                            load_references=metadata.load_references,
                            load_assets=metadata.load_assets
                        )
                        context.references = resources.get('references', [])
                        context.assets = resources.get('assets', [])

            # 带重试的执行
            result, trace = skill.execute_with_retry(
                context,
                on_retry=self._on_skill_retry
            )

            # ===== 阶段 4: 观察 - 结果验证 =====
            if not result.success or not result.validation_passed:
                print(f"[WARN] 技能执行失败: {result.error}")

                # ===== 阶段 5a: 降级处理 =====
                if skill.get_config().fallback_enabled:
                    trace.status = ExecutionStatus.FALLBACK
                    trace.fallback_used = True

                    fallback_result = skill.fallback(context, result.error or "验证失败")

                    if fallback_result.success:
                        trace.final_result = fallback_result
                        return fallback_result.response, trace

                # 生成错误反馈
                feedback = generate_feedback(
                    result.error or "执行失败",
                    context={
                        "intent": intent,
                        "skill_name": skill.name
                    },
                    trace=trace,
                    skill_name=skill.name
                )

                print(f"[DEBUG] 错误反馈: {feedback.message}")

                return None, trace

            # ===== 阶段 5b: 成功返回 =====
            trace.status = ExecutionStatus.SUCCESS
            trace.final_result = result

            return result.response, trace

        except Exception as e:
            print(f"[ERROR] 技能处理出错: {e}")
            trace.status = ExecutionStatus.FAILED

            feedback = generate_feedback(str(e), skill_name=trace.skill_name)
            print(f"[DEBUG] 错误反馈: {feedback.message}")

            return None, trace

    def _on_skill_retry(self, attempt: int, delay: float, error: str):
        """技能重试回调"""
        print(f"[DEBUG] 技能重试 {attempt}: 等待 {delay:.1f}s, 错误: {error}")

    # ============================================================
    # 原有方法（保持兼容）
    # ============================================================

    def process_with_skill(self, user_input: str, intent: str) -> Optional[str]:
        """
        使用技能处理请求（简化版，保持兼容）

        Args:
            user_input: 用户输入
            intent: 识别的意图

        Returns:
            技能处理结果，如果没有匹配的技能则返回 None
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
                tools={},  # 不再传递外部工具
                llm=self.llm
            )

            # 根据意图获取技能
            skill = skill_registry.get_skill_by_intent(
                intent,
                tools={},  # 不再传递外部工具
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

    def generate_response(self, user_input: str, intent: str) -> str:
        """
        生成响应（LLM 降级响应）

        当没有匹配的 Skill 时，使用 LLM 直接生成响应
        """
        chat_history = self.memory.get_history_text(self.session_id)

        # 使用通用模板
        prompt = ROUTER_PROMPTS["default"].format(
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

        处理链：Skills → LLM（二级）

        Args:
            user_input: 用户输入

        Returns:
            包含意图和响应的字典
        """
        # 1. 记录用户消息
        self.memory.add_message(self.session_id, "user", user_input)

        # 2. 识别意图
        intent = self.classify_intent(user_input)
        intent_name = IntentManager.get_intent_name(intent)

        print(f"[DEBUG] 识别意图: {intent} ({intent_name})")

        # 3. 根据意图处理（Skills → LLM 二级处理链）
        response = None

        # 3.1 尝试使用技能（增强版闭环执行）
        if Config.SKILLS_ENABLED:
            response, trace = self.process_with_skill_enhanced(user_input, intent)

            if trace.fallback_used:
                print(f"[DEBUG] 使用了降级处理")

        # 3.2 降级到 LLM 直接响应
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
        intent_name = IntentManager.get_intent_name(intent)

        print(f"[DEBUG] 识别意图: {intent} ({intent_name})")

        # 先发送意图信息
        yield f"data: {json.dumps({'type': 'intent', 'intent': intent, 'intent_name': intent_name})}\n\n"

        # 3. 尝试使用技能
        full_response = ""

        if Config.SKILLS_ENABLED:
            skill_response, trace = self.process_with_skill_enhanced(user_input, intent)
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

        # 4. 流式生成响应（LLM 降级）
        chat_history = self.memory.get_history_text(self.session_id)
        prompt = ROUTER_PROMPTS["default"].format(
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

        # 5. 记录助手回复
        self.memory.add_message(self.session_id, "assistant", full_response)

        # 发送结束信号
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    def chat_stream_simple(self, user_input: str):
        """
        简化流式对话

        Yields:
            流式响应的文本块
        """
        # 1. 记录用户消息
        self.memory.add_message(self.session_id, "user", user_input)

        # 2. 识别意图
        intent = self.classify_intent(user_input)
        intent_name = IntentManager.get_intent_name(intent)

        print(f"[DEBUG] 识别意图: {intent} ({intent_name})")

        # 先发送意图信息
        yield f"data: {json.dumps({'type': 'intent', 'intent': intent, 'intent_name': intent_name})}\n\n"

        # 3. 根据意图处理（Skills → LLM）
        full_response = ""

        # 3.1 尝试使用技能（增强版闭环执行）
        if Config.SKILLS_ENABLED:
            skill_response, trace = self.process_with_skill_enhanced(user_input, intent)
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

        # 3.2 流式生成响应（LLM 降级）
        chat_history = self.memory.get_history_text(self.session_id)
        prompt = ROUTER_PROMPTS["default"].format(
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
