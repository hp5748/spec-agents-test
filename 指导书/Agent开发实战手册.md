# Agent开发实战手册

## 1. 开发流程总览

```
┌─────────────────────────────────────────────────────────┐
│                Agent开发标准流程                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1️⃣ 需求分析                                            │
│     └─ 明确场景、用户、目标                              │
│                                                         │
│  2️⃣ 架构设计                                            │
│     └─ Agent角色、工具、工作流                          │
│                                                         │
│  3️⃣ 原型开发                                            │
│     └─ 快速验证核心功能                                  │
│                                                         │
│  4️⃣ 迭代优化                                            │
│     └─ 调优Prompt、工具、工作流                          │
│                                                         │
│  5️⃣ 测试评估                                            │
│     └─ 功能测试、性能测试、安全测试                      │
│                                                         │
│  6️⃣ 部署上线                                            │
│     └─ 容器化、监控、告警                                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 需求分析模板

### 2.1 Agent需求分析文档

```markdown
# Agent需求分析文档

## 1. 项目概述
- **项目名称**: [Agent名称]
- **版本**: v1.0
- **负责人**: [姓名]
- **创建日期**: [日期]

## 2. 业务背景
### 2.1 当前痛点
- 痛点1: [描述]
- 痛点2: [描述]

### 2.2 期望效果
- 效果1: [可量化的指标]
- 效果2: [可量化的指标]

## 3. 用户分析
### 3.1 目标用户
- 用户画像: [描述]
- 技术水平: [高/中/低]

### 3.2 使用场景
| 场景 | 触发条件 | 期望输出 |
|------|---------|---------|
| 场景1 | ... | ... |
| 场景2 | ... | ... |

## 4. 功能需求
### 4.1 核心功能
1. [功能1]: [描述]
2. [功能2]: [描述]

### 4.2 工具需求
- [ ] 需要搜索能力
- [ ] 需要数据库访问
- [ ] 需要文件操作
- [ ] 需要API调用

### 4.3 记忆需求
- [ ] 短期对话记忆
- [ ] 长期知识存储
- [ ] 用户偏好记忆

## 5. 非功能需求
### 5.1 性能要求
- 响应时间: < [X]秒
- 并发用户: [X]人

### 5.2 安全要求
- 数据敏感度: [高/中/低]
- 合规要求: [列表]

## 6. 成功指标
- 准确率: > [X]%
- 用户满意度: > [X]%
- 自动化率: > [X]%
```

### 2.2 实战案例：智能客服Agent需求

```markdown
# 智能客服Agent需求分析

## 1. 项目概述
- **项目名称**: 电商智能客服Agent
- **目标**: 自动处理80%的常见客服咨询

## 2. 业务背景
### 2.1 当前痛点
- 客服人力成本高，响应慢
- 重复性问题占比高（60%）
- 夜间无人值守

### 2.2 期望效果
- 自动化率 > 80%
- 响应时间 < 3秒
- 24小时服务

## 3. 用户分析
### 3.1 目标用户
- 电商平台消费者
- 技术水平: 中等

### 3.2 使用场景
| 场景 | 触发条件 | 期望输出 |
|------|---------|---------|
| 订单查询 | "我的订单到哪了" | 物流状态 |
| 退换货 | "想退货" | 退货流程引导 |
| 商品咨询 | "这个好用吗" | 商品推荐 |
| 投诉处理 | "要投诉" | 转人工 |

## 4. 功能需求
### 4.1 核心功能
1. 意图识别: 理解用户想做什么
2. 订单查询: 查询订单状态和物流
3. 商品推荐: 基于需求推荐商品
4. 问题解答: 回答常见问题

### 4.2 工具需求
- [x] 订单系统API
- [x] 物流系统API
- [x] 商品数据库
- [x] 知识库检索

## 5. 成功指标
- 意图识别准确率 > 95%
- 问题解决率 > 80%
- 用户满意度 > 4.0/5.0
```

---

## 3. Agent设计模式

### 3.1 单Agent模式

```python
"""
适用场景: 任务简单、流程固定
"""
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import Tool
from langchain.prompts import ChatPromptTemplate

class SingleAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        self.tools = self._setup_tools()
        self.agent = self._create_agent()
    
    def _setup_tools(self):
        return [
            Tool(
                name="search",
                func=self._search,
                description="搜索信息"
            ),
            Tool(
                name="calculate",
                func=self._calculate,
                description="执行计算"
            )
        ]
    
    def _create_agent(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个有用的助手"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        agent = create_openai_functions_agent(self.llm, self.tools, prompt)
        return AgentExecutor(agent=agent, tools=self.tools, verbose=True)
    
    def run(self, query):
        return self.agent.invoke({"input": query})

# 使用
agent = SingleAgent()
result = agent.run("帮我搜索今天的天气")
```

### 3.2 路由Agent模式

```python
"""
适用场景: 多种任务类型，需要分类处理
"""
from typing import Literal
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel

class IntentClassification(BaseModel):
    intent: Literal["order_query", "product_search", "complaint", "general"]
    confidence: float

class RouterAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        self.specialized_agents = {
            "order_query": OrderQueryAgent(),
            "product_search": ProductSearchAgent(),
            "complaint": ComplaintAgent(),
            "general": GeneralAgent()
        }
        self.parser = PydanticOutputParser(pydantic_object=IntentClassification)
    
    def classify_intent(self, query):
        prompt = f"""
        分析用户意图，返回JSON格式:
        {self.parser.get_format_instructions()}
        
        用户输入: {query}
        """
        
        response = self.llm.invoke(prompt)
        return self.parser.parse(response.content)
    
    def route(self, query):
        # 1. 分类意图
        classification = self.classify_intent(query)
        
        # 2. 路由到专业Agent
        if classification.confidence > 0.8:
            agent = self.specialized_agents[classification.intent]
            return agent.process(query)
        else:
            # 置信度低，转人工
            return {"action": "escalate", "reason": "意图不明确"}

# 使用
router = RouterAgent()
result = router.route("我的订单12345到哪了？")
```

### 3.3 协作Agent模式

```python
"""
适用场景: 复杂任务，需要多步骤协作
"""
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

class WorkflowState(TypedDict):
    query: str
    research_result: str
    analysis_result: str
    final_report: str

class CollaborativeAgentSystem:
    def __init__(self):
        self.researcher = ResearchAgent()
        self.analyst = AnalystAgent()
        self.writer = WriterAgent()
        self.reviewer = ReviewerAgent()
        
        self.workflow = self._build_workflow()
    
    def _build_workflow(self):
        workflow = StateGraph(WorkflowState)
        
        # 添加节点
        workflow.add_node("research", self._research_node)
        workflow.add_node("analyze", self._analyze_node)
        workflow.add_node("write", self._write_node)
        workflow.add_node("review", self._review_node)
        
        # 定义流程
        workflow.set_entry_point("research")
        workflow.add_edge("research", "analyze")
        workflow.add_edge("analyze", "write")
        workflow.add_edge("write", "review")
        workflow.add_conditional_edges(
            "review",
            self._should_revise,
            {
                "revise": "write",
                "finish": END
            }
        )
        
        return workflow.compile()
    
    def _research_node(self, state: WorkflowState):
        result = self.researcher.run(state["query"])
        state["research_result"] = result
        return state
    
    def _analyze_node(self, state: WorkflowState):
        result = self.analyst.run(state["research_result"])
        state["analysis_result"] = result
        return state
    
    def _write_node(self, state: WorkflowState):
        result = self.writer.run(
            research=state["research_result"],
            analysis=state["analysis_result"]
        )
        state["final_report"] = result
        return state
    
    def _review_node(self, state: WorkflowState):
        result = self.reviewer.run(state["final_report"])
        state["review_feedback"] = result
        return state
    
    def _should_revise(self, state: WorkflowState):
        if state.get("review_feedback", {}).get("approved"):
            return "finish"
        return "revise"
    
    def run(self, query):
        return self.workflow.invoke({"query": query})
```

### 3.4 层级Agent模式

```python
"""
适用场景: 任务可分解，有明确层级
"""
class HierarchicalAgentSystem:
    def __init__(self):
        # 主控Agent
        self.master = MasterAgent()
        
        # 子Agent
        self.sub_agents = {
            "data_collection": DataCollectionAgent(),
            "data_analysis": DataAnalysisAgent(),
            "report_generation": ReportGenerationAgent()
        }
    
    def process(self, task):
        # 1. 主控Agent分解任务
        subtasks = self.master.decompose(task)
        
        # 2. 分配给子Agent
        results = {}
        for subtask in subtasks:
            agent = self.sub_agents[subtask["type"]]
            results[subtask["id"]] = agent.run(subtask)
        
        # 3. 主控Agent汇总
        final_result = self.master.aggregate(results)
        
        return final_result

class MasterAgent:
    def decompose(self, task):
        """将大任务分解为子任务"""
        prompt = f"""
        将以下任务分解为子任务:
        {task}
        
        输出JSON格式的子任务列表。
        """
        
        response = llm.invoke(prompt)
        return parse_subtasks(response)
    
    def aggregate(self, results):
        """汇总子任务结果"""
        prompt = f"""
        整合以下子任务结果:
        {results}
        
        生成最终报告。
        """
        
        return llm.invoke(prompt)
```

---

## 4. 工具开发指南

### 4.1 工具开发模板

```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Type

# 1. 定义输入Schema
class WeatherInput(BaseModel):
    city: str = Field(description="城市名称")
    date: Optional[str] = Field(default=None, description="日期，格式YYYY-MM-DD")

# 2. 实现工具类
class WeatherTool(BaseTool):
    name = "weather_query"
    description = "查询指定城市的天气信息"
    args_schema: Type[BaseModel] = WeatherInput
    
    def _run(self, city: str, date: Optional[str] = None) -> str:
        """执行天气查询"""
        try:
            # 调用天气API
            weather_data = self._call_weather_api(city, date)
            return self._format_result(weather_data)
        except Exception as e:
            return f"查询失败: {str(e)}"
    
    def _call_weather_api(self, city, date):
        """实际API调用"""
        import requests
        url = f"https://api.weather.com/v1/{city}"
        response = requests.get(url)
        return response.json()
    
    def _format_result(self, data):
        """格式化结果"""
        return f"""
        天气信息:
        - 温度: {data['temp']}°C
        - 天气: {data['weather']}
        - 湿度: {data['humidity']}%
        """

# 3. 注册工具
from langchain.agents import Tool

weather_tool = Tool(
    name="weather_query",
    func=WeatherTool(),
    description="查询天气，输入城市名称"
)
```

### 4.2 常用工具实现

```python
# === 数据库查询工具 ===
class DatabaseQueryTool(BaseTool):
    name = "database_query"
    description = "查询数据库"
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def _run(self, query: str) -> str:
        # 安全检查
        if not self._is_safe_query(query):
            return "不安全的查询被拒绝"
        
        try:
            result = self.db.execute(query)
            return str(result.fetchall())
        except Exception as e:
            return f"查询失败: {str(e)}"
    
    def _is_safe_query(self, query):
        """SQL注入检查"""
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "UPDATE"]
        return not any(kw in query.upper() for kw in dangerous_keywords)

