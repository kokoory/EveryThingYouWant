"""FastAPI application for the Requirements Management System."""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .graph_engine import GraphEngine
from .models import (
    BaselineRequest,
    CreateLinkRequest,
    CreateNodeRequest,
    UpdateNodeRequest,
)

engine = GraphEngine(project_name="requirements")


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine.load()
    yield
    engine.save()


app = FastAPI(
    title="Requirements Graph Manager",
    description="IBM DOORS-like requirements management tool using graph-based architecture",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


# ── Frontend ──

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    index_path = FRONTEND_DIR / "index.html"
    return index_path.read_text(encoding="utf-8")


# ── Node Endpoints ──

@app.get("/api/nodes")
async def list_nodes(subsystem: Optional[str] = None, node_type: Optional[str] = None):
    return engine.get_all_nodes(subsystem=subsystem, node_type=node_type)


@app.post("/api/nodes")
async def create_node(req: CreateNodeRequest):
    node = engine.add_node(req)
    engine.save()
    return node


@app.get("/api/nodes/{node_id}")
async def get_node(node_id: str):
    node = engine.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@app.put("/api/nodes/{node_id}")
async def update_node(node_id: str, req: UpdateNodeRequest):
    node = engine.update_node(node_id, req)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    engine.save()
    return node


@app.delete("/api/nodes/{node_id}")
async def delete_node(node_id: str):
    if not engine.delete_node(node_id):
        raise HTTPException(status_code=404, detail="Node not found")
    engine.save()
    return {"status": "deleted"}


# ── Link Endpoints ──

@app.get("/api/links")
async def list_links():
    return engine.get_all_links()


@app.post("/api/links")
async def create_link(req: CreateLinkRequest):
    link = engine.add_link(req)
    if not link:
        raise HTTPException(status_code=400, detail="Source or target node not found")
    engine.save()
    return link


@app.delete("/api/links/{source_id}/{target_id}")
async def delete_link(source_id: str, target_id: str):
    if not engine.delete_link(source_id, target_id):
        raise HTTPException(status_code=404, detail="Link not found")
    engine.save()
    return {"status": "deleted"}


@app.get("/api/nodes/{node_id}/links")
async def get_node_links(node_id: str):
    return engine.get_node_links(node_id)


# ── Suspect Link Endpoints ──

@app.get("/api/suspects/nodes")
async def get_suspect_nodes():
    return engine.get_suspect_nodes()


@app.get("/api/suspects/links")
async def get_suspect_links():
    return engine.get_suspect_links()


@app.post("/api/suspects/link/resolve")
async def resolve_suspect_link(source_id: str, target_id: str):
    if not engine.resolve_suspect_link(source_id, target_id):
        raise HTTPException(status_code=404, detail="Link not found")
    engine.save()
    return {"status": "resolved", "source_id": source_id, "target_id": target_id}


@app.post("/api/suspects/{node_id}/resolve")
async def resolve_suspect(node_id: str):
    result = engine.resolve_suspect(node_id)
    if not result:
        raise HTTPException(status_code=404, detail="Node not found")
    engine.save()
    return result


# ── Impact Analysis ──

@app.get("/api/impact/{node_id}")
async def impact_analysis(node_id: str, depth: int = -1):
    result = engine.impact_analysis(node_id, depth=depth)
    if not result.get("affected_nodes") and node_id not in engine.graph.nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    return result


# ── Baseline (Version) Endpoints ──

@app.get("/api/baselines")
async def list_baselines():
    return engine.list_baselines()


@app.post("/api/baselines")
async def create_baseline(req: BaselineRequest):
    baseline = engine.create_baseline(req.name, req.description)
    engine.save()
    return baseline


@app.post("/api/baselines/{name}/restore")
async def restore_baseline(name: str):
    if not engine.restore_baseline(name):
        raise HTTPException(status_code=404, detail="Baseline not found")
    engine.save()
    return {"status": "restored", "baseline": name}


@app.get("/api/baselines/compare")
async def compare_baselines(name1: str, name2: str):
    result = engine.compare_baselines(name1, name2)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ── Tree View ──

@app.get("/api/tree")
async def get_tree_view(root_id: Optional[str] = None):
    return engine.get_tree_view(root_id=root_id)


# ── Subsystems ──

@app.get("/api/subsystems")
async def get_subsystems():
    return engine.get_subsystems()


# ── Graph Visualization Data ──

@app.get("/api/graph/vis")
async def get_vis_data():
    return engine.to_vis_data()


# ── Statistics ──

@app.get("/api/stats")
async def get_statistics():
    return engine.get_statistics()


# ── History ──

@app.get("/api/history")
async def get_history(limit: int = 50):
    return engine.change_history[-limit:]


# ── Demo Data ──

@app.post("/api/demo/load")
async def load_demo_data():
    """Load sample data for demonstration."""
    if engine.graph.number_of_nodes() > 0:
        return {"status": "skipped", "message": "Data already exists"}

    # System-level requirements
    reqs = [
        ("SYS-001", "시스템 전원 관리", "시스템은 전원 On/Off를 제어할 수 있어야 한다", "requirement", "critical", "SS"),
        ("SYS-002", "비상 정지", "비상 상황 시 3초 이내 시스템을 정지할 수 있어야 한다", "requirement", "critical", "SS"),
        ("SYS-003", "사용자 인증", "시스템 접근 시 사용자 인증을 수행해야 한다", "requirement", "high", "GCS"),
        ("SPC-001", "전원 모듈 설계", "전원 모듈은 12V DC 입력을 지원한다", "specification", "high", "SS"),
        ("SPC-002", "비상 정지 회로", "하드웨어 레벨의 비상 정지 회로를 구현한다", "specification", "critical", "AVS"),
        ("SPC-003", "인증 프로토콜", "OAuth 2.0 기반 인증을 적용한다", "specification", "high", "GCS"),
        ("DES-001", "전원 회로도", "전원 공급 회로의 상세 설계", "design", "high", "SS"),
        ("TST-001", "전원 On/Off 테스트", "전원 켜기/끄기 100회 반복 테스트", "test_case", "high", "SS"),
        ("TST-002", "비상 정지 응답 테스트", "비상 정지 시간 측정 테스트", "test_case", "critical", "AVS"),
        ("TST-003", "인증 보안 테스트", "인증 우회 시도 및 보안 검증", "test_case", "high", "GCS"),
        ("RSK-001", "전원 불안정 위험", "입력 전원 불안정 시 시스템 오동작 위험", "risk", "high", "DLS"),
    ]

    for rid, title, content, ntype, priority, subsystem in reqs:
        engine.add_node(CreateNodeRequest(
            id=rid, title=title, content=content,
            node_type=ntype, priority=priority,
            author="시스템", subsystem=subsystem,
        ))

    # Traceability links
    links = [
        ("SYS-001", "SPC-001", "derives_from"),
        ("SYS-002", "SPC-002", "derives_from"),
        ("SYS-003", "SPC-003", "derives_from"),
        ("SPC-001", "DES-001", "derives_from"),
        ("SPC-001", "TST-001", "verified_by"),
        ("SPC-002", "TST-002", "verified_by"),
        ("SPC-003", "TST-003", "verified_by"),
        ("RSK-001", "SPC-001", "mitigated_by"),
        ("SYS-001", "TST-001", "traces_to"),
        ("SYS-002", "TST-002", "traces_to"),
    ]

    for src, tgt, ltype in links:
        engine.add_link(CreateLinkRequest(source_id=src, target_id=tgt, link_type=ltype))

    engine.create_baseline("v1.0-initial", "초기 요구사항 베이스라인")
    engine.save()

    return {"status": "loaded", "nodes": engine.graph.number_of_nodes(), "links": engine.graph.number_of_edges()}
