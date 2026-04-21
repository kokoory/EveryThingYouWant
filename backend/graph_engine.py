"""Graph-based Requirements Management Engine.

Core engine that manages requirements as a directed graph using NetworkX.
Supports versioning (baselines), suspect link propagation, and tree views.
"""

import copy
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import networkx as nx

from .models import (
    BaselineInfo,
    CreateLinkRequest,
    CreateNodeRequest,
    LinkType,
    NodeStatus,
    NodeType,
    Priority,
    RequirementLink,
    RequirementNode,
    DEFAULT_SUBSYSTEMS,
    UpdateNodeRequest,
)

DATA_DIR = Path(os.environ.get("RGM_DATA_DIR", Path(__file__).parent.parent / "data"))


class GraphEngine:
    """Core engine for managing requirements as a directed graph."""

    def __init__(self, project_name: str = "default"):
        self.project_name = project_name
        self.graph = nx.DiGraph()
        self.baselines: dict[str, dict] = {}
        self.change_history: list[dict] = []
        self.subsystem_list: list[str] = list(DEFAULT_SUBSYSTEMS)
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ── Node Operations ──

    def add_node(self, req: CreateNodeRequest) -> RequirementNode:
        node_id = req.id or f"{req.node_type.value[:3].upper()}-{uuid.uuid4().hex[:6]}"
        now = datetime.now()
        node = RequirementNode(
            id=node_id,
            title=req.title,
            content=req.content,
            node_type=req.node_type,
            priority=req.priority,
            verification=req.verification if req.verification else ["test"],
            method=req.method,
            ft_no=req.ft_no,
            attachment_note=req.attachment_note,
            etc=req.etc,
            author=req.author,
            tags=req.tags,
            subsystem=req.subsystem,
            created_at=now,
            updated_at=now,
        )
        self.graph.add_node(node_id, **node.model_dump(mode="json"))
        self._record_change("add_node", node_id, None, node.model_dump(mode="json"))
        return node

    def get_node(self, node_id: str) -> Optional[dict]:
        if node_id not in self.graph.nodes:
            return None
        return dict(self.graph.nodes[node_id])

    def update_node(self, node_id: str, update: UpdateNodeRequest) -> Optional[dict]:
        if node_id not in self.graph.nodes:
            return None

        old_data = dict(self.graph.nodes[node_id])
        changes = update.model_dump(exclude_none=True)
        if not changes:
            return old_data

        for key, value in changes.items():
            if isinstance(value, (NodeStatus, Priority, NodeType)):
                self.graph.nodes[node_id][key] = value.value
            else:
                self.graph.nodes[node_id][key] = value

        now = datetime.now().isoformat()
        new_version = old_data.get("version", 1) + 1
        self.graph.nodes[node_id]["updated_at"] = now
        self.graph.nodes[node_id]["version"] = new_version

        # Version history logging
        version_history = self.graph.nodes[node_id].get("version_history", [])
        changed_fields = {}
        for key in changes:
            old_val = old_data.get(key)
            new_val = self.graph.nodes[node_id].get(key)
            if old_val != new_val:
                changed_fields[key] = {"old": old_val, "new": new_val}
        version_history.append({
            "version": new_version,
            "date": now,
            "changes": changed_fields,
        })
        self.graph.nodes[node_id]["version_history"] = version_history

        # Suspect link propagation
        self._propagate_suspect(node_id)

        self._record_change("update_node", node_id, old_data, dict(self.graph.nodes[node_id]))
        return dict(self.graph.nodes[node_id])

    def delete_node(self, node_id: str) -> bool:
        if node_id not in self.graph.nodes:
            return False
        old_data = dict(self.graph.nodes[node_id])
        self.graph.remove_node(node_id)
        self._record_change("delete_node", node_id, old_data, None)
        return True

    def get_all_nodes(self, subsystem: Optional[str] = None, node_type: Optional[str] = None) -> list[dict]:
        nodes = []
        for nid, data in self.graph.nodes(data=True):
            if subsystem and data.get("subsystem") != subsystem:
                continue
            if node_type and data.get("node_type") != node_type:
                continue
            nodes.append({"id": nid, **data})
        return nodes

    # ── Link Operations ──

    def add_link(self, req: CreateLinkRequest) -> Optional[RequirementLink]:
        if req.source_id not in self.graph.nodes or req.target_id not in self.graph.nodes:
            return None

        link = RequirementLink(
            source_id=req.source_id,
            target_id=req.target_id,
            link_type=req.link_type,
            description=req.description,
        )
        self.graph.add_edge(
            req.source_id,
            req.target_id,
            **link.model_dump(mode="json"),
        )
        self._record_change("add_link", f"{req.source_id}->{req.target_id}", None, link.model_dump(mode="json"))
        return link

    def delete_link(self, source_id: str, target_id: str) -> bool:
        if not self.graph.has_edge(source_id, target_id):
            return False
        self.graph.remove_edge(source_id, target_id)
        self._record_change("delete_link", f"{source_id}->{target_id}", None, None)
        return True

    def get_all_links(self) -> list[dict]:
        links = []
        for src, tgt, data in self.graph.edges(data=True):
            links.append({"source_id": src, "target_id": tgt, **data})
        return links

    def get_node_links(self, node_id: str) -> dict:
        if node_id not in self.graph.nodes:
            return {"incoming": [], "outgoing": []}
        incoming = [
            {"source_id": src, **data}
            for src, _, data in self.graph.in_edges(node_id, data=True)
        ]
        outgoing = [
            {"target_id": tgt, **data}
            for _, tgt, data in self.graph.out_edges(node_id, data=True)
        ]
        return {"incoming": incoming, "outgoing": outgoing}

    # ── Suspect Link Propagation ──

    def _propagate_suspect(self, changed_node_id: str):
        """When a node changes, mark all outgoing linked nodes as suspect."""
        for _, successor in self.graph.out_edges(changed_node_id):
            self.graph.edges[changed_node_id, successor]["is_suspect"] = True
            if self.graph.nodes[successor].get("status") != NodeStatus.SUSPECT.value:
                self.graph.nodes[successor]["status"] = NodeStatus.SUSPECT.value

    def resolve_suspect(self, node_id: str) -> Optional[dict]:
        """Resolve suspect status on a node and ALL its connected suspect links."""
        if node_id not in self.graph.nodes:
            return None
        self.graph.nodes[node_id]["status"] = NodeStatus.APPROVED.value
        # Clear incoming suspect links
        for pred, _ in self.graph.in_edges(node_id):
            self.graph.edges[pred, node_id]["is_suspect"] = False
        # Clear outgoing suspect links too
        for _, succ in self.graph.out_edges(node_id):
            self.graph.edges[node_id, succ]["is_suspect"] = False
        return dict(self.graph.nodes[node_id])

    def resolve_suspect_link(self, source_id: str, target_id: str) -> bool:
        """Resolve a specific suspect link."""
        if not self.graph.has_edge(source_id, target_id):
            return False
        self.graph.edges[source_id, target_id]["is_suspect"] = False
        return True

    def get_suspect_nodes(self) -> list[dict]:
        """Get all nodes currently in suspect status."""
        return [
            {"id": nid, **data}
            for nid, data in self.graph.nodes(data=True)
            if data.get("status") == NodeStatus.SUSPECT.value
        ]

    def get_suspect_links(self) -> list[dict]:
        """Get all links currently marked as suspect."""
        return [
            {"source_id": src, "target_id": tgt, **data}
            for src, tgt, data in self.graph.edges(data=True)
            if data.get("is_suspect", False)
        ]

    # ── Impact Analysis ──

    def impact_analysis(self, node_id: str, depth: int = -1) -> dict:
        """Analyze the impact of changing a node using BFS traversal."""
        if node_id not in self.graph.nodes:
            return {"affected_nodes": [], "depth_map": {}}

        visited = set()
        depth_map = {}
        queue = [(node_id, 0)]
        affected = []

        while queue:
            current, d = queue.pop(0)
            if current in visited:
                continue
            if depth != -1 and d > depth:
                continue
            visited.add(current)
            if current != node_id:
                affected.append({"id": current, "depth": d, **self.graph.nodes[current]})
                depth_map[current] = d

            for _, successor in self.graph.out_edges(current):
                if successor not in visited:
                    queue.append((successor, d + 1))

        return {"source": node_id, "affected_nodes": affected, "depth_map": depth_map}

    # ── Version Management (Baselines) ──

    def create_baseline(self, name: str, description: str = "") -> BaselineInfo:
        """Create a snapshot (baseline) of the current graph state."""
        snapshot = {
            "nodes": {nid: dict(data) for nid, data in self.graph.nodes(data=True)},
            "edges": [
                {"source": src, "target": tgt, **dict(data)}
                for src, tgt, data in self.graph.edges(data=True)
            ],
            "created_at": datetime.now().isoformat(),
            "description": description,
        }
        self.baselines[name] = snapshot
        self._save_baseline(name, snapshot)

        return BaselineInfo(
            name=name,
            description=description,
            created_at=datetime.now(),
            node_count=len(snapshot["nodes"]),
            link_count=len(snapshot["edges"]),
        )

    def list_baselines(self) -> list[BaselineInfo]:
        result = []
        for name, snap in self.baselines.items():
            result.append(BaselineInfo(
                name=name,
                description=snap.get("description", ""),
                created_at=datetime.fromisoformat(snap["created_at"]),
                node_count=len(snap["nodes"]),
                link_count=len(snap["edges"]),
            ))
        return result

    def restore_baseline(self, name: str) -> bool:
        """Restore the graph to a previous baseline state."""
        if name not in self.baselines:
            return False
        snapshot = self.baselines[name]
        self.graph.clear()
        for nid, data in snapshot["nodes"].items():
            self.graph.add_node(nid, **data)
        for edge in snapshot["edges"]:
            src = edge.pop("source")
            tgt = edge.pop("target")
            self.graph.add_edge(src, tgt, **edge)
            edge["source"] = src
            edge["target"] = tgt
        return True

    def compare_baselines(self, name1: str, name2: str) -> dict:
        """Compare two baselines and return detailed differences."""
        if name1 not in self.baselines or name2 not in self.baselines:
            return {"error": "Baseline not found"}

        snap1 = self.baselines[name1]
        snap2 = self.baselines[name2]
        nodes1 = set(snap1["nodes"].keys())
        nodes2 = set(snap2["nodes"].keys())

        added_nodes = [
            {"id": nid, **snap2["nodes"][nid]}
            for nid in sorted(nodes2 - nodes1)
        ]
        removed_nodes = [
            {"id": nid, **snap1["nodes"][nid]}
            for nid in sorted(nodes1 - nodes2)
        ]

        modified_nodes = []
        for nid in sorted(nodes1 & nodes2):
            n1 = snap1["nodes"][nid]
            n2 = snap2["nodes"][nid]
            if n1 != n2:
                changes = {}
                for key in set(list(n1.keys()) + list(n2.keys())):
                    v1 = n1.get(key)
                    v2 = n2.get(key)
                    if v1 != v2:
                        changes[key] = {"old": v1, "new": v2}
                modified_nodes.append({"id": nid, "title": n2.get("title", ""), "changes": changes})

        return {
            "baseline1": name1,
            "baseline2": name2,
            "summary": {
                "added": len(added_nodes),
                "removed": len(removed_nodes),
                "modified": len(modified_nodes),
            },
            "added_nodes": added_nodes,
            "removed_nodes": removed_nodes,
            "modified_nodes": modified_nodes,
        }

    # ── Tree / Hierarchy View ──

    def get_tree_view(self, root_id: Optional[str] = None) -> list[dict]:
        """Get a hierarchical tree view starting from root nodes or a specific root."""
        if root_id:
            if root_id not in self.graph.nodes:
                return []
            return [self._build_subtree(root_id, set())]

        roots = [n for n in self.graph.nodes if self.graph.in_degree(n) == 0]
        if not roots:
            roots = list(self.graph.nodes)[:1]

        tree = []
        for root in roots:
            # Use per-root path tracking (cycle detection), not global visited
            tree.append(self._build_subtree(root, set()))
        return tree

    def _build_subtree(self, node_id: str, path: set) -> dict:
        data = self.graph.nodes.get(node_id, {})
        base = {
            "id": node_id,
            "title": data.get("title", node_id),
            "node_type": data.get("node_type", "requirement"),
            "status": data.get("status", "draft"),
            "priority": data.get("priority", "medium"),
            "verification": data.get("verification", ["test"]),
            "subsystem": data.get("subsystem", "SS"),
        }

        # Cycle detection on this path only
        if node_id in path:
            return {**base, "title": base["title"] + " (↺ cycle)", "children": []}

        new_path = path | {node_id}
        children = []
        for _, child in self.graph.out_edges(node_id):
            children.append(self._build_subtree(child, new_path))
        return {**base, "children": children}

    # ── Subsystem Operations ──

    def get_subsystems(self) -> list[str]:
        return list(self.subsystem_list)

    def add_subsystem(self, name: str) -> bool:
        name = name.strip().upper()
        if not name or name in self.subsystem_list:
            return False
        self.subsystem_list.append(name)
        return True

    def delete_subsystem(self, name: str) -> dict:
        if name not in self.subsystem_list:
            return {"success": False, "error": "Subsystem not found"}
        # Check if any node uses this subsystem
        in_use = [nid for nid, data in self.graph.nodes(data=True) if data.get("subsystem") == name]
        if in_use:
            return {"success": False, "error": f"Subsystem '{name}' is used by {len(in_use)} node(s): {', '.join(in_use[:5])}"}
        self.subsystem_list.remove(name)
        return {"success": True}

    def get_used_subsystems(self) -> list[str]:
        used = set()
        for _, data in self.graph.nodes(data=True):
            used.add(data.get("subsystem", "SS"))
        return sorted(used)

    # ── Export ──

    def export_tree_csv(self) -> bytes:
        """Export all nodes as CSV with new format: ID, Content, Analyze, Inspection, Demonstration, Test, Method, FT_No, Attachment, ETC, Subsystem, Type, Status, Priority, Version, Updated."""
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Content",
            "Analyze", "Inspection", "Demonstration", "Test",
            "Method", "FT_No", "Attachment", "ETC",
            "Subsystem", "Type", "Status", "Priority", "Version", "Updated",
        ])

        for nid, data in self.graph.nodes(data=True):
            verif = data.get("verification", []) or []
            if isinstance(verif, str):
                verif = [verif]
            analyze_mark = "X" if "analysis" in verif else ""
            inspection_mark = "X" if "inspection" in verif else ""
            demo_mark = "X" if "demonstration" in verif else ""
            test_mark = "X" if "test" in verif else ""

            # Build content (title + content if both present and different)
            title = data.get("title", "")
            content = data.get("content", "")
            combined = title if title == content else (f"{title}\n{content}" if content else title)

            attachments = data.get("attachments", [])
            attach_summary = "; ".join(a.get("filename", "") for a in attachments) if attachments else data.get("attachment_note", "")

            writer.writerow([
                nid, combined,
                analyze_mark, inspection_mark, demo_mark, test_mark,
                data.get("method", ""),
                data.get("ft_no", ""),
                attach_summary,
                data.get("etc", ""),
                data.get("subsystem", ""),
                data.get("node_type", ""),
                data.get("status", ""),
                data.get("priority", ""),
                data.get("version", 1),
                data.get("updated_at", ""),
            ])
        # UTF-8 BOM + content for Excel compatibility
        return b'\xef\xbb\xbf' + output.getvalue().encode('utf-8')

    def import_nodes_csv(self, csv_bytes: bytes) -> dict:
        """Import nodes from CSV. Subsystem and links are NOT imported."""
        import csv as csv_mod
        import io

        if csv_bytes.startswith(b'\xef\xbb\xbf'):
            csv_bytes = csv_bytes[3:]
        text = csv_bytes.decode('utf-8-sig', errors='replace')
        reader = csv_mod.DictReader(io.StringIO(text))

        def find_col(row, *names):
            for name in names:
                for key in row:
                    if key and key.strip().lower() == name.lower():
                        return row[key] or ""
            return ""

        def is_checked(val):
            if not val:
                return False
            s = str(val).strip().lower()
            return s not in ("", "0", "no", "n", "false", "-")

        added = 0
        skipped = 0
        errors = []

        for i, row in enumerate(reader, 2):
            try:
                nid = find_col(row, "ID").strip()
                content = find_col(row, "Content").strip()
                if not nid and not content:
                    continue

                verification = []
                if is_checked(find_col(row, "Analyze", "Analysis")):
                    verification.append("analysis")
                if is_checked(find_col(row, "Inspection")):
                    verification.append("inspection")
                if is_checked(find_col(row, "Demonstration", "Demo")):
                    verification.append("demonstration")
                if is_checked(find_col(row, "Test")):
                    verification.append("test")
                if not verification:
                    verification = ["test"]

                method = find_col(row, "Method").strip()
                ft_no = find_col(row, "FT_No", "FT No", "FT-No", "FTNo").strip()
                attachment_note = find_col(row, "Attachment").strip()
                etc = find_col(row, "ETC", "Note", "Notes").strip()

                if not nid:
                    nid = f"REQ-{uuid.uuid4().hex[:6].upper()}"

                if nid in self.graph.nodes:
                    skipped += 1
                    continue

                title = content.split("\n")[0][:100] if content else nid
                now = datetime.now()
                node_data = RequirementNode(
                    id=nid,
                    title=title,
                    content=content or title,
                    node_type=NodeType.REQUIREMENT,
                    priority=Priority.MEDIUM,
                    verification=verification,
                    method=method,
                    ft_no=ft_no,
                    attachment_note=attachment_note,
                    etc=etc,
                    author="csv_import",
                    subsystem="SS",
                    created_at=now,
                    updated_at=now,
                ).model_dump(mode="json")
                self.graph.add_node(nid, **node_data)
                self._record_change("add_node", nid, None, node_data)
                added += 1
            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")

        return {
            "added": added,
            "skipped": skipped,
            "errors": errors,
            "total_rows": added + skipped + len(errors),
        }

    # ── Statistics ──

    def get_statistics(self) -> dict:
        type_counts = {}
        status_counts = {}
        for _, data in self.graph.nodes(data=True):
            nt = data.get("node_type", "unknown")
            st = data.get("status", "unknown")
            type_counts[nt] = type_counts.get(nt, 0) + 1
            status_counts[st] = status_counts.get(st, 0) + 1

        suspect_links = sum(1 for _, _, d in self.graph.edges(data=True) if d.get("is_suspect"))
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_links": self.graph.number_of_edges(),
            "type_counts": type_counts,
            "status_counts": status_counts,
            "suspect_links": suspect_links,
            "subsystems": self.get_used_subsystems(),
            "baselines": len(self.baselines),
        }

    # ── Persistence ──

    def save(self):
        filepath = DATA_DIR / f"{self.project_name}.json"
        data = {
            "project_name": self.project_name,
            "nodes": {nid: dict(d) for nid, d in self.graph.nodes(data=True)},
            "edges": [
                {"source": s, "target": t, **dict(d)}
                for s, t, d in self.graph.edges(data=True)
            ],
            "baselines": self.baselines,
            "subsystem_list": self.subsystem_list,
            "change_history": self.change_history[-100:],
        }
        filepath.write_text(json.dumps(data, default=str, ensure_ascii=False, indent=2))

    def load(self) -> bool:
        filepath = DATA_DIR / f"{self.project_name}.json"
        if not filepath.exists():
            return False
        data = json.loads(filepath.read_text())
        self.graph.clear()
        for nid, ndata in data.get("nodes", {}).items():
            self.graph.add_node(nid, **ndata)
        for edge in data.get("edges", []):
            src = edge.pop("source")
            tgt = edge.pop("target")
            self.graph.add_edge(src, tgt, **edge)
            edge["source"] = src
            edge["target"] = tgt
        self.baselines = data.get("baselines", {})
        self.subsystem_list = data.get("subsystem_list", list(DEFAULT_SUBSYSTEMS))
        self.change_history = data.get("change_history", [])
        return True

    def _save_baseline(self, name: str, snapshot: dict):
        filepath = DATA_DIR / f"{self.project_name}_baseline_{name}.json"
        filepath.write_text(json.dumps(snapshot, default=str, ensure_ascii=False, indent=2))

    def _record_change(self, action: str, target: str, old_value, new_value):
        self.change_history.append({
            "action": action,
            "target": target,
            "old_value": old_value,
            "new_value": new_value,
            "timestamp": datetime.now().isoformat(),
        })

    # ── Graph Export for Visualization ──

    def to_vis_data(self) -> dict:
        """Export graph data in a format suitable for frontend visualization."""
        nodes = []
        for nid, data in self.graph.nodes(data=True):
            color_map = {
                "requirement": "#4A90D9",
                "specification": "#7B68EE",
                "test_case": "#2ECC71",
                "design": "#F39C12",
                "risk": "#E74C3C",
            }
            status_border = {
                "suspect": "#FF0000",
                "approved": "#27AE60",
                "draft": "#95A5A6",
                "review": "#F1C40F",
            }
            nt = data.get("node_type", "requirement")
            st = data.get("status", "draft")
            nodes.append({
                "id": nid,
                "label": f"{nid}\n{data.get('title', '')}",
                "title": f"Type: {nt}\nStatus: {st}\nPriority: {data.get('priority', 'medium')}\n\n{data.get('content', '')}",
                "color": {
                    "background": color_map.get(nt, "#4A90D9"),
                    "border": status_border.get(st, "#95A5A6"),
                },
                "borderWidth": 3 if st == "suspect" else 1,
                "shape": "box",
                "font": {"color": "#FFFFFF", "size": 12},
                "node_type": nt,
                "status": st,
            })

        edges = []
        for src, tgt, data in self.graph.edges(data=True):
            is_suspect = data.get("is_suspect", False)
            edges.append({
                "from": src,
                "to": tgt,
                "label": data.get("link_type", "traces_to"),
                "arrows": "to",
                "color": {"color": "#FF0000" if is_suspect else "#848484"},
                "dashes": is_suspect,
                "width": 2 if is_suspect else 1,
                "title": f"{'⚠ SUSPECT' if is_suspect else ''} {data.get('description', '')}".strip(),
            })

        return {"nodes": nodes, "edges": edges}