# === 文件操作工具 ===
class FileOperationTool(BaseTool):
    name = "file_operation"
    description = "读写文件"
    
    def _run(self, operation: str, path: str, content: str = None) -> str:
        if operation == "read":
            return self._read_file(path)
        elif operation == "write":
            return self._write_file(path, content)
        else:
            return "不支持的操作"
    
    def _read_file(self, path):
        # 安全检查
        if not self._is_safe_path(path):
            return "访问被拒绝"
        
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _is_safe_path(self, path):
        """路径安全检查"""
        import os
        allowed_dir = "/safe/directory"
        real_path = os.path.realpath(path)
        return real_path.startswith(allowed_dir)

# === API调用工具 ===
class APICallTool(BaseTool):
    name = "api_call"
    description = "调用外部API"
    
    def __init__(self, allowed_apis):
        self.allowed_apis = allowed_apis
    
    def _run(self, endpoint: str, method: str = "GET", params: dict = None) -> str:
        # 检查API白名单
        if endpoint not in self.allowed_apis:
            return "API不在白名单中"
        
        import requests
        
        try:
            if method == "GET":
                response = requests.get(endpoint, params=params)
            else:
                response = requests.post(endpoint, json=params)
            
            return response.json()
        except Exception as e:
            return f"API调用失败: {str(e)}"

