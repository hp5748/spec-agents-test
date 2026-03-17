# Skills 模块说明

## 概述

Skills 模块是一个比 Tools 更高级的能力抽象层，用于智能客服系统。

**Agent 驱动 Skill 执行闭环**

主要特性：
- **标准目录结构**：每个技能独立目录，包含 SKILL.md、scripts、references、assets
- **元数据扫描**：从 SKILL.md 的 YAML Front Matter 扫描元数据
- **配置简化**：config/skills.yaml 只配置 quick_actions
- **执行闭环**：感知 → 规划 → 执行 → 观察 → 反馈
- **重试验证**：支持重试策略、结果验证、降级处理

## 目录结构

```
skills/                           # 技能根目录
├── order-assistant/              # 订单助手技能
│   ├── SKILL.md                  # 元数据和核心指令（必需）
│   ├── scripts/
│   │   └── executor.py           # 技能执行器（必需）
│   ├── references/               # 参考资料（可选）
│   └── assets/                   # 模板资源（可选）
│
├── logistics-assistant/          # 物流查询技能
│   ├── SKILL.md
│   └── scripts/executor.py
│
├── product-assistant/            # 商品咨询技能
│   ├── SKILL.md
│   └── scripts/executor.py
│
└── complaint-assistant/          # 投诉处理技能
    ├── SKILL.md
    └── scripts/executor.py

config/
└── skills.yaml                   # 快捷操作配置
```

## 核心模块

| 模块 | 文件 | 职责 |
|------|------|------|
| 基类 | `base.py` | SkillConfig, SkillContext, SkillResult, BaseSkill |
| 注册中心 | `registry.py` | 技能注册、发现、匹配 |
| 资源加载 | `resource_loader.py` | SKILL.md 解析、references/assets 加载 |
| 验证器 | `validators.py` | 结果验证 |
| 重试管理 | `retry.py` | 重试策略和延迟计算 |
| 反馈生成 | `feedback.py` | 错误反馈生成 |

## 核心数据类

### 1. SkillConfig - 技能配置

```python
@dataclass
class SkillConfig:
    priority: int = 10
    enabled: bool = True
    max_retries: int = 3
    timeout: int = 30
    fallback_enabled: bool = True
    stream_enabled: bool = True

    # 重试策略
    retry_strategy: str = "exponential"  # exponential/linear/fixed
    retry_base_delay: float = 1.0

    # 验证配置
    validation_schema: Optional[str] = None

    # 降级配置
    fallback_strategy: str = "llm_assist"
    fallback_message: str = ""
```

### 2. SkillContext - 执行上下文

```python
@dataclass
class SkillContext:
    session_id: str
    user_input: str
    intent: str
    chat_history: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 运行时依赖
    tools: Dict[str, Any] = field(default_factory=dict)
    llm: Any = None

    # 技能资源
    references: List[ReferenceContent] = field(default_factory=list)
    assets: List[AssetContent] = field(default_factory=list)
    instruction: str = ""  # SKILL.md 指令内容
```

### 3. SkillResult - 执行结果

```python
@dataclass
class SkillResult:
    success: bool
    response: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    used_tools: List[str] = field(default_factory=list)

    # 验证信息
    validation_passed: bool = True
    validation_errors: List[str] = field(default_factory=list)
```

### 4. SkillMatch - 技能匹配结果

```python
@dataclass
class SkillMatch:
    skill_name: str
    confidence: float  # 0.0 - 1.0
    matched_intents: List[str]
    matched_keywords: List[str]
    priority: int
```

### 5. ExecutionTrace - 执行追踪

```python
@dataclass
class ExecutionTrace:
    trace_id: str
    skill_name: str
    status: ExecutionStatus  # pending/running/success/failed/retrying/fallback
    attempts: List[ExecutionAttempt]
    final_result: Optional[SkillResult]
    fallback_used: bool
    total_elapsed: float
```

## SKILL.md 配置规范

### YAML Front Matter 完整配置

