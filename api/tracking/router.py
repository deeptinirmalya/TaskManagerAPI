from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import JSONResponse
from security.auth import token_required
from typing import Dict, List
import uuid

tracking_router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, message: dict, session_id: str):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                await connection.send_json(message)

manager = ConnectionManager()

@tracking_router.post("/create")
async def create_session(_user_data: dict = Depends(token_required(allowed_roles=["user"]))):
    try:
        session_id = str(uuid.uuid4())
        manager.active_connections[session_id] = []
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Tracking session created successfully",
                "data": {
                    "session_id": session_id
                },
                "error": None
            }
        )
    except HTTPException as httpe:
        raise httpe
    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@tracking_router.websocket("/ws/{session_id}")
async def tracking_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(data, session_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