# === 代码执行工具（沙箱）===
class CodeExecutionTool(BaseTool):
    name = "code_execute"
    description = "在沙箱中执行Python代码"
    
    def _run(self, code: str) -> str:
        # 安全检查
        if self._has_dangerous_code(code):
            return "代码包含危险操作"
        
        # 在沙箱中执行
        return self._execute_in_sandbox(code)
    
    def _has_dangerous_code(self, code):
        dangerous = ["import os", "import sys", "subprocess", "eval(", "exec("]
        return any(d in code for d in dangerous)
    
    def _execute_in_sandbox(self, code):
        # 使用RestrictedPython或Docker容器
        import subprocess
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout or result.stderr
```

### 4.3 工具安全最佳实践

```python
class SecureToolMixin:
    """工具安全混入类"""
    
    def validate_input(self, input_data):
        """输入验证"""
        # 1. 类型检查
        if not isinstance(input_data, self.expected_type):
            raise ValueError(f"期望类型: {self.expected_type}")
        
        # 2. 长度限制
        if len(str(input_data)) > self.max_length:
            raise ValueError("输入过长")
        
        # 3. 内容检查
        if self.contains_malicious(input_data):
            raise ValueError("检测到恶意内容")
        
        return input_data
    
    def rate_limit(self, user_id):
        """限流检查"""
        # 使用Redis实现
        key = f"rate_limit:{self.name}:{user_id}"
        count = redis.get(key)
        
        if count and int(count) > self.max_calls:
            raise Exception("请求过于频繁")
        
        redis.incr(key)
        redis.expire(key, 60)  # 1分钟窗口
    
    def log_operation(self, user_id, input_data, output):
        """操作日志"""
        log_entry = {
            "tool": self.name,
            "user_id": user_id,
            "input": input_data,
            "output": output,
            "timestamp": datetime.now()
        }
        logger.info(log_entry)

# 使用示例
class SecureWeatherTool(WeatherTool, SecureToolMixin):
    expected_type = str
    max_length = 100
    max_calls = 10
    
    def _run(self, city: str) -> str:
        # 安全检查
        city = self.validate_input(city)
        self.rate_limit(self.user_id)
        
        # 执行
        result = super()._run(city)
        
        # 日志
        self.log_operation(self.user_id, city, result)
        
        return result
```

---

## 5. Prompt工程实战

### 5.1 Agent系统提示词模板

```python
# === 基础模板 ===
BASE_SYSTEM_PROMPT = """
你是一个{role}。

## 你的能力
{capabilities}

## 你的工具
{tools_description}

## 工作流程
1. 理解用户请求
2. 分析需要使用哪些工具
3. 执行工具调用
4. 整合结果并回复

## 注意事项
- 始终使用工具获取最新信息
- 不确定时主动询问用户
- 保持回答简洁准确
"""

# === ReAct模板 ===
REACT_PROMPT = """
你是一个能够思考和行动的智能助手。

对于每个任务，你需要:
1. Thought: 思考下一步该做什么
2. Action: 选择要使用的工具
3. Action Input: 提供工具参数
4. Observation: 观察工具返回结果
5. 重复以上步骤直到完成任务

可用工具:
{tool_names}

工具使用格式:
```
Thought: [你的思考]
Action: [工具名称]
Action Input: [工具参数JSON]
```

开始!

问题: {input}
{agent_scratchpad}
"""

# === 带约束的模板 ===
CONSTRAINED_PROMPT = """
你是一个{role}。

## 角色定位
{role_description}

## 行为约束
1. 只回答{domain}相关问题
2. 对于超出范围的问题，礼貌拒绝
3. 不确定时，明确说明并提供替代方案

## 安全规则
1. 不透露敏感信息
2. 不执行危险操作
3. 不生成有害内容

## 输出格式
{output_format}

用户输入: {input}
你的回复:
"""
```

### 5.2 Prompt优化技巧

```python
# 技巧1: Few-shot示例
FEW_SHOT_PROMPT = """
以下是一些示例对话:

用户: 12345订单到哪了？
助手: [调用订单查询工具] 您的订单12345目前在上海转运中心，预计明天送达。

用户: 这个手机好用吗？
助手: [调用商品推荐工具] 这款手机用户评价4.5分，主要优点是拍照清晰、续航长。

现在请处理:
用户: {query}
助手:
"""

