"""FastAPI application for the Requirements Management System."""

import base64
import io
import json
import shutil
import uuid as uuid_mod
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .graph_engine import GraphEngine, DATA_DIR
from .models import (
    BaselineRequest,
    CreateLinkRequest,
    CreateNodeRequest,
    SubsystemColorRequest,
    SubsystemRequest,
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

import os as _os
_base = Path(_os.environ.get("RGM_BASE_DIR", Path(__file__).parent.parent))
FRONTEND_DIR = _base / "frontend"


# ── Frontend ──

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    index_path = FRONTEND_DIR / "index.html"
    return index_path.read_text(encoding="utf-8")


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


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


# ── Export ──

@app.get("/api/export/csv")
async def export_csv():
    csv_bytes = engine.export_tree_csv()
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=requirements_tree.csv"},
    )


@app.get("/api/export/csv/template")
async def download_csv_template():
    """Download a blank CSV template for import."""
    import io
    import csv as csv_mod
    out = io.StringIO()
    w = csv_mod.writer(out)
    w.writerow(["ID", "Content", "Analyze", "Inspection", "Demonstration", "Test", "Method", "FT_No", "Attachment", "ETC"])
    w.writerow(["SYS-001", "시스템은 전원 On/Off를 제어할 수 있어야 한다", "", "", "", "X", "", "FT-001", "", ""])
    w.writerow(["SYS-002", "3초 이내 비상 정지가 가능해야 한다", "X", "", "X", "X", "응답시간 측정", "FT-002", "test_plan.pdf", "Critical"])
    w.writerow(["SYS-003", "사용자 인증 수행", "", "X", "", "X", "", "FT-003", "", ""])
    content = b'\xef\xbb\xbf' + out.getvalue().encode('utf-8')
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=import_template.csv"},
    )


@app.post("/api/import/csv")
async def import_csv(file: UploadFile = File(...)):
    content = await file.read()
    result = engine.import_nodes_csv(content)
    engine.save()
    return result


# ── Attachments ──

UPLOAD_DIR = DATA_DIR / "attachments"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/api/nodes/{node_id}/attachments")
async def upload_attachment(node_id: str, file: UploadFile = File(...), description: str = Form("")):
    if node_id not in engine.graph.nodes:
        raise HTTPException(status_code=404, detail="Node not found")

    ext = Path(file.filename).suffix
    file_id = uuid_mod.uuid4().hex[:8]
    stored_name = f"{node_id}_{file_id}{ext}"
    file_path = UPLOAD_DIR / stored_name
    content = await file.read()
    file_path.write_bytes(content)

    attachment = {
        "id": file_id,
        "filename": file.filename,
        "stored_name": stored_name,
        "description": description,
        "size": len(content),
        "uploaded_at": datetime.now().isoformat(),
    }
    attachments = engine.graph.nodes[node_id].get("attachments", [])
    attachments.append(attachment)
    engine.graph.nodes[node_id]["attachments"] = attachments
    engine.save()
    return attachment


@app.get("/api/attachments/{stored_name}")
async def download_attachment(stored_name: str):
    file_path = UPLOAD_DIR / stored_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    content = file_path.read_bytes()
    ext = file_path.suffix.lower()
    media_types = {
        ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg", ".gif": "image/gif", ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".txt": "text/plain", ".csv": "text/csv",
    }
    return Response(
        content=content,
        media_type=media_types.get(ext, "application/octet-stream"),
        headers={"Content-Disposition": f"inline; filename={Path(stored_name).name}"},
    )


@app.delete("/api/nodes/{node_id}/attachments/{file_id}")
async def delete_attachment(node_id: str, file_id: str):
    if node_id not in engine.graph.nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    attachments = engine.graph.nodes[node_id].get("attachments", [])
    target = None
    for a in attachments:
        if a["id"] == file_id:
            target = a
            break
    if not target:
        raise HTTPException(status_code=404, detail="Attachment not found")
    # Delete file
    file_path = UPLOAD_DIR / target["stored_name"]
    if file_path.exists():
        file_path.unlink()
    attachments.remove(target)
    engine.graph.nodes[node_id]["attachments"] = attachments
    engine.save()
    return {"status": "deleted"}


# ── Report ──