```yaml
---
# ==========================================
# 基础元数据（必需）
# ==========================================
name: skill-name
description: 技能描述
version: 1.0.0
priority: 10
intents:
  - intent1
  - intent2
required_tools: []

# ==========================================
# 感知增强（可选）
# ==========================================
keywords:
  - 关键词1
  - 关键词2
examples:
  - "示例输入1"
  - "示例输入2"

# ==========================================
# 执行配置（可选）
# ==========================================
execution:
  timeout: 30
  stream_enabled: true
  load_references: true
  load_assets: true

# ==========================================
# 验证配置（可选）
# ==========================================
validation:
  result_schema: schema_name
  required_fields:
    - field1
    - field2

# ==========================================
# 重试配置（可选）
# ==========================================
retry:
  max_attempts: 3
  strategy: exponential
  base_delay: 1.0
  retryable_errors:
    - timeout
    - rate_limit

# ==========================================
# 降级配置（可选）
# ==========================================
fallback:
  strategy: llm_assist
  message: "服务暂时不可用"

# ==========================================
# 反馈配置（可选）
# ==========================================
feedback:
  error_templates:
    validation_failed: "验证失败提示"
    timeout: "超时提示"
    not_found: "未找到提示"
---

# 技能指令

技能的详细说明和使用方法...
```

## 使用方式

### 1. 从 SKILL.md 加载（推荐）

```python
from skills import skill_registry

# 自动扫描 skills/ 目录下的 SKILL.md
count = skill_registry.load_from_config('config/skills.yaml')
print(f"已注册 {count} 个技能")
```

### 2. 多 Skill 匹配

```python
# 带置信度的多 Skill 匹配
matches = skill_registry.find_matching_skills(
    intent="order_query",
    user_input="查询订单 12345678",
    top_k=3
)

for match in matches:
    print(f"{match.skill_name}: {match.confidence:.2f}")

# 选择最佳 Skill
best = skill_registry.select_best_skill(matches, strategy="confidence")
```

### 3. 执行闭环

```python
from skills import SkillContext

# 创建上下文
context = SkillContext(
    session_id="session-123",
    user_input="查询订单 12345678",
    intent="order_query"
)

# 获取技能
skill = skill_registry.get_skill_by_intent("order_query", llm=llm)

# 带重试的执行
result, trace = skill.execute_with_retry(
    context,
    on_retry=lambda attempt, delay, error: print(f"重试 {attempt}")
)

if trace.fallback_used:
    print("使用了降级处理")

print(result.response)
```

## 配置文件

### config/skills.yaml（简化版）

```yaml
# 全局配置
global:
  enabled: true
  hot_reload: true
  default_timeout: 30
  default_retries: 3

# 快捷操作配置（前端动态加载）
quick_actions:
  order-assistant:
    - label: "[ORDER] 订单查询"
      message: "查询订单 12345678"
  logistics-assistant:
    - label: "[LOG] 物流查询"
      message: "查询物流 SF1234567890"
```

## 执行闭环流程

```
1. 感知阶段
   ├── 扫描 skills/ 目录
   ├── 解析 SKILL.md 元数据
   └── 计算 Skill 置信度

2. 规划阶段
   ├── 选择最佳 Skill
   └── 准备降级方案

3. 执行阶段
   ├── 加载 references/assets
   ├── 执行技能逻辑
   └── 追踪执行状态

4. 观察阶段
   ├── 验证结果质量
   └── 决定重试/降级

5. 反馈阶段
   ├── 生成用户友好消息
   └── 记录执行日志
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/skills` | GET | 列出所有技能 |
| `/api/skills/reload` | POST | 重载所有技能 |
| `/api/skills/{name}/reload` | POST | 重载单个技能 |
| `/api/skills/{name}/enable` | POST | 启用技能 |
| `/api/skills/{name}/disable` | POST | 禁用技能 |

## 已实现的技能

| 技能名称 | 意图 | 优先级 | 说明 |
|---------|------|--------|------|
| order-assistant | order_query | 10 | 订单查询 |
| logistics-assistant | logistics_query | 10 | 物流跟踪 |
| product-assistant | product_consult | 10 | 商品咨询 |
| complaint-assistant | complaint | 10 | 投诉处理 |

## 与 Tools 的区别

| 特性 | Tools | Skills |
|------|-------|--------|
| 抽象层级 | 低 | 高 |
| 操作类型 | 单步 | 多步骤 |
| 工具组合 | 单一 | 多个 |
| 知识 | 无 | 包含专业知识 |
| 重试验证 | 无 | 支持重试和验证 |
| 降级处理 | 无 | 支持多种降级策略 |
| 执行追踪 | 无 | 完整执行追踪 |

## 扩展新技能

1. 在 `skills/` 目录创建新的技能目录
2. 创建 `SKILL.md`（包含 YAML Front Matter）
3. 创建 `scripts/executor.py`
4. 重启服务或调用 `/api/skills/reload`

*文档更新时间: 2026-03-16*
