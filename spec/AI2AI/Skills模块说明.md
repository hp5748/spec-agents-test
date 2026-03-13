# Skills 模块说明

## 概述

Skills 模块是一个比 Tools 更高级的能力抽象层，用于智能客服系统。

**遵循标准目录结构规范**

主要特性：
- **标准目录结构**：每个技能独立目录，包含 SKILL.md、scripts、references、assets
- **YAML 配置管理**：通过 `skills/skills.yaml` 管理所有技能
- **多步骤操作**：组合多个工具完成复杂任务
- **专业知识**：每个技能包含特定领域的知识
- **热加载**：运行时动态更新技能

## 目录结构

```
skills/                           # 技能根目录
├── skills.yaml                   # 技能配置文件
├── README.md                     # 使用说明
│
├── order-assistant/              # 订单助手技能
│   ├── SKILL.md                  # 元数据和核心指令（必需）
│   ├── scripts/
│   │   └── executor.py           # 技能执行器（必需）
│   └── references/
│       └── order-fields.md       # 参考资料（可选）
│
├── product-expert/               # 产品专家技能
│   ├── SKILL.md
│   └── scripts/
│       └── executor.py
│
└── complaint-handler/            # 投诉处理技能
    ├── SKILL.md
    ├── scripts/
    │   └── executor.py
    └── assets/
        └── response-template.md  # 响应模板（可选）
```

## 单个技能目录规范

```
skill-name/                       # 使用 kebab-case 命名
├── SKILL.md                      # 必需：YAML 元数据 + 核心指令
├── scripts/                      # 可选：可执行脚本
│   └── executor.py               # 技能执行器
├── references/                   # 可选：参考资料
│   └── *.md                      # API 文档、字段说明
└── assets/                       # 可选：模板和静态资源
    └── *.md                      # 响应模板、配置模板
```

## 核心类

### 1. BaseSkill - 技能基类

```python
from skills import BaseSkill, SkillConfig, SkillContext, SkillResult
from skills import register_skill

@register_skill(config=SkillConfig(priority=10))
class MySkill(BaseSkill):
    name = "my_skill"
    description = "技能描述"
    required_tools = ["tool1"]  # 依赖的工具
    supported_intents = ["intent1", "intent2"]

    def execute(self, context: SkillContext) -> SkillResult:
        # 获取工具
        tool = self.get_tool("tool1")

        # 处理逻辑
        result = tool.do_something(context.user_input)

        return SkillResult(
            success=True,
            response="处理结果",
            data={"key": "value"},
            used_tools=["tool1"]
        )
```

### 2. SkillContext - 执行上下文

```python
@dataclass
class SkillContext:
    session_id: str       # 会话ID
    user_input: str       # 用户输入
    intent: str           # 意图类型
    chat_history: str     # 对话历史
    metadata: dict        # 元数据
    tools: dict           # 可用工具
    llm: Any              # LLM 实例
```

### 3. SkillResult - 执行结果

```python
@dataclass
class SkillResult:
    success: bool         # 是否成功
    response: str         # 响应文本
    data: dict            # 返回数据
    error: str            # 错误信息
    used_tools: list      # 使用的工具列表
```

## 使用方式

### 1. 从配置文件加载（推荐）

```python
from skills import skill_registry

# 从 skills/skills.yaml 加载
count = skill_registry.load_from_config('skills/skills.yaml')
print(f"已注册 {count} 个技能")
```

### 2. 查看已注册技能

```python
skills = skill_registry.list_skills()
for skill in skills:
    print(f"- {skill['name']}: {skill['description']}")
```

### 3. 使用技能

```python
from skills import skill_registry, SkillContext

# 按意图获取技能
skill = skill_registry.get_skill_by_intent(
    "order_query",
    tools={"order_query": order_tool},
    llm=llm
)

# 创建上下文
context = SkillContext(
    session_id="session-123",
    user_input="查询订单 ORD1234567890",
    intent="order_query"
)

# 执行技能
result = skill.execute(context)
print(result.response)
```

## 配置文件管理

### skills/skills.yaml 结构

```yaml
# 全局配置
global:
  enabled: true
  hot_reload: true
  default_timeout: 30

# 技能定义
skills:
  order_assistant:
    name: order_assistant
    description: 专业的订单查询和跟踪服务
    version: 1.0.0
    enabled: true
    priority: 10
    file: order_assistant.py      # Python 文件
    class: OrderAssistantSkill    # 类名
    intents:
      - order_query
      - logistics_query
    required_tools:
      - order_query
    config:
      max_retries: 3
      timeout: 30
```

### 新增技能步骤