@app.get("/api/report", response_class=HTMLResponse)
async def generate_report():
    """Generate a full HTML report with tree, graph, nodes, links, and attachments."""
    nodes = engine.get_all_nodes()
    links = engine.get_all_links()
    tree = engine.get_tree_view()
    stats = engine.get_statistics()
    suspects = engine.get_suspect_nodes()

    verif_labels = {
        "inspection": "Inspection (검사)", "analysis": "Analysis (분석)",
        "demonstration": "Demonstration (시연)", "test": "Test (시험)",
    }
    type_colors = {
        "requirement": "#4A90D9", "specification": "#7B68EE",
        "test_case": "#2ECC71", "design": "#F39C12", "risk": "#E74C3C",
    }
    priority_colors = {"critical": "#E74C3C", "high": "#F39C12", "medium": "#3498DB", "low": "#95A5A6"}

    # Build tree HTML
    def render_tree_html(node, level=0):
        nid = node.get("id", "")
        data = engine.graph.nodes.get(nid, {})
        nt = node.get("node_type", "unknown")
        color = type_colors.get(nt, "#888")
        status = node.get("status", "")
        suspect_mark = ' <span style="color:#E74C3C;font-weight:bold">⚠ SUSPECT</span>' if status == "suspect" else ""
        indent = 24 * level
        html = f'<div style="margin-left:{indent}px;padding:4px 0;border-bottom:1px solid #eee">'
        html += f'<span style="background:{color};color:#fff;padding:1px 6px;border-radius:3px;font-size:11px">{nt[:3].upper()}</span> '
        html += f'<strong>{nid}</strong> - {node.get("title", "")}{suspect_mark}'
        v_raw = data.get("verification", ["test"])
        v_str = ", ".join(v_raw) if isinstance(v_raw, list) else str(v_raw)
        html += f' <small style="color:#888">({v_str} | {data.get("subsystem","SS")} | v{data.get("version",1)})</small>'
        html += '</div>\n'
        for child in node.get("children", []):
            html += render_tree_html(child, level + 1)
        return html

    tree_html = ""
    for root in tree:
        tree_html += render_tree_html(root)

    # Build node detail cards
    node_cards = ""
    for n in sorted(nodes, key=lambda x: x.get("id", "")):
        nid = n.get("id", "")
        nt = n.get("node_type", "")
        color = type_colors.get(nt, "#888")
        pri_color = priority_colors.get(n.get("priority", ""), "#888")
        verif_raw = n.get("verification", ["test"])
        if isinstance(verif_raw, str):
            verif_raw = [verif_raw]
        verif = ", ".join(verif_labels.get(v, v) for v in verif_raw) if verif_raw else ""

        # Links
        node_links = engine.get_node_links(nid)
        incoming_html = ", ".join([f'{l["source_id"]} ({l.get("link_type","")})' for l in node_links["incoming"]]) or "None"
        outgoing_html = ", ".join([f'{l["target_id"]} ({l.get("link_type","")})' for l in node_links["outgoing"]]) or "None"

        # Attachments
        attachments = n.get("attachments", [])
        attach_html = ""
        if attachments:
            attach_html = '<div style="margin-top:8px;page-break-inside:avoid"><strong>Attachments (근거자료):</strong>'
            for a in attachments:
                fname = a.get("filename", "")
                ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                desc = a.get("description", "")
                size_kb = a.get("size", 0) / 1024
                date = a.get("uploaded_at", "")[:10]
                stored = a.get("stored_name", "")

                attach_html += '<div style="margin:8px 0;padding:8px;border:1px solid #e0e0e0;border-radius:4px">'
                attach_html += f'<div style="font-size:13px"><strong>{fname}</strong>'
                if desc:
                    attach_html += f' &mdash; {desc}'
                attach_html += f' <small style="color:#888">({size_kb:.1f}KB, {date})</small></div>'

                if ext in ("png", "jpg", "jpeg", "gif", "bmp", "webp", "svg"):
                    attach_html += f'<img src="/api/attachments/{stored}" style="max-width:100%;max-height:400px;margin-top:6px;border:1px solid #ddd;border-radius:4px" alt="{fname}">'
                elif ext == "pdf":
                    attach_html += f'<div style="margin-top:4px;font-size:12px;color:#4A90D9"><a href="/api/attachments/{stored}" target="_blank">PDF 열기</a></div>'
                elif ext in ("txt", "csv", "log", "md"):
                    txt_path = UPLOAD_DIR / stored
                    if txt_path.exists():
                        try:
                            txt = txt_path.read_text(encoding="utf-8")[:2000]
                            attach_html += f'<pre style="margin-top:6px;padding:8px;background:#f8f8f8;border:1px solid #e0e0e0;border-radius:4px;font-size:12px;white-space:pre-wrap;max-height:200px;overflow-y:auto">{txt}</pre>'
                        except Exception:
                            pass
                else:
                    attach_html += f'<div style="margin-top:4px;font-size:12px;color:#888"><a href="/api/attachments/{stored}" target="_blank">Download</a></div>'

                attach_html += '</div>'
            attach_html += '</div>'

        # Version history
        vh = n.get("version_history", [])
        vh_html = ""
        if vh:
            vh_html = '<div style="margin-top:8px"><strong>Version History:</strong><table style="width:100%;font-size:12px;border-collapse:collapse;margin-top:4px">'
            vh_html += '<tr style="background:#f5f5f5"><th style="padding:4px;text-align:left">Ver</th><th style="padding:4px;text-align:left">Date</th><th style="padding:4px;text-align:left">Changes</th></tr>'
            for v in vh:
                changes_str = "; ".join([f'{k}: {c["old"]}→{c["new"]}' for k, c in v["changes"].items() if k not in ("updated_at", "created_at")])
                vh_html += f'<tr><td style="padding:4px">v{v["version"]}</td><td style="padding:4px">{v["date"][:19]}</td><td style="padding:4px">{changes_str}</td></tr>'
            vh_html += '</table></div>'

        node_cards += f'''
        <div style="border:1px solid #ddd;border-left:4px solid {color};border-radius:6px;padding:16px;margin:12px 0;page-break-inside:avoid">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div>
                    <span style="background:{color};color:#fff;padding:2px 8px;border-radius:3px;font-size:12px">{nt}</span>
                    <span style="background:{pri_color};color:#fff;padding:2px 8px;border-radius:3px;font-size:12px;margin-left:4px">{n.get("priority","")}</span>
                    <strong style="font-size:16px;margin-left:8px">{nid}</strong>
                </div>
                <div style="color:#888;font-size:12px">v{n.get("version",1)} | {n.get("updated_at","")[:10]} | {n.get("subsystem","")}</div>
            </div>
            <h3 style="margin:8px 0 4px">{n.get("title","")}</h3>
            <p style="color:#555;margin:4px 0">{n.get("content","")}</p>
            <div style="display:flex;gap:24px;margin-top:8px;font-size:13px;color:#666">
                <div><strong>Verification:</strong> {verif}</div>
                <div><strong>Status:</strong> {n.get("status","")}</div>
            </div>
            <div style="font-size:12px;color:#666;margin-top:8px">
                <div><strong>Incoming Links:</strong> {incoming_html}</div>
                <div><strong>Outgoing Links:</strong> {outgoing_html}</div>
            </div>
            {attach_html}
            {vh_html}
        </div>'''

    # Links table
    links_table = '<table style="width:100%;border-collapse:collapse;font-size:13px"><tr style="background:#f5f5f5"><th style="padding:8px;text-align:left;border-bottom:2px solid #ddd">Source</th><th style="padding:8px;text-align:left;border-bottom:2px solid #ddd">Target</th><th style="padding:8px;text-align:left;border-bottom:2px solid #ddd">Type</th><th style="padding:8px;text-align:left;border-bottom:2px solid #ddd">Suspect</th></tr>'
    for l in links:
        suspect_style = 'color:#E74C3C;font-weight:bold' if l.get("is_suspect") else ''
        links_table += f'<tr><td style="padding:6px;border-bottom:1px solid #eee">{l.get("source_id","")}</td><td style="padding:6px;border-bottom:1px solid #eee">{l.get("target_id","")}</td><td style="padding:6px;border-bottom:1px solid #eee">{l.get("link_type","")}</td><td style="padding:6px;border-bottom:1px solid #eee;{suspect_style}">{"⚠ YES" if l.get("is_suspect") else "-"}</td></tr>'
    links_table += '</table>'

    # Suspect summary
    suspect_html = ""
    if suspects:
        suspect_html = f'<div style="background:#FFF3F3;border:1px solid #E74C3C;border-radius:6px;padding:16px;margin:12px 0"><h3 style="color:#E74C3C;margin:0 0 8px">⚠ Suspect Items ({len(suspects)})</h3><ul>'
        for s in suspects:
            suspect_html += f'<li><strong>{s["id"]}</strong> - {s.get("title","")} [{s.get("subsystem","")}]</li>'
        suspect_html += '</ul></div>'

    report_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Requirements Report</title>