# 技巧2: 思维链
CHAIN_OF_THOUGHT_PROMPT = """
分析以下问题时，请一步步思考:

问题: {query}

让我们一步步分析:
1. 首先，我需要理解问题的核心是...
2. 然后，我需要获取的信息有...
3. 接下来，我应该使用的工具是...
4. 最后，我需要整合的信息是...

现在开始分析:
"""

# 技巧3: 自我反思
SELF_REFLECTION_PROMPT = """
你刚刚给出的回答是:
{previous_answer}

请自我评估:
1. 回答是否准确？(是/否，说明原因)
2. 是否完整回答了问题？(是/否)
3. 是否可以改进？如何改进？

如果需要改进，请给出更好的回答。
"""

# 技巧4: 角色扮演
ROLE_PLAY_PROMPT = """
你现在是{role_name}，具有以下特征:

性格: {personality}
说话风格: {speaking_style}
专业领域: {expertise}

当用户问你问题时，以这个角色的身份回答。

用户: {query}
{role_name}:
"""
```

### 5.3 Prompt版本管理

```python
# prompts/registry.py
from typing import Dict
import yaml

class PromptRegistry:
    """Prompt版本管理"""
    
    def __init__(self, config_path="prompts/config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.prompts: Dict[str, Dict] = {}
        self._load_prompts()
    
    def _load_prompts(self):
        """加载所有Prompt"""
        for name, info in self.config.items():
            version = info["current_version"]
            path = f"prompts/{name}/{version}.txt"
            
            with open(path) as f:
                self.prompts[name] = {
                    "content": f.read(),
                    "version": version,
                    "metadata": info.get("metadata", {})
                }
    
    def get(self, name: str, variables: dict = None) -> str:
        """获取Prompt并填充变量"""
        prompt = self.prompts[name]["content"]
        
        if variables:
            prompt = prompt.format(**variables)
        
        return prompt
    
    def list_versions(self, name: str) -> list:
        """列出所有版本"""
        return self.prompts[name].get("metadata", {}).get("versions", [])

# config.yaml示例
"""
customer_service:
  current_version: "v2"
  metadata:
    versions: ["v1", "v2"]
    author: "team"
    updated_at: "2026-03-01"
"""

# 使用
registry = PromptRegistry()
prompt = registry.get("customer_service", {"user_name": "张三"})
```

---

## 6. 记忆系统设计

### 6.1 记忆架构

```python
from typing import List, Dict
from datetime import datetime
import json

class AgentMemory:
    """Agent记忆系统"""
    
    def __init__(self):
        # 短期记忆: 最近N轮对话
        self.short_term: List[Dict] = []
        self.max_short_term = 10
        
        # 工作记忆: 当前任务状态
        self.working: Dict = {}
        
        # 长期记忆: 向量数据库
        self.long_term = VectorStoreMemory()
    
    # === 短期记忆 ===
    def add_short_term(self, role: str, content: str):
        """添加短期记忆"""
        self.short_term.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # 保持最近N条
        if len(self.short_term) > self.max_short_term:
            self.short_term.pop(0)
    
    def get_context(self, n: int = 5) -> str:
        """获取最近n轮对话"""
        recent = self.short_term[-n:]
        return "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in recent
        ])
    
    # === 工作记忆 ===
    def update_working(self, key: str, value):
        """更新工作记忆"""
        self.working[key] = {
            "value": value,
            "updated_at": datetime.now()
        }
    
    def get_working(self, key: str):
        """获取工作记忆"""
        return self.working.get(key, {}).get("value")
    
    # === 长期记忆 ===
    def store_long_term(self, content: str, metadata: dict = None):
        """存储到长期记忆"""
        self.long_term.add(content, metadata)
    
    def recall_long_term(self, query: str, top_k: int = 5):
        """从长期记忆检索"""
        return self.long_term.search(query, top_k)
    
    # === 总结压缩 ===
    def summarize_context(self):
        """当上下文过长时，压缩历史"""
        if len(self.short_term) > self.max_short_term:
            # 保留最近5条
            recent = self.short_term[-5:]
            
            # 总结较早的对话
            old_conversations = self.short_term[:-5]
            summary = self._summarize(old_conversations)
            
            # 存储到长期记忆
            self.store_long_term(summary, {"type": "conversation_summary"})
            
            # 更新短期记忆
            self.short_term = [
                {"role": "system", "content": f"历史摘要: {summary}"}
            ] + recent
    
    def _summarize(self, conversations: List[Dict]) -> str:
        """使用LLM总结对话"""
        text = "\n".join([
            f"{c['role']}: {c['content']}" 
            for c in conversations
        ])
        
        prompt = f"请总结以下对话的关键信息:\n{text}"
        return llm.invoke(prompt).content
