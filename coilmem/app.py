"""FastAPI wrapper over store.py. Run: uvicorn coilmem.app:app

Env:
  COILMEM_KEY  required — value clients must send in X-API-Key
  COILMEM_DB   optional — sqlite path (default coilmem.db)
  OPENAI_API_KEY required — used by the embedder
"""
import os
import threading

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from . import store
from .config import load_env

load_env()  # populate os.environ from ./.env before reading any var

app = FastAPI(title="coilmem", version="0.1.0")

_conn = store.connect(os.environ.get("COILMEM_DB", "coilmem.db"))
_lock = threading.Lock()  # ponytail: one global lock; fine for MVP throughput.


def require_key(x_api_key: str = Header(default="")):
    expected = os.environ.get("COILMEM_KEY")
    if not expected or x_api_key != expected:
        raise HTTPException(status_code=401, detail="bad or missing X-API-Key")


class WriteReq(BaseModel):
    workspace: str
    agent_id: str
    scope: str  # "private" | "shared"
    text: str
    metadata: dict | None = None


@app.post("/memory", dependencies=[Depends(require_key)])
def write_memory(req: WriteReq):
    try:
        with _lock:
            mem_id = store.add(_conn, req.workspace, req.agent_id, req.scope, req.text, req.metadata)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": mem_id}


@app.get("/memory/search", dependencies=[Depends(require_key)])
def search_memory(workspace: str, agent_id: str, query: str, k: int = 5):
    with _lock:
        return {"results": store.search(_conn, workspace, agent_id, query, k)}


@app.get("/memory", dependencies=[Depends(require_key)])
def list_memory(workspace: str, agent_id: str):
    with _lock:
        return {"memories": store.list_memories(_conn, workspace, agent_id)}


@app.delete("/memory/{mem_id}", dependencies=[Depends(require_key)])
def delete_memory(mem_id: str):
    with _lock:
        ok = store.delete(_conn, mem_id)
    if not ok:
        raise HTTPException(status_code=404, detail="not found")
    return {"deleted": mem_id}