<style>
    body {{ font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; max-width: 1000px; margin: 0 auto; padding: 24px; color: #333; }}
    h1 {{ border-bottom: 3px solid #4A90D9; padding-bottom: 8px; }}
    h2 {{ color: #4A90D9; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-top: 32px; }}
    .stats {{ display: flex; gap: 16px; margin: 16px 0; }}
    .stat-box {{ flex: 1; padding: 16px; background: #f8f9fa; border-radius: 8px; text-align: center; }}
    .stat-box .num {{ font-size: 28px; font-weight: bold; color: #4A90D9; }}
    .stat-box .label {{ font-size: 12px; color: #888; }}
    @media print {{
        body {{ font-size: 11px; }}
        .stat-box .num {{ font-size: 20px; }}
        h1 {{ font-size: 18px; }}
        h2 {{ font-size: 15px; page-break-before: auto; }}
    }}
</style></head><body>
<h1>Requirements Traceability Report</h1>
<p style="color:#888">Generated: {report_date} | Project: {engine.project_name}</p>

<div class="stats">
    <div class="stat-box"><div class="num">{stats["total_nodes"]}</div><div class="label">Total Nodes</div></div>
    <div class="stat-box"><div class="num">{stats["total_links"]}</div><div class="label">Total Links</div></div>
    <div class="stat-box"><div class="num">{stats["suspect_links"]}</div><div class="label">Suspect Links</div></div>
    <div class="stat-box"><div class="num">{len(stats.get("subsystems",[]))}</div><div class="label">Subsystems</div></div>
    <div class="stat-box"><div class="num">{stats["baselines"]}</div><div class="label">Baselines</div></div>
</div>

{suspect_html}

<h2>1. Requirements Tree (계층 구조)</h2>
<div style="border:1px solid #ddd;border-radius:6px;padding:16px;background:#fafafa">{tree_html}</div>

<h2>2. Traceability Matrix (추적성 매트릭스)</h2>
{links_table}

<h2>3. Node Details (노드 상세)</h2>
{node_cards}

<div style="margin-top:40px;padding-top:16px;border-top:2px solid #ddd;color:#888;font-size:12px;text-align:center">
    Requirements Graph Manager — Report generated on {report_date}
</div>
</body></html>'''


# ── Backup & Restore ──

@app.get("/api/backup")
async def backup_project():
    """Download a ZIP containing all project data + attachments."""
    engine.save()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Main data JSON
        data_file = DATA_DIR / f"{engine.project_name}.json"
        if data_file.exists():
            zf.write(data_file, "project_data.json")

        # 2. All attachment files
        attach_dir = DATA_DIR / "attachments"
        if attach_dir.exists():
            for fpath in attach_dir.iterdir():
                if fpath.is_file():
                    zf.write(fpath, f"attachments/{fpath.name}")

        # 3. Metadata
        meta = {
            "app": "Requirements Graph Manager",
            "version": "1.0.0",
            "exported_at": datetime.now().isoformat(),
            "project_name": engine.project_name,
            "node_count": engine.graph.number_of_nodes(),
            "link_count": engine.graph.number_of_edges(),
            "baseline_count": len(engine.baselines),
        }
        zf.writestr("backup_meta.json", json.dumps(meta, ensure_ascii=False, indent=2))

    buf.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=rgm_backup_{timestamp}.zip"},
    )


@app.post("/api/restore")
async def restore_project(file: UploadFile = File(...)):
    """Restore project from a backup ZIP file."""
    content = await file.read()
    buf = io.BytesIO(content)

    try:
        with zipfile.ZipFile(buf, "r") as zf:
            names = zf.namelist()

            # Validate
            if "project_data.json" not in names:
                raise HTTPException(status_code=400, detail="Invalid backup: project_data.json not found")

            # Read and validate JSON
            raw = zf.read("project_data.json")
            data = json.loads(raw)
            if "nodes" not in data:
                raise HTTPException(status_code=400, detail="Invalid backup: no nodes in data")

            # Save project data
            data_file = DATA_DIR / f"{engine.project_name}.json"
            data_file.write_bytes(raw)

            # Restore attachments
            attach_dir = DATA_DIR / "attachments"
            attach_dir.mkdir(parents=True, exist_ok=True)
            for name in names:
                if name.startswith("attachments/") and not name.endswith("/"):
                    fname = Path(name).name
                    (attach_dir / fname).write_bytes(zf.read(name))

            # Reload engine
            engine.load()

            meta = {}
            if "backup_meta.json" in names:
                meta = json.loads(zf.read("backup_meta.json"))

            return {
                "status": "restored",
                "nodes": engine.graph.number_of_nodes(),
                "links": engine.graph.number_of_edges(),
                "baselines": len(engine.baselines),
                "backup_date": meta.get("exported_at", "unknown"),
            }
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid file: not a ZIP archive")


# ── Subsystems ──

@app.get("/api/subsystems")
async def get_subsystems():
    return engine.get_subsystems()


@app.post("/api/subsystems")
async def add_subsystem(req: SubsystemRequest):
    if engine.add_subsystem(req.name, req.color):
        engine.save()
        return {"status": "added", "name": req.name.strip().upper(), "subsystems": engine.get_subsystems()}
    raise HTTPException(status_code=400, detail=f"Subsystem '{req.name}' already exists or is invalid")


@app.put("/api/subsystems/{name}/color")
async def set_subsystem_color(name: str, req: SubsystemColorRequest):
    if engine.set_subsystem_color(name, req.color):
        engine.save()
        return {"status": "updated", "name": name, "color": req.color}
    raise HTTPException(status_code=404, detail="Subsystem not found")


@app.delete("/api/subsystems/{name}")
async def delete_subsystem(name: str):
    result = engine.delete_subsystem(name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    engine.save()
    return {"status": "deleted", "name": name, "subsystems": engine.get_subsystems()}


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

    # System-level requirements: (id, title, content, type, priority, subsystem, verification)
    reqs = [
        ("SYS-001", "시스템 전원 관리", "시스템은 전원 On/Off를 제어할 수 있어야 한다", "requirement", "critical", "SS", "test"),
        ("SYS-002", "비상 정지", "비상 상황 시 3초 이내 시스템을 정지할 수 있어야 한다", "requirement", "critical", "SS", "demonstration"),
        ("SYS-003", "사용자 인증", "시스템 접근 시 사용자 인증을 수행해야 한다", "requirement", "high", "GCS", "test"),
        ("SPC-001", "전원 모듈 설계", "전원 모듈은 12V DC 입력을 지원한다", "specification", "high", "SS", "analysis"),
        ("SPC-002", "비상 정지 회로", "하드웨어 레벨의 비상 정지 회로를 구현한다", "specification", "critical", "AVS", "inspection"),
        ("SPC-003", "인증 프로토콜", "OAuth 2.0 기반 인증을 적용한다", "specification", "high", "GCS", "analysis"),
        ("DES-001", "전원 회로도", "전원 공급 회로의 상세 설계", "design", "high", "SS", "inspection"),
        ("TST-001", "전원 On/Off 테스트", "전원 켜기/끄기 100회 반복 테스트", "test_case", "high", "SS", "test"),
        ("TST-002", "비상 정지 응답 테스트", "비상 정지 시간 측정 테스트", "test_case", "critical", "AVS", "test"),
        ("TST-003", "인증 보안 테스트", "인증 우회 시도 및 보안 검증", "test_case", "high", "GCS", "test"),
        ("RSK-001", "전원 불안정 위험", "입력 전원 불안정 시 시스템 오동작 위험", "risk", "high", "DLS", "analysis"),
    ]

    for rid, title, content, ntype, priority, subsystem, verif in reqs:
        engine.add_node(CreateNodeRequest(
            id=rid, title=title, content=content,
            node_type=ntype, priority=priority,
            verification=[verif], author="시스템", subsystem=subsystem,
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
