"""
智能客服Agent - FastAPI服务入口
集成技能管理 API
"""
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from config import Config, IntentManager
from agent import CustomerServiceAgent, create_agent

# Skills 相关导入
from skills import skill_registry
from skills.hot_reload import init_hot_reloader, get_hot_reloader

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


# ===== 技能管理 API =====

@app.get("/api/skills")
def list_skills():
    """
    列出所有已注册技能

    返回所有技能的详细信息，包括名称、描述、版本、支持的意图等
    """
    skills = skill_registry.list_skills()
    return {
        "total": len(skills),
        "skills": skills
    }


@app.post("/api/skills/reload")
def reload_skills():
    """
    重新加载所有技能

    清除现有技能注册，重新扫描并注册所有技能
    """
    try:
        count = skill_registry.reload_all()
        return {
            "status": "ok",
            "message": f"成功重新加载 {count} 个技能",
            "count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重载技能失败: {str(e)}")


@app.post("/api/skills/{skill_name}/reload")
def reload_skill(skill_name: str):
    """
    重新加载指定技能

    - **skill_name**: 要重载的技能名称
    """
    reloader = get_hot_reloader()
    if reloader:
        success = reloader.reload_skill(skill_name)
        return {"success": success, "skill_name": skill_name}
    else:
        raise HTTPException(status_code=503, detail="热加载功能未启用")


@app.delete("/api/skills/{skill_name}")
def remove_skill(skill_name: str):
    """
    移除指定技能

    - **skill_name**: 要移除的技能名称
    """
    reloader = get_hot_reloader()
    if reloader:
        success = reloader.remove_skill(skill_name)
        return {"success": success, "skill_name": skill_name}
    else:
        # 直接从注册中心移除
        success = skill_registry.unregister(skill_name)
        return {"success": success, "skill_name": skill_name}


@app.post("/api/skills/{skill_name}/enable")
def enable_skill(skill_name: str):
    """
    启用指定技能

    - **skill_name**: 要启用的技能名称
    """
    success = skill_registry.enable_skill(skill_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"技能 {skill_name} 不存在")
    return {"success": True, "skill_name": skill_name}


@app.post("/api/skills/{skill_name}/disable")
def disable_skill(skill_name: str):
    """
    禁用指定技能

    - **skill_name**: 要禁用的技能名称
    """
    success = skill_registry.disable_skill(skill_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"技能 {skill_name} 不存在")
    return {"success": True, "skill_name": skill_name}


# ===== 配置刷新 API =====

@app.post("/api/config/refresh")
def refresh_config():
    """
    刷新配置

    1. 重新扫描 skills 目录下注册的技能
    2. 检查 config 文件夹下配置文件的更新状态
    3. 返回最新的技能列表（包含 quick_actions）
    """
    import os
    from datetime import datetime

    project_root = os.path.dirname(os.path.dirname(__file__))
    skills_dir = os.path.join(project_root, "skills")
    config_dir = os.path.join(project_root, "config")

    result = {
        "status": "ok",
        "skills": {},
        "config_files": {},
        "reloaded": False
    }

    # 1. 扫描 skills 目录
    if os.path.exists(skills_dir):
        skill_dirs = []
        for item in os.listdir(skills_dir):
            item_path = os.path.join(skills_dir, item)
            if os.path.isdir(item_path) and not item.startswith('_'):
                # 检查是否有 SKILL.md 或 scripts/executor.py
                has_skill_md = os.path.exists(os.path.join(item_path, "SKILL.md"))
                has_executor = os.path.exists(os.path.join(item_path, "scripts", "executor.py"))
                if has_skill_md or has_executor:
                    skill_dirs.append({
                        "name": item,
                        "has_skill_md": has_skill_md,
                        "has_executor": has_executor
                    })
        result["skills"]["directories"] = skill_dirs
        result["skills"]["count"] = len(skill_dirs)

    # 2. 检查 config 目录下的文件状态
    config_files_status = []
    if os.path.exists(config_dir):
        for filename in os.listdir(config_dir):
            if filename.endswith(('.yaml', '.yml')):
                filepath = os.path.join(config_dir, filename)
                stat = os.stat(filepath)
                mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
                config_files_status.append({
                    "name": filename,
                    "path": filepath,
                    "modified_time": mtime,
                    "size": stat.st_size
                })
    result["config_files"]["list"] = config_files_status
    result["config_files"]["count"] = len(config_files_status)

    # 3. 重新加载配置
    try:
        # 查找配置文件
        config_path = os.path.join(config_dir, "skills.yaml")
        if not os.path.exists(config_path):
            config_path = os.path.join(skills_dir, "skills.yaml")

        if os.path.exists(config_path):
            count = skill_registry.reload_all()
            result["reloaded"] = True
            result["message"] = f"成功重新加载 {count} 个技能"
            result["loaded_count"] = count
            # 返回最新的技能列表
            result["skills"]["registered"] = skill_registry.list_skills()
        else:
            result["message"] = "未找到配置文件 skills.yaml"
            result["reloaded"] = False
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"重载配置失败: {str(e)}"
        result["reloaded"] = False

    return result