1. 在 `skills/` 下创建技能目录（如 `new-skill/`）
2. 创建 `SKILL.md`（元数据 + 核心指令）
3. 创建 `scripts/executor.py`（执行器）
4. 在 `skills.yaml` 中添加配置
5. 重启服务或调用 `/api/skills/reload`

### 修改技能

1. 编辑对应技能目录下的文件
2. 如启用热加载，自动生效
3. 或调用 `/api/skills/{name}/reload`

### 删除技能

1. 从 `skills.yaml` 删除配置
2. 删除对应的技能目录
3. 调用 `/api/skills/{name}` DELETE

## 集成到 Agent

```python
class Agent:
    _skills_initialized = False

    def __init__(self):
        self._init_skills()

    @classmethod
    def _init_skills(cls):
        if cls._skills_initialized:
            return
        skill_registry.auto_discover()
        cls._skills_initialized = True

    def process_with_skill(self, user_input: str, intent: str) -> str:
        context = SkillContext(
            session_id=self.session_id,
            user_input=user_input,
            intent=intent
        )

        skill = skill_registry.get_skill_by_intent(
            intent,
            tools=self.tools,
            llm=self.llm
        )

        if skill:
            result = skill.execute(context)
            return result.response if result.success else None
        return None

    def chat(self, user_input: str) -> str:
        intent = self.detect_intent(user_input)

        # 优先使用 Skills
        response = self.process_with_skill(user_input, intent)
        if response:
            return response

        # 降级到 Tools 或 LLM
        return self.fallback_process(user_input)
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/skills` | GET | 列出所有技能 |
| `/api/skills/{name}` | GET | 获取技能详情 |
| `/api/skills/reload` | POST | 重载所有技能 |
| `/api/skills/{name}/reload` | POST | 重载单个技能 |
| `/api/skills/{name}/enable` | POST | 启用技能 |
| `/api/skills/{name}/disable` | POST | 禁用技能 |
| `/api/skills/{name}` | DELETE | 删除技能 |

## 热加载

```python
from skills import init_hot_reloader, get_hot_reloader

# 初始化并启动（监控 skills/ 目录）
reloader = init_hot_reloader(skill_registry, "skills")
reloader.start_watch()

# 手动重载
reloader.reload_skill("order_assistant")
```

## 配置

### src/config.py

```python
class Config:
    SKILLS_ENABLED: bool = True
    SKILLS_HOT_RELOAD: bool = True
```

### skills/skills.yaml（主要配置）

```yaml
global:
  enabled: true
  hot_reload: true
  default_timeout: 30
```

## 已实现的技能

| 技能名称 | 意图 | 优先级 | 说明 |
|---------|------|--------|------|
| order_assistant | order_query, logistics_query | 10 | 订单查询和跟踪 |
| product_expert | product_inquiry, product_recommend | 8 | 产品咨询和推荐 |
| complaint_handler | complaint, refund_request | 15 | 投诉处理 |

## 扩展新技能

### 步骤

1. 在 `skills/` 目录创建新的 Python 文件
2. 在 `skills.yaml` 中添加配置
3. 重启服务或调用重载 API

### 示例：创建新技能

**skills/weather_assistant.py:**
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from skills.base import BaseSkill, SkillConfig, SkillContext, SkillResult
from skills.registry import register_skill

@register_skill(config=SkillConfig(priority=5))
class WeatherAssistantSkill(BaseSkill):
    name = "weather_assistant"
    description = "天气查询助手"
    version = "1.0.0"
    tags = ["天气", "查询"]

    required_tools = []  # 可选
    supported_intents = ["weather_query"]

    def execute(self, context: SkillContext) -> SkillResult:
        user_input = context.user_input

        # 处理逻辑
        return SkillResult(
            success=True,
            response=f"您查询的天气信息：...",
            used_tools=[]
        )
```

**skills/skills.yaml 添加配置:**
```yaml
skills:
  weather_assistant:
    name: weather_assistant
    description: 天气查询助手
    version: 1.0.0
    enabled: true
    priority: 5
    file: weather_assistant.py
    class: WeatherAssistantSkill
    intents:
      - weather_query
    required_tools: []
```

## 与 Tools 的区别

| 特性 | Tools | Skills |
|------|-------|--------|
| 抽象层级 | 低 | 高 |
| 操作类型 | 单步 | 多步骤 |
| 工具组合 | 单一 | 多个 |
| 知识 | 无 | 包含专业知识 |
| 状态 | 无状态 | 可维护上下文 |
| 输出 | 单一结果 | 支持流式 |

## 更多信息

详细使用说明请参考 `skills/README.md`
