---
# ==========================================
# 技能元数据 (YAML Front Matter)
# ==========================================
name: order-assistant
description: 订单查询和跟踪服务
version: 1.0.0
priority: 10
intents:
  - order_query
  - logistics_query
required_tools:
  - order_query
---

# Order Assistant 技能

> **模板说明**: 本技能作为开发新技能的模板参考

订单查询和跟踪服务，帮助用户查询订单状态、物流信息。

---

## 目录结构

```
order-assistant/
├── SKILL.md              # 本文件 - 元数据和核心指令
├── scripts/
│   └── executor.py       # 技能执行器 (必需)
├── references/           # 参考资料 (可选)
└── assets/               # 模板资源 (可选)
```

---

## 功能说明

- 根据订单号查询订单状态
- 查询物流跟踪信息
- 处理订单相关问题咨询

---

## 触发条件

当用户意图为 `order_query` 或 `logistics_query` 时自动触发。

### 订单号格式

- `ORD` + 10位数字：如 ORD1234567890
- 8位纯数字：如 12345678

---

## 执行流程

1. 从用户输入中提取订单号
2. 调用 `order_query` 工具查询
3. 格式化并返回结果

---

## 测试数据

| 订单号 | 状态 | 说明 |
|--------|------|------|
| 12345678 | 已发货 | iPhone 15 Pro |
| 87654321 | 待发货 | MacBook Air |
| 11111111 | 已送达 | AirPods Pro |

---

## 开发新技能指南

### 1. 创建目录结构

```bash
mkdir -p skills/your-skill/scripts
touch skills/your-skill/SKILL.md
touch skills/your-skill/scripts/executor.py
```

### 2. 编写 SKILL.md

复制本文件，修改元数据和指令。

### 3. 实现 executor.py

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
    required_tools = []  # 依赖的工具
    supported_intents = ["your_intent"]

    def execute(self, context: SkillContext) -> SkillResult:
        # 实现逻辑
        return SkillResult(
            success=True,
            response="响应内容",
            used_tools=[]
        )

SKILL_CLASS = YourSkill
```

### 4. 注册到 skills.yaml

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
    required_tools: []
```

---

## 示例对话

**用户**: 查询订单 12345678
**技能**:
```
订单查询结果：
订单号：12345678
状态：已发货
物流单号：SF1234567890
预计送达：明天
商品：iPhone 15 Pro, 手机壳
金额：¥8999
```

**用户**: 我的订单到哪了？
**技能**: 请提供您的订单号，格式如：ORD1234567890 或 8位纯数字