@app.get("/api/config/status")
def get_config_status():
    """
    获取配置状态

    返回当前配置文件的状态和已注册的技能信息
    """
    import os
    from datetime import datetime

    project_root = os.path.dirname(os.path.dirname(__file__))
    config_dir = os.path.join(project_root, "config")

    # 获取配置文件状态
    config_status = {
        "config_dir": config_dir,
        "exists": os.path.exists(config_dir),
        "files": []
    }

    if os.path.exists(config_dir):
        for filename in os.listdir(config_dir):
            if filename.endswith(('.yaml', '.yml')):
                filepath = os.path.join(config_dir, filename)
                stat = os.stat(filepath)
                config_status["files"].append({
                    "name": filename,
                    "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size": stat.st_size
                })

    # 获取已注册技能
    registered_skills = skill_registry.list_skills()

    return {
        "config": config_status,
        "registered_skills": {
            "count": len(registered_skills),
            "list": registered_skills
        }
    }


def main():
    """启动服务"""
    import uvicorn
    import os
    import logging

    # 配置日志格式
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 技能执行日志单独配置（更详细的输出）
    skill_logger = logging.getLogger("skill_execution")
    skill_logger.setLevel(logging.DEBUG)

    # 验证配置
    try:
        Config.validate()
        print(f"[OK] 配置验证通过")
        print(f"[OK] 使用模型: {Config.MODEL_NAME}")
    except ValueError as e:
        print(f"[ERROR] 配置错误: {e}")
        print("请创建 .env 文件并配置 SILICONFLOW_API_KEY")
        return

    # 加载意图配置
    intents_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "intents.yaml")
    if os.path.exists(intents_path):
        count = IntentManager.load(intents_path)
        print(f"[OK] 加载意图配置，共 {count} 个意图")
    else:
        print(f"[WARN] 未找到意图配置文件: {intents_path}")

    # 初始化技能系统
    if Config.SKILLS_ENABLED:
        try:
            from skills import skill_registry

            # 优先从配置文件加载（优先 config 目录）
            project_root = os.path.dirname(os.path.dirname(__file__))
            config_path = os.path.join(project_root, "config", "skills.yaml")

            if not os.path.exists(config_path):
                # 降级到 skills 目录
                config_path = os.path.join(project_root, "skills", "skills.yaml")

            if os.path.exists(config_path):
                count = skill_registry.load_from_config(config_path)
                print(f"[OK] 从配置文件加载技能，注册 {count} 个技能")
            else:
                # 降级到自动发现
                count = skill_registry.auto_discover()
                print(f"[OK] 自动发现技能，注册 {count} 个技能")

            # 初始化热加载
            if Config.SKILLS_HOT_RELOAD:
                skills_dir = os.path.join(project_root, "skills")
                if os.path.exists(skills_dir):
                    reloader = init_hot_reloader(skill_registry, skills_dir)
                    reloader.start_watch()
                    print(f"[OK] 技能热加载已启用")
        except Exception as e:
            print(f"[WARN] 技能系统初始化失败: {e}")

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
