"""
对话记忆模块
管理多轮对话的上下文
"""
from typing import List, Dict, Optional
from collections import defaultdict
from config import Config


class Message:
    """消息类"""

    def __init__(self, role: str, content: str):
        self.role = role  # "user" 或 "assistant"
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class ConversationMemory:
    """对话记忆管理器"""

    def __init__(self, window_size: int = None):
        self.window_size = window_size or Config.MEMORY_WINDOW
        # 按会话ID存储对话历史
        self._conversations: Dict[str, List[Message]] = defaultdict(list)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """添加消息到对话历史"""
        message = Message(role, content)
        self._conversations[session_id].append(message)

        # 保持窗口大小，移除旧消息
        if len(self._conversations[session_id]) > self.window_size * 2:
            # 移除最早的一轮对话（用户消息+助手回复）
            self._conversations[session_id] = self._conversations[session_id][-self.window_size * 2:]

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """获取对话历史"""
        messages = self._conversations.get(session_id, [])
        return [msg.to_dict() for msg in messages]

    def get_history_text(self, session_id: str) -> str:
        """获取对话历史的文本格式"""
        messages = self._conversations.get(session_id, [])
        if not messages:
            return "（无历史对话）"

        history_lines = []
        for msg in messages:
            role_name = "用户" if msg.role == "user" else "助手"
            history_lines.append(f"{role_name}: {msg.content}")

        return "\n".join(history_lines)

    def clear_session(self, session_id: str) -> None:
        """清除指定会话的历史"""
        if session_id in self._conversations:
            del self._conversations[session_id]

    def get_last_intent(self, session_id: str) -> Optional[str]:
        """获取最近的意图（从元数据中）"""
        # 简化实现：可以从对话历史中推断
        return getattr(self._conversations[session_id][-1], 'intent', None) if self._conversations.get(session_id) else None

    def set_intent(self, session_id: str, intent: str) -> None:
        """设置当前意图"""
        # 存储在会话级别
        if session_id in self._conversations and self._conversations[session_id]:
            self._conversations[session_id][-1].intent = intent


class SimpleMemory:
    """简化的内存记忆（用于单次对话）"""

    def __init__(self):
        self.messages: List[Dict[str, str]] = []

    def add_user_message(self, content: str) -> None:
        """添加用户消息"""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        """添加助手消息"""
        self.messages.append({"role": "assistant", "content": content})

    def get_messages(self) -> List[Dict[str, str]]:
        """获取所有消息"""
        return self.messages

    def clear(self) -> None:
        """清空记忆"""
        self.messages = []


# 全局对话记忆实例
conversation_memory = ConversationMemory()
