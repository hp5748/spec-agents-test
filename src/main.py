"""
智能客服Agent - FastAPI服务入口
"""
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from config import Config
from agent import CustomerServiceAgent, create_agent

# 创建FastAPI应用（禁用默认docs，使用自定义）
app = FastAPI(
    title="智能客服Agent API",
    description="基于 DeepSeek 的智能客服Agent Demo",
    version="1.0.0",
    docs_url=None,  # 禁用默认docs
    redoc_url=None  # 禁用默认redoc
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 自定义 Swagger UI（使用国内CDN）
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
    )


# 前端页面
@app.get("/chat", include_in_schema=False)
async def chat_page():
    """前端对话页面"""
    import os
    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "index.html")
    return FileResponse(static_path)


# 请求/响应模型
class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    """对话响应"""
    session_id: str
    intent: str
    intent_name: str
    response: str


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    model: str


class HistoryResponse(BaseModel):
    """对话历史响应"""
    session_id: str
    history: list


# 存储Agent实例的缓存
agent_cache: dict = {}


def get_agent(session_id: str) -> CustomerServiceAgent:
    """获取或创建Agent实例"""
    if session_id not in agent_cache:
        agent_cache[session_id] = create_agent(session_id)
    return agent_cache[session_id]


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "智能客服Agent API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="healthy",
        model=Config.MODEL_NAME
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    对话接口

    - **message**: 用户输入的消息
    - **session_id**: 会话ID（可选，用于保持多轮对话上下文）
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    try:
        # 获取或创建Agent
        agent = get_agent(request.session_id)

        # 处理对话
        result = agent.chat(request.message.strip())

        return ChatResponse(
            session_id=request.session_id,
            intent=result["intent"],
            intent_name=result["intent_name"],
            response=result["response"]
        )

    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式对话接口（SSE长连接）

    - **message**: 用户输入的消息
    - **session_id**: 会话ID（可选，用于保持多轮对话上下文）

    返回 Server-Sent Events 流:
    - type: intent - 意图识别结果
    - type: content - 内容块
    - type: done - 完成
    - type: error - 错误
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    try:
        agent = get_agent(request.session_id)

        def event_generator():
            for chunk in agent.chat_stream_simple(request.message.strip()):
                yield chunk

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")


@app.get("/api/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str):
    """
    获取对话历史

    - **session_id**: 会话ID
    """
    agent = get_agent(session_id)
    history = agent.get_history()

    return HistoryResponse(
        session_id=session_id,
        history=history
    )


@app.delete("/api/history/{session_id}")
async def clear_history(session_id: str):
    """
    清空对话历史

    - **session_id**: 会话ID
    """
    agent = get_agent(session_id)
    agent.clear_history()

    if session_id in agent_cache:
        del agent_cache[session_id]

    return {"message": f"会话 {session_id} 的历史已清空"}


@app.post("/api/session/new")
async def new_session():
    """创建新会话"""
    session_id = str(uuid.uuid4())[:8]
    return {"session_id": session_id}


def main():
    """启动服务"""
    import uvicorn

    # 验证配置
    try:
        Config.validate()
        print(f"[OK] 配置验证通过")
        print(f"[OK] 使用模型: {Config.MODEL_NAME}")
    except ValueError as e:
        print(f"[ERROR] 配置错误: {e}")
        print("请创建 .env 文件并配置 SILICONFLOW_API_KEY")
        return

    print(f"\n启动智能客服Agent服务...")
    print(f"访问地址: http://{Config.HOST}:{Config.PORT}")
    print(f"API文档: http://{Config.HOST}:{Config.PORT}/docs")
    print(f"\n按 Ctrl+C 停止服务\n")

    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=False,
        log_level=Config.LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    main()