```

### 6.2 向量记忆实现

```python
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings

class VectorStoreMemory:
    """向量存储的长期记忆"""
    
    def __init__(self, persist_directory="./memory_db"):
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore = Chroma(
            embedding_function=self.embeddings,
            persist_directory=persist_directory
        )
    
    def add(self, content: str, metadata: dict = None):
        """添加记忆"""
        self.vectorstore.add_texts(
            texts=[content],
            metadatas=[metadata or {}]
        )
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """检索相关记忆"""
        docs = self.vectorstore.similarity_search(query, k=top_k)
        
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "relevance": "high"  # 可以计算实际相似度
            }
            for doc in docs
        ]
    
    def search_with_threshold(self, query: str, threshold: float = 0.7):
        """带阈值过滤的检索"""
        docs_with_scores = self.vectorstore.similarity_search_with_score(query)
        
        return [
            doc for doc, score in docs_with_scores 
            if score >= threshold
        ]

# 用户偏好记忆
class UserPreferenceMemory:
    """用户偏好记忆"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.preferences = self._load_preferences()
    
    def record_preference(self, category: str, preference: str):
        """记录用户偏好"""
        if category not in self.preferences:
            self.preferences[category] = []
        
        self.preferences[category].append({
            "value": preference,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_preferences()
    
    def get_preference(self, category: str) -> List[str]:
        """获取用户偏好"""
        return [p["value"] for p in self.preferences.get(category, [])]
    
    def _load_preferences(self):
        # 从数据库或文件加载
        pass
    
    def _save_preferences(self):
        # 保存到数据库或文件
        pass
```

---

## 7. 错误处理与降级

### 7.1 错误处理策略

```python
from enum import Enum
from typing import Optional
import asyncio

class ErrorType(Enum):
    LLM_ERROR = "llm_error"
    TOOL_ERROR = "tool_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"

class AgentErrorHandler:
    """Agent错误处理器"""
    
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 1
    
    async def handle_with_retry(
        self, 
        func, 
        *args, 
        **kwargs
    ):
        """带重试的执行"""
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            
            except RateLimitError as e:
                # 限流错误: 等待后重试
                wait_time = self._extract_wait_time(e)
                await asyncio.sleep(wait_time)
            
            except TimeoutError:
                # 超时错误: 降级处理
                return self._fallback_response()
            
            except LLMAPIError as e:
                # API错误: 切换备用模型
                if attempt == self.max_retries - 1:
                    return self._handle_final_error(e)
                
                kwargs["model"] = self._get_backup_model()
            
            except Exception as e:
                # 未知错误: 记录并返回友好消息
                self._log_error(e)
                return self._generic_error_response()
        
        return self._generic_error_response()
    
    def _fallback_response(self):
        """降级响应"""
        return {
            "success": False,
            "message": "服务暂时繁忙，请稍后再试",
            "fallback": True
        }
    
    def _get_backup_model(self):
        """获取备用模型"""
        return "gpt-3.5-turbo"  # 降级到更便宜的模型
    
    def _handle_final_error(self, error):
        """最终错误处理"""
        return {
            "success": False,
            "error": str(error),
            "action": "escalate_to_human"
        }
```

### 7.2 降级策略

```python
class DegradationStrategy:
    """降级策略"""
    
    def __init__(self):
        self.strategies = {
            "llm_failure": self._llm_fallback,
            "tool_failure": self._tool_fallback,
            "db_failure": self._db_fallback,
            "full_failure": self._full_fallback
        }
    
    def execute(self, strategy_name: str, context: dict):
        """执行降级策略"""
        strategy = self.strategies.get(strategy_name)
        
        if strategy:
            return strategy(context)
        else:
            return self._full_fallback(context)
    
    def _llm_fallback(self, context):
        """LLM降级: 使用缓存或规则"""
        # 1. 尝试缓存
        cached = self._check_cache(context["query"])
        if cached:
            return cached
        
        # 2. 使用规则引擎
        rule_result = self._apply_rules(context["query"])
        if rule_result:
            return rule_result
        
        # 3. 返回模板响应
        return "抱歉，智能服务暂时不可用，请稍后再试"
    
    def _tool_fallback(self, context):
        """工具降级: 使用简化逻辑"""
        tool_name = context.get("tool_name")
        
        # 使用缓存的工具结果
        if tool_name == "search":
            return "搜索服务暂时不可用"
        elif tool_name == "database":
            return self._get_cached_data()
        
        return "相关服务暂时不可用"
    
    def _db_fallback(self, context):
        """数据库降级: 使用只读副本或缓存"""
        # 切换到只读副本
        # 或返回缓存数据
        pass
    
    def _full_fallback(self, context):
        """完全降级: 转人工"""
        return {
            "message": "系统繁忙，正在为您转接人工客服...",
            "action": "transfer_to_human",
            "context": context
        }
```

---

## 8. 性能优化

### 8.1 响应速度优化

```python
# 1. 流式输出
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

llm = ChatOpenAI(
    model="gpt-4",
    streaming=True,
    callbacks=[StreamingStdOutCallbackHandler()]
)

# 2. 并行工具调用
async def parallel_tool_calls(tools_to_call):
    """并行执行多个工具"""
    tasks = [tool.run_async(params) for tool, params in tools_to_call]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# 3. 缓存常见问题
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_response(query_hash: str):
    """缓存常见问题"""
    return cached_response

# 4. 预加载
class AgentPreloader:
    """预加载资源"""
    
    def __init__(self):
        self.warm_up_complete = False
    
    async def warm_up(self):
        """预热"""
        # 预加载向量索引
        await self._load_vector_index()
        
        # 预加载常见工具
        await self._initialize_tools()
        
        # 预热LLM连接
        await self._ping_llm()
        
        self.warm_up_complete = True
```

### 8.2 成本优化

```python
class CostOptimizer:
    """成本优化器"""
    
    def __init__(self):
        self.model_costs = {
            "gpt-4": 0.03,  # 每1K tokens
            "gpt-3.5-turbo": 0.002,
            "claude-3": 0.015
        }
    
    def select_model(self, query: str, complexity_threshold: float = 0.7):
        """智能选择模型"""
        complexity = self._assess_complexity(query)
        
        if complexity > complexity_threshold:
            return "gpt-4"
        else:
            return "gpt-3.5-turbo"
    
    def _assess_complexity(self, query: str) -> float:
        """评估查询复杂度"""
        # 基于规则评估
        score = 0
        
        if len(query) > 200:
            score += 0.2
        if "分析" in query or "比较" in query:
            score += 0.3
        if "为什么" in query:
            score += 0.2
        
        return min(score, 1.0)
    
    def compress_context(self, context: str) -> str:
        """压缩上下文"""
        # 使用LLM总结
        prompt = f"请压缩以下内容，保留关键信息:\n{context}"
        return llm.invoke(prompt).content
```

---

## 9. 开发检查清单

```markdown
## Agent开发检查清单

### 需求阶段
- [ ] 明确Agent的目标和边界
- [ ] 识别所有用户场景
- [ ] 定义成功指标

### 设计阶段
- [ ] 选择合适的Agent模式
- [ ] 设计Agent角色和职责
- [ ] 规划工具集
- [ ] 设计记忆系统

### 开发阶段
- [ ] 实现核心Agent逻辑
- [ ] 开发必要工具
- [ ] 编写系统Prompt
- [ ] 实现错误处理
- [ ] 添加日志记录

### 测试阶段
- [ ] 单元测试
- [ ] 集成测试
- [ ] 边界测试
- [ ] 性能测试
- [ ] 安全测试

### 部署阶段
- [ ] 容器化
- [ ] 配置监控
- [ ] 设置告警
- [ ] 准备降级方案

### 上线后
- [ ] 监控关键指标
- [ ] 收集用户反馈
- [ ] 持续优化
```

---

*下一章节: 部署与运维指南 →*
