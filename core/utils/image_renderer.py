import os
import sys
import json
import logging
import math

logger = logging.getLogger("ImageRenderer")

class ImageRenderer:
    """
    🎨 [VISUAL-ARTIFACT-RENDERER]: Động cơ sinh ảnh, sơ đồ kiến trúc & UI Mockups thực tế.
    Hỗ trợ Matplotlib, Pillow, Graphviz và Native SVG Rendering với cạnh nối (edges) & UI Mockups.
    """
    @staticmethod
    def render_architecture_diagram(nodes: list, edges: list, output_filename: str = "architecture_diagram.svg") -> dict:
        """Tạo sơ đồ kiến trúc hệ thống trực quan kèm các mũi tên liên kết (Edges/Arrows) chuẩn SVG."""
        try:
            target_dir = os.getenv("STORAGE_DIR", "D:\\Docker\\JKAI\\brain\\artifacts")
            os.makedirs(target_dir, exist_ok=True)
            if not output_filename.endswith(".svg"):
                output_filename = output_filename.rsplit(".", 1)[0] + ".svg"
            full_path = os.path.join(target_dir, output_filename)

            # Tính vị trí tọa độ các Nút (Node Positions)
            node_positions = {}
            cols = min(4, max(2, len(nodes)))
            for idx, node in enumerate(nodes):
                col = idx % cols
                row = idx // cols
                cx = 150 + col * 220
                cy = 100 + row * 140
                node_positions[node] = (cx, cy)

            max_x = max([p[0] for p in node_positions.values()]) + 150 if node_positions else 800
            max_y = max([p[1] for p in node_positions.values()]) + 120 if node_positions else 400

            svg_lines = [
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{max_x}" height="{max_y}">',
                '  <defs>',
                '    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">',
                '      <polygon points="0 0, 10 3.5, 0 7" fill="#38BDF8"/>',
                '    </marker>',
                '  </defs>',
                '  <rect width="100%" height="100%" fill="#0F172A"/>',
                '  <text x="50%" y="35" font-family="Arial" font-size="20" fill="#38BDF8" text-anchor="middle" font-weight="bold">🏛️ JKAI Sovereign OS - Architecture Diagram</text>'
            ]

            # 1. Vẽ các Cạnh Nối (Edges / Lines with Arrowheads)
            for u, v in edges:
                if u in node_positions and v in node_positions:
                    x1, y1 = node_positions[u]
                    x2, y2 = node_positions[v]
                    svg_lines.append(f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#38BDF8" stroke-width="2" stroke-dasharray="4" marker-end="url(#arrowhead)"/>')

            # 2. Vẽ các Nút (Nodes / Rectangles)
            for node, (cx, cy) in node_positions.items():
                svg_lines.append(f'  <rect x="{cx-75}" y="{cy-25}" width="150" height="50" rx="8" fill="#1E293B" stroke="#38BDF8" stroke-width="2"/>')
                svg_lines.append(f'  <text x="{cx}" y="{cy+5}" font-family="Arial" font-size="13" fill="#F8FAFC" text-anchor="middle" font-weight="bold">{node}</text>')

            svg_lines.append('</svg>')
            svg_content = "\n".join(svg_lines)

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(svg_content)

            logger.info(f"🎨 [IMAGE-RENDERER-SUCCESS]: Đã sinh sơ đồ kiến trúc SVG kèm Edges tại {full_path}")
            return {"status": "success", "file_path": full_path, "message": f"Sơ đồ SVG đã tạo thành công tại {full_path}"}
        except Exception as e:
            logger.error(f"[IMAGE-RENDERER-ERR] {e}")
            return {"status": "error", "error": str(e)}

    @staticmethod
    def render_ui_mockup(title: str, components: list, output_filename: str = "ui_mockup.svg") -> dict:
        """Tạo bản phác thảo giao diện người dùng (UI Mockup) chuẩn SVG."""
        try:
            target_dir = os.getenv("STORAGE_DIR", "D:\\Docker\\JKAI\\brain\\artifacts")
            os.makedirs(target_dir, exist_ok=True)
            full_path = os.path.join(target_dir, output_filename)

            svg_lines = [
                '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600">',
                '  <rect width="100%" height="100%" fill="#1E293B"/>',
                '  <!-- Header Bar -->',
                '  <rect x="0" y="0" width="900" height="60" fill="#0F172A"/>',
                f'  <text x="30" y="38" font-family="Arial" font-size="18" fill="#38BDF8" font-weight="bold">{title}</text>',
                '  <!-- Sidebar -->',
                '  <rect x="0" y="60" width="200" height="540" fill="#0F172A" opacity="0.7"/>',
                '  <text x="30" y="100" font-family="Arial" font-size="14" fill="#94A3B8">📊 Dashboard</text>',
                '  <text x="30" y="140" font-family="Arial" font-size="14" fill="#94A3B8">⚙️ Settings</text>',
                '  <text x="30" y="180" font-family="Arial" font-size="14" fill="#94A3B8">🚀 Missions</text>',
                '  <!-- Main Canvas -->'
            ]

            # Render UI Components
            start_y = 90
            for idx, comp in enumerate(components):
                comp_type = comp.get("type", "card")
                label = comp.get("label", f"Component {idx+1}")
                if comp_type == "button":
                    svg_lines.append(f'  <rect x="230" y="{start_y}" width="140" height="40" rx="6" fill="#0284C7"/>')
                    svg_lines.append(f'  <text x="300" y="{start_y+25}" font-family="Arial" font-size="14" fill="#FFFFFF" text-anchor="middle" font-weight="bold">{label}</text>')
                    start_y += 60
                elif comp_type == "input":
                    svg_lines.append(f'  <rect x="230" y="{start_y}" width="300" height="40" rx="6" fill="#334155" stroke="#475569"/>')
                    svg_lines.append(f'  <text x="245" y="{start_y+25}" font-family="Arial" font-size="13" fill="#94A3B8">{label}...</text>')
                    start_y += 60
                else: # Card
                    svg_lines.append(f'  <rect x="230" y="{start_y}" width="640" height="100" rx="8" fill="#334155"/>')
                    svg_lines.append(f'  <text x="250" y="{start_y+35}" font-family="Arial" font-size="16" fill="#F8FAFC" font-weight="bold">{label}</text>')
                    svg_lines.append(f'  <text x="250" y="{start_y+65}" font-family="Arial" font-size="13" fill="#CBD5E1">{comp.get("description", "UI Component Panel")}</text>')
                    start_y += 120

            svg_lines.append('</svg>')
            with open(full_path, "w", encoding="utf-8") as f:
                f.write("\n".join(svg_lines))

            return {"status": "success", "file_path": full_path, "message": f"UI Mockup đã tạo tại {full_path}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

image_renderer = ImageRenderer()
