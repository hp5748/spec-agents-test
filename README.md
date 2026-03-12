# 智能客服 Agent Demo

基于 LangChain + 通义千问 的智能客服 Agent Demo，支持意图识别、路由分发和多轮对话。

## 功能特性

- ✅ **意图识别**：自动识别用户意图（订单查询/商品咨询/投诉处理/通用问答）
- ✅ **路由分发**：根据意图路由到专业处理模块
- ✅ **多轮对话**：维护对话上下文，支持连续对话
- ✅ **工具调用**：支持订单查询、商品搜索、工单创建等工具
- ✅ **RESTful API**：提供 FastAPI 接口服务

## 技术栈

- **Agent框架**：LangChain 0.2.0
- **LLM**：通义千问（阿里云DashScope API）
- **Web框架**：FastAPI 0.109.0
- **Python**：3.10+

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，并填入你的通义千问 API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：
```
DASHSCOPE_API_KEY=your_dashscope_api_key_here
```

> 获取 API Key：访问 [阿里云DashScope](https://dashscope.console.aliyun.com/) 注册并创建 API Key

### 3. 启动服务

```bash
cd src
python main.py
```

服务启动后访问：
- API服务：http://localhost:8000
- API文档：http://localhost:8000/docs

### 4. 测试对话

使用 curl 测试：

```bash
# 订单查询
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "我的订单12345678到哪了", "session_id": "test"}'

# 商品咨询
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "推荐一款手机", "session_id": "test"}'

# 多轮对话
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "预算3000左右", "session_id": "test"}'
```

或访问 http://localhost:8000/docs 使用交互式API文档测试。

## API 接口

### POST /api/chat

对话接口

**请求体**：
```json
{
  "message": "用户消息",
  "session_id": "会话ID（可选）"
}
```

**响应**：
```json
{
  "session_id": "会话ID",
  "intent": "意图代码",
  "intent_name": "意图名称",
  "response": "回复内容"
}
```

### GET /api/history/{session_id}

获取对话历史

### DELETE /api/history/{session_id}

清空对话历史

### POST /api/session/new

创建新会话

### GET /health

健康检查

## 项目结构

```
.
├── spec/                    # 规范文档
│   ├── Me2AI/              # 人类到AI的沟通文档
│   │   ├── 需求描述.md
│   │   ├── 技术约束.md
│   │   └── 任务规划.md
│   └── AI2AI/              # AI到AI的沟通文档
├── src/                    # 源代码
│   ├── main.py            # FastAPI入口
│   ├── config.py          # 配置管理
│   ├── agent.py           # Agent核心逻辑
│   ├── tools.py           # 工具定义
│   ├── memory.py          # 对话记忆
│   └── prompts.py         # Prompt模板
├── requirements.txt        # 依赖列表
├── .env.example           # 环境变量模板
└── README.md              # 使用说明
```

## 意图类型

| 意图代码 | 意图名称 | 说明 |
|---------|---------|------|
| order_query | 订单查询 | 查询订单状态、物流信息 |
| product_consult | 商品咨询 | 询问商品信息、推荐商品 |
| complaint | 投诉处理 | 投诉、反馈问题 |
| general_qa | 通用问答 | 常见问题、服务说明 |

## 测试用例

### 1. 订单查询
```
用户：我的订单到哪了？
Agent：请提供您的8位订单号，我帮您查询订单状态。
用户：12345678
Agent：订单查询结果：订单号：12345678，状态：已发货...
```

### 2. 商品咨询
```
用户：推荐一款手机
Agent：找到 3 个相关商品：iPhone 15 Pro (¥7999)...
```

### 3. 多轮对话
```
用户：我想买手机
Agent：请问您的预算是多少？
用户：3000左右
Agent：在这个价位我推荐...
```

## 扩展开发

### 添加新工具

在 `src/tools.py` 中添加新的工具类：

```python
class MyNewTool(BaseTool):
    name: str = "my_tool"
    description: str = "工具描述"
    args_schema: type[BaseModel] = MyToolInput

    def _run(self, **kwargs) -> str:
        # 实现工具逻辑
        return "结果"
```

### 添加新意图

1. 在 `src/config.py` 中添加意图类型
2. 在 `src/prompts.py` 中添加对应的提示词模板
3. 在 `src/agent.py` 中添加意图到工具的映射

## 注意事项

- Demo版本使用模拟数据，不需要真实数据库
- 通义千问 API 需要[阿里云账号](https://dashscope.console.aliyun.com/)
- 建议使用 Python 3.10+ 版本

## License

MIT
