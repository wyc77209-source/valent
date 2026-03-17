# main.py
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

# --- 1. 数据模型 (Pydantic) ---

class USS_Metadata(BaseModel):
    """
    用于在 Oasis/NemoClaw 生态系统中进行路由、安全和跟踪的元数据。
    """
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="任务的唯一标识符。")
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="任务创建的 ISO 8601 时间戳。")
    source_ip: Optional[str] = Field(None, description="请求的源 IP 地址。")
    user_id: Optional[str] = Field(None, description="来自 Oasis 平台认证的用户 ID。")
    wallet_address: Optional[str] = Field(None, description="用户的 Web3 钱包地址（如果已连接）。")
    priority: Literal['low', 'normal', 'high', 'critical'] = 'normal'
    required_track: Optional[Literal['groq_lpu', 'vera_rubin', 'clara_tee']] = Field(None, description="需要的特定计算轨道（例如，用于低延迟或复杂推理）。")

class USS_Task(BaseModel):
    """
    通用自进化服务 (USS) 任务对象。
    此对象封装了用户的请求，是传递给 NemoClaw Agent 编排层的标准工作单元。
    """
    metadata: USS_Metadata
    prompt: str = Field(..., description="用户的原始输入提示。")
    params: Dict[str, Any] = Field(default_factory=dict, description="任务的附加参数，如 temperature, max_tokens 等。")
    target_agent: Optional[str] = Field(None, description="指定目标 Agent（例如，'QuantAlpha', 'ClinicalMonitor'）。如果为 None，则由路由器决定。")

# --- 2. FastAPI 应用实例 ---

app = FastAPI(
    title="Oasis NemoClaw Gateway",
    description="支持 REST 和 WebSocket 的 FastAPI 入口，用于对接 NVIDIA NemoClaw 协议并封装 USS_Task 对象。",
    version="2.0.0",
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- 3. REST API 端点 ---

@app.post("/api/v1/task", response_model=USS_Task)
async def create_task_rest(prompt: str, user_id: Optional[str] = None, wallet_address: Optional[str] = None):
    """
    通过 REST API 接收一个 prompt，将其包装成一个 USS_Task 对象并返回。
    这模拟了 NemoClaw 的同步请求入口。
    """
    # 模拟 NemoClaw 握手协议：在这里，它只是一个成功的 HTTP 请求/响应周期。
    # 在生产环境中，这里可能包含认证、头信息验证等步骤。
    print(f"[REST] 收到来自用户 '{user_id or 'anonymous'}' 的 prompt。")

    metadata = USS_Metadata(
        user_id=user_id,
        wallet_address=wallet_address,
        priority='high' # REST 请求通常被视为高优先级
    )
    
    uss_task = USS_Task(
        metadata=metadata,
        prompt=prompt
    )
    
    # 在实际应用中，此任务对象将被分派给 NemoClaw Agent。
    # dispatch_to_nemoclaw(uss_task)
    
    return uss_task

# --- 4. WebSocket 端点 ---

@app.websocket("/ws/task")
async def task_websocket(websocket: WebSocket, user_id: Optional[str] = None, wallet_address: Optional[str] = None):
    """
    通过 WebSocket 处理实时、流式的 Agent 交互。
    """
    await manager.connect(websocket)
    
    # 1. 模拟 NemoClaw 握手协议
    # 发送一个欢迎消息，确认连接已建立并准备好接收任务。
    await websocket.send_json({"status": "connected", "message": "Oasis-NemoClaw Gateway 已连接。准备接收 USS_Task。"})
    print(f"[WS] 客户端 '{user_id or wallet_address or 'anonymous'}' 已连接。")

    try:
        while True:
            # 2. 等待客户端发送 prompt
            data = await websocket.receive_text()
            
            # 3. 将 prompt 包装成 USS_Task 对象
            metadata = USS_Metadata(
                user_id=user_id,
                wallet_address=wallet_address,
                source_ip=websocket.client.host
            )
            uss_task = USS_Task(metadata=metadata, prompt=data)
            
            # 4. 将创建的 USS_Task 发回给客户端进行确认
            await websocket.send_json({"status": "task_created", "task": uss_task.dict()})
            print(f"[WS] 为客户端 '{user_id or 'anonymous'}' 创建了任务: {uss_task.metadata.task_id}")

            # 5. 模拟 Agent 流式响应
            # 在实际应用中，这里会调用 NemoClaw Agent 并流式传输其响应。
            await asyncio.sleep(0.5) # 模拟初始处理延迟
            response_chunks = ["正在分析您的请求...", "路由到 'QuantAlpha' Agent...", "正在生成初步见解...", "完成。"]
            for chunk in response_chunks:
                await websocket.send_json({"status": "streaming_response", "chunk": chunk, "task_id": uss_task.metadata.task_id})
                await asyncio.sleep(0.8) # 模拟每个 chunk 之间的延迟

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"[WS] 客户端 '{user_id or 'anonymous'}' 已断开连接。")
    except Exception as e:
        print(f"[WS] 发生错误: {e}")
        await websocket.send_json({"status": "error", "message": str(e)})
        manager.disconnect(websocket)

# --- 5. 根端点 ---

@app.get("/")
async def root():
    return {"message": "欢迎来到 Oasis NemoClaw Gateway。请使用 /api/v1/task (REST) 或 /ws/task (WebSocket) 端点。"}

# --- 运行服务器 (用于本地测试) ---
# 在生产环境中，使用 Gunicorn 或 Uvicorn 运行
# uvicorn main:app --host 0.0.0.0 --port 8000 --reload
