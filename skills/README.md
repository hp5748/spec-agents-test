# Skills 技能系统

项目根目录的技能定义，遵循标准目录结构规范。

## 目录结构

```
skills/
├── skills.yaml              # 技能配置文件
├── order-assistant/         # 订单助手技能
│   ├── SKILL.md             # 技能元数据和核心指令
│   ├── scripts/
│   │   └── executor.py      # 技能执行器
│   └── references/
│       └── order-fields.md  # 参考资料
├── product-expert/          # 产品专家技能
│   ├── SKILL.md
│   └── scripts/
│       └── executor.py
└── complaint-handler/       # 投诉处理技能
    ├── SKILL.md
    ├── scripts/
    │   └── executor.py
    └── assets/
        └── response-template.md
```

## 目录规范

每个技能目录结构：

```
skill-name/                  # 技能目录，使用 kebab-case 命名
├── SKILL.md                 # 必需：包含 YAML 元数据和核心指令
├── scripts/                 # 可选：可执行脚本
│   └── executor.py          # 技能执行器（必需）
├── references/              # 可选：参考资料
│   └── *.md                 # API 文档、字段说明等
└── assets/                  # 可选：模板和静态资源
    └── *.md                 # 响应模板、配置模板等
```

## SKILL.md 格式

```yaml
---
name: skill-name
description: 技能描述
version: 1.0.0
priority: 10
intents:
  - intent1
  - intent2
required_tools:
  - tool1
---

# 技能名称

技能功能说明...

## 功能说明
...

## 使用方式
...

## 执行流程
...

## 示例对话
...
```

## 如何新增技能

### 1. 创建目录结构

```bash
mkdir -p skills/new-skill/scripts
mkdir -p skills/new-skill/references  # 可选
mkdir -p skills/new-skill/assets      # 可选
```

### 2. 创建 SKILL.md

```yaml
---
name: new_skill
description: 新技能描述
version: 1.0.0
priority: 10
intents:
  - new_intent
required_tools: []
---

# New Skill

技能说明...
```

### 3. 创建执行器 scripts/executor.py

```python
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from skills.base import BaseSkill, SkillConfig, SkillContext, SkillResult
from skills.registry import register_skill


@register_skill(config=SkillConfig(priority=10))
class NewSkill(BaseSkill):
    name = "new_skill"
    description = "新技能描述"
    version = "1.0.0"
    tags = []
    required_tools = []
    supported_intents = ["new_intent"]

    def execute(self, context: SkillContext) -> SkillResult:
        # 实现技能逻辑
        return SkillResult(
            success=True,
            response="处理结果",
            used_tools=[]
        )


SKILL_CLASS = NewSkill
```

### 4. 更新 skills.yaml

```yaml
skills:
  new-skill:
    name: new_skill
    description: 新技能描述
    version: 1.0.0
    enabled: true
    priority: 10
    intents:
      - new_intent
    required_tools: []
```

### 5. 重载技能

```bash
curl -X POST http://localhost:8000/api/skills/reload
```

## 如何修改技能

1. 编辑对应目录下的文件
2. 如果启用热加载，自动生效
3. 或调用 `/api/skills/{name}/reload`

## 如何删除技能

1. 从 `skills.yaml` 删除配置
2. 删除对应的技能目录
3. 调用 `/api/skills/{name}` DELETE

## 已有技能

| 技能目录 | 名称 | 优先级 | 支持的意图 |
|---------|------|--------|-----------|
| order-assistant | order_assistant | 10 | order_query, logistics_query |
| product-expert | product_expert | 8 | product_inquiry, product_recommend, product_compare |
| complaint-handler | complaint_handler | 15 | complaint, refund_request, quality_issue |
