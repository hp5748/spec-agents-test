# AI Agent 调测入口

基于 LangChain + 硅基流动(DeepSeek) 的智能客服 Agent 系统，支持意图识别、技能路由和多轮对话。

## 功能特性

- ✅ **意图识别**：自动识别用户意图（订单查询/商品咨询/投诉处理/通用问答）
- ✅ **技能系统**：基于 Skills 的高级能力抽象，支持多步骤操作
- ✅ **多轮对话**：维护对话上下文，支持连续对话
- ✅ **流式响应**：SSE 长连接实时输出
- ✅ **RESTful API**：FastAPI 接口服务
- ✅ **黑科技界面**：炫酷的 Web 聊天界面

## 技术栈

| 组件 | 技术 |
|------|------|
| Agent框架 | LangChain 0.2.0 |
| LLM | DeepSeek-V3.2 (硅基流动) |
| Web框架 | FastAPI 0.109.0 |
| 流式传输 | Server-Sent Events |
| Python | 3.10+ |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入 API Key：

```bash
cp .env.example .env
```

编辑 `.env`：
```bash
SILICONFLOW_API_KEY=your_api_key_here
```

> 获取 API Key：访问 [硅基流动](https://siliconflow.cn/) 注册并创建

### 3. 启动服务

```bash
# Windows
start.bat

# Linux/Mac
./start.sh

# 或直接运行
cd src && python main.py
```

### 4. 访问服务

| 服务 | 地址 |
|------|------|
| 聊天界面 | http://localhost:8000/chat |
| API文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |

---

## Skills 技能系统

### 概述

Skills 是比 Tools 更高级的能力抽象层：
- 支持多步骤操作和专业知识
- 每个技能独立目录，包含元数据和执行器
- 通过 `skills/skills.yaml` 统一配置
- 支持热加载

### 目录结构

```
skills/
├── skills.yaml              # 技能配置文件
├── order-assistant/         # 订单助手技能（模板示例）
│   ├── SKILL.md             # 元数据和核心指令
│   ├── scripts/
│   │   └── executor.py      # 技能执行器
│   └── references/          # 参考资料（可选）
```

### 配置新技能

**1. 创建技能目录**

```bash
mkdir -p skills/your-skill/scripts
```

**2. 编写 SKILL.md**

```markdown
---
name: your-skill
description: 技能描述
version: 1.0.0
priority: 10
intents:
  - your_intent
required_tools:
  - your_tool
---

# 技能说明
...
```

**3. 实现执行器 scripts/executor.py**

```python
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from skills.base import BaseSkill, SkillConfig, SkillContext, SkillResult
from skills.registry import register_skill

@register_skill(config=SkillConfig(priority=10))
class YourSkill(BaseSkill):
    name = "your_skill"
    description = "技能描述"
    version = "1.0.0"
    required_tools = ["your_tool"]
    supported_intents = ["your_intent"]

    def execute(self, context: SkillContext) -> SkillResult:
        # 实现逻辑
        return SkillResult(
            success=True,
            response="响应内容",
            used_tools=["your_tool"]
        )

SKILL_CLASS = YourSkill
```

**4. 注册到 skills.yaml**

```yaml
skills:
  your-skill:
    name: your_skill
    description: 技能描述
    version: 1.0.0
    enabled: true
    priority: 10
    intents:
      - your_intent
    required_tools:
      - your_tool
    # 快捷操作配置 - 前端动态加载
    quick_actions:
      - label: "[YOUR] 操作名称"
        message: "预设的消息内容"
```

### 快捷操作配置

`quick_actions` 配置项用于定义前端界面中的快捷操作按钮，支持动态加载：

```yaml
quick_actions:
  - label: "[ORDER] 订单查询"    # 按钮显示文本
    message: "查询订单 12345678"  # 点击后发送的消息
  - label: "[ORDER] 待发货"
    message: "查询订单 87654321"
```

前端会在页面加载和新建会话时自动从 `/api/skills` 接口获取快捷操作并渲染按钮。

### 技能 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/skills` | GET | 列出所有技能 |
| `/api/skills/reload` | POST | 重载所有技能 |
| `/api/skills/{name}/reload` | POST | 重载单个技能 |

### 参考：order-assistant 技能

`order-assistant` 是技能模板示例，包含完整的目录结构和代码实现。开发新技能时请参考它。

**测试数据**：
| 订单号 | 状态 | 商品 |
|--------|------|------|
| 12345678 | 已发货 | iPhone 15 Pro |
| 87654321 | 待发货 | MacBook Air |
| 11111111 | 已送达 | AirPods Pro |

---

## API 接口

### POST /api/chat

普通对话接口

```json
// 请求
{"message": "查询订单12345678", "session_id": "test"}

// 响应
{
  "session_id": "test",
  "intent": "order_query",
  "intent_name": "订单查询",
  "response": "订单查询结果..."
}
```

### POST /api/chat/stream

流式对话接口（SSE）

```
data: {"type": "intent", "intent": "order_query", "intent_name": "订单查询"}

data: {"type": "content", "content": "正在查询..."}

data: {"type": "done"}
```

### 其他接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/history/{session_id}` | GET | 获取对话历史 |
| `/api/history/{session_id}` | DELETE | 清空对话历史 |
| `/api/session/new` | POST | 创建新会话 |
| `/health` | GET | 健康检查 |

---

## 意图类型

| 意图代码 | 名称 | 说明 |
|---------|------|------|
| order_query | 订单查询 | 查询订单状态、物流信息 |
| product_consult | 商品咨询 | 商品推荐、价格查询 |
| complaint | 投诉处理 | 创建工单、反馈问题 |
| general_qa | 通用问答 | 常见问题、服务说明 |

---

## 项目结构

```
.
├── src/                    # 源代码
│   ├── main.py            # FastAPI 入口
│   ├── agent.py           # Agent 核心逻辑
│   ├── config.py          # 配置管理
│   ├── tools.py           # 工具定义
│   ├── memory.py          # 对话记忆
│   ├── prompts.py         # Prompt 模板
│   └── skills/            # 技能模块
│
├── skills/                 # 技能配置目录
│   ├── skills.yaml        # 技能配置
│   └── order-assistant/   # 订单助手（模板）
│
├── static/                 # 静态资源
│   └── index.html         # 聊天界面
│
├── spec/                   # 规范文档
│   ├── Me2AI/             # 需求文档
│   └── AI2AI/             # 技术文档
│
├── requirements.txt        # 依赖列表
├── .env.example           # 环境变量模板
└── README.md              # 本文件
```

---

## 扩展开发

### 添加新意图

1. `config.py`: 添加 `IntentType` 枚举值
2. `prompts.py`: 添加对应的提示词模板
3. `agent.py`: 在意图映射中添加

### 添加新工具

1. `tools.py`: 继承 `BaseTool` 创建工具类
2. `tools.py`: 在 `get_tools()` 注册

### 添加新技能

参考 [Skills 技能系统](#skills-技能系统) 章节

---

## 常见问题

**Q: 启动报错 Connection error?**
A: 检查 API Key 是否正确，网络是否通畅。已配置 120 秒超时和重试机制。

**Q: 技能没有生效?**
A: 检查 `skills/skills.yaml` 中是否正确配置，`enabled: true`，意图映射是否正确。

**Q: 如何调试技能?**
A: 查看控制台日志，技能执行会输出详细的执行过程日志。

---

## License

MIT
