"""
Dynamic Visual Generation Engine.

    Educational JSON -> Diagram Schema -> SVG Renderer -> Dynamic SVG

No prebuilt per-topic SVG templates exist anywhere in this codebase. Instead
a small set of reusable primitives (draw_circle, draw_rect, draw_arrow,
draw_text, draw_cloud, draw_plant, draw_planet, draw_organ) are composed at
runtime based on whatever "elements" list an LLM produced for the current
topic — so a brand-new topic the developer never anticipated still renders
correctly as long as it fits the schema in prompts/visual.txt.
"""

from __future__ import annotations

import math
from collections import Counter
from html import escape
from typing import Any

CANVAS_W = 760
CANVAS_H = 430
_DEFAULT_FILL = "#6366f1"

_PALETTE = {
    "sun": "#f59e0b",
    "plant": "#22c55e",
    "cloud": "#7dd3fc",
    "planet": "#8b5cf6",
    "organ": "#fb7185",
    "circle": "#6366f1",
    "rect": "#0ea5e9",
}


def _esc(text: Any) -> str:
    return escape(str(text), quote=True)


def _wrap_label(label: str, max_chars: int = 14, max_lines: int = 2) -> list[str]:
    """Greedy word-wrap a label into at most `max_lines` short lines so it
    stays legible inside a fixed-size shape on a projector."""
    words = str(label).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
        if len(lines) == max_lines - 1:
            break
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    return lines or [""]


def _multiline_text(cx: float, cy: float, label: str, size: int = 15, color: str = "#111827") -> str:
    if not label:
        return ""
    lines = _wrap_label(label)
    line_height = size + 4
    start_y = cy - (len(lines) - 1) * line_height / 2
    spans = "".join(
        f'<tspan x="{cx:.1f}" y="{(start_y + i * line_height):.1f}">{_esc(line)}</tspan>' for i, line in enumerate(lines)
    )
    return (
        f'<text text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="{size}" font-weight="600" fill="{color}">{spans}</text>'
    )


# ---------------------------------------------------------------------------
# Reusable SVG primitives — each returns a standalone SVG fragment string.
# ---------------------------------------------------------------------------


def draw_circle(cx: float, cy: float, r: float, fill: str = _DEFAULT_FILL, label: str = "", label_side: str = "below") -> str:
    circle = f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" stroke="#1f2937" stroke-width="2"/>'
    label_y = cy - r - 14 if label_side == "above" else cy + r + 22
    caption = _multiline_text(cx, label_y, label) if label else ""
    return circle + caption


def draw_rect(x: float, y: float, w: float, h: float, fill: str = _DEFAULT_FILL, label: str = "", rx: float = 14) -> str:
    rect = (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx:.1f}" '
        f'fill="{fill}" stroke="#1f2937" stroke-width="2"/>'
    )
    caption = _multiline_text(x + w / 2, y + h / 2 + 5, label, color="#ffffff") if label else ""
    return rect + caption


def draw_text(x: float, y: float, text: str, size: int = 17, color: str = "#111827") -> str:
    return _multiline_text(x, y, text, size=size, color=color)


def draw_cloud(cx: float, cy: float, w: float = 110, h: float = 60, fill: str = "#7dd3fc", label: str = "", label_side: str = "below") -> str:
    r = h / 2.1
    puffs = [
        (cx - w * 0.28, cy + h * 0.08, r * 0.85),
        (cx + w * 0.0, cy - h * 0.18, r * 1.05),
        (cx + w * 0.30, cy + h * 0.05, r * 0.9),
        (cx - w * 0.05, cy + h * 0.18, r * 0.95),
    ]
    circles = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.1f}" fill="{fill}" stroke="#0ea5e9" stroke-width="1.5"/>' for x, y, rr in puffs)
    base = f'<rect x="{cx - w/2:.1f}" y="{cy - h*0.05:.1f}" width="{w:.1f}" height="{h*0.45:.1f}" rx="{h*0.2:.1f}" fill="{fill}" stroke="#0ea5e9" stroke-width="1.5"/>'
    label_y = cy - h * 0.85 if label_side == "above" else cy + h * 0.85
    caption = _multiline_text(cx, label_y, label) if label else ""
    return base + circles + caption


def draw_plant(cx: float, cy: float, height: float = 95, label: str = "", label_side: str = "below") -> str:
    pot_w, pot_h = height * 0.55, height * 0.32
    pot_top = cy + height * 0.18
    pot = (
        f'<polygon points="{cx - pot_w/2:.1f},{pot_top:.1f} {cx + pot_w/2:.1f},{pot_top:.1f} '
        f'{cx + pot_w*0.36:.1f},{pot_top + pot_h:.1f} {cx - pot_w*0.36:.1f},{pot_top + pot_h:.1f}" '
        f'fill="#b45309" stroke="#1f2937" stroke-width="2"/>'
    )
    stem_top = cy - height * 0.42
    stem = f'<rect x="{cx - 3:.1f}" y="{stem_top:.1f}" width="6" height="{pot_top - stem_top:.1f}" fill="#15803d"/>'
    leaves = []
    for dx, dy, rx_, ry_, rot in (
        (-22, -6, 24, 13, -35),
        (22, -6, 24, 13, 35),
        (0, -28, 22, 13, 0),
    ):
        lx, ly = cx + dx, stem_top + dy
        leaves.append(
            f'<ellipse cx="{lx:.1f}" cy="{ly:.1f}" rx="{rx_}" ry="{ry_}" '
            f'fill="#22c55e" stroke="#15803d" stroke-width="1.5" transform="rotate({rot} {lx:.1f} {ly:.1f})"/>'
        )
    label_y = stem_top - 55 if label_side == "above" else pot_top + pot_h + 22
    caption = _multiline_text(cx, label_y, label) if label else ""
    return pot + stem + "".join(leaves) + caption


def draw_planet(cx: float, cy: float, r: float = 34, fill: str = "#8b5cf6", label: str = "", ringed: bool = True, label_side: str = "below") -> str:
    ring = (
        f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{r * 1.7:.1f}" ry="{r * 0.45:.1f}" '
        f'fill="none" stroke="#1f2937" stroke-width="2" opacity="0.6"/>'
        if ringed
        else ""
    )
    body = f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" stroke="#1f2937" stroke-width="2"/>'
    highlight = f'<circle cx="{cx - r*0.3:.1f}" cy="{cy - r*0.3:.1f}" r="{r*0.35:.1f}" fill="#ffffff" opacity="0.25"/>'
    label_y = cy - r - 16 if label_side == "above" else cy + r + 24
    caption = _multiline_text(cx, label_y, label) if label else ""
    return ring + body + highlight + caption


def draw_organ(cx: float, cy: float, w: float = 90, h: float = 65, fill: str = "#fb7185", label: str = "", label_side: str = "below") -> str:
    # Stylized rounded-organic blob built from a closed bezier path.
    path = (
        f"M {cx - w/2:.1f} {cy} "
        f"C {cx - w/2:.1f} {cy - h/2:.1f}, {cx - w/4:.1f} {cy - h/2:.1f}, {cx:.1f} {cy - h/2.3:.1f} "
        f"C {cx + w/4:.1f} {cy - h/2:.1f}, {cx + w/2:.1f} {cy - h/2:.1f}, {cx + w/2:.1f} {cy:.1f} "
        f"C {cx + w/2:.1f} {cy + h/2:.1f}, {cx + w/4:.1f} {cy + h/2.1:.1f}, {cx:.1f} {cy + h/2.4:.1f} "
        f"C {cx - w/4:.1f} {cy + h/2.1:.1f}, {cx - w/2:.1f} {cy + h/2:.1f}, {cx - w/2:.1f} {cy:.1f} Z"
    )
    blob = f'<path d="{path}" fill="{fill}" stroke="#1f2937" stroke-width="2"/>'
    label_y = cy - h / 2 - 14 if label_side == "above" else cy + h / 2 + 24
    caption = _multiline_text(cx, label_y, label) if label else ""
    return blob + caption


def draw_arrow(x1: float, y1: float, x2: float, y2: float, label: str = "", color: str = "#374151", curve: float = 0) -> str:
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1.0
    perp_x, perp_y = -dy / length, dx / length  # unit vector perpendicular to the line

    if curve:
        ox, oy = perp_x * curve, perp_y * curve
        cxp, cyp = mx + ox, my + oy
        path = f'<path d="M {x1:.1f} {y1:.1f} Q {cxp:.1f} {cyp:.1f} {x2:.1f} {y2:.1f}" fill="none" stroke="{color}" stroke-width="2.5" marker-end="url(#arrowhead)"/>'
        label_anchor_x, label_anchor_y = cxp, cyp
    else:
        path = f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="2.5" marker-end="url(#arrowhead)"/>'
        label_anchor_x, label_anchor_y = mx, my

    # Push the label off to one side of the line (rather than centered on
    # top of it) so its opaque background never hides the line/arrowhead —
    # especially important once endpoints are trimmed short between two
    # nearby shapes.
    label_x = label_anchor_x + perp_x * 17
    label_y = label_anchor_y + perp_y * 17

    caption = ""
    if label:
        text_w = min(150, max(36, len(label) * 7))
        caption = (
            f'<rect x="{label_x - text_w/2:.1f}" y="{label_y - 12:.1f}" width="{text_w:.1f}" height="20" '
            f'rx="6" fill="#ffffff" opacity="0.9"/>'
            + _multiline_text(label_x, label_y + 4, label, size=12, color="#374151")
        )
    return path + caption



# ---------------------------------------------------------------------------
# Layout + composition
# ---------------------------------------------------------------------------

_PRIMITIVE_SIZES = {
    "sun": 38,
    "circle": 34,
    "planet": 32,
    "plant": 90,  # height
    "cloud": 110,  # width
    "organ": 90,  # width
    "rect": 100,  # width
}

# Approximate "keep-out" radius per node type, used to trim arrow endpoints
# back to each shape's visual edge rather than its center — otherwise an
# arrow (and its label) ends up drawn straight through the shape's glyph.
# These are deliberately generous circular approximations of irregular
# shapes (plant, cloud, organ); pixel-perfect clipping isn't worth the
# complexity for an MVP diagram engine.
_EFFECTIVE_RADIUS = {
    "sun": 62,
    "circle": 38,
    "planet": 58,
    "plant": 60,
    "cloud": 52,
    "organ": 46,
    "rect": 52,
    "text": 16,
}


def _trim_point(x: float, y: float, towards_x: float, towards_y: float, radius: float) -> tuple[float, float]:
    """Move (x, y) toward (towards_x, towards_y) by `radius` pixels — used to
    pull an arrow's endpoint back to a shape's edge instead of its center."""
    dx, dy = towards_x - x, towards_y - y
    distance = math.hypot(dx, dy) or 1.0
    ratio = min(radius / distance, 0.45)  # never eat more than ~45% of a short segment
    return x + dx * ratio, y + dy * ratio


def _compute_layout(
    nodes: list[dict[str, Any]], arrows: list[dict[str, Any]]
) -> tuple[dict[str, tuple[float, float]], str | None]:
    cx, cy = CANVAS_W / 2, CANVAS_H / 2 + 5
    if not nodes:
        return {}, None
    if len(nodes) == 1:
        return {nodes[0]["id"]: (cx, cy)}, None

    indegree = Counter(a.get("to") for a in arrows if a.get("to"))
    total_degree: Counter[str] = Counter()
    for a in arrows:
        if a.get("from"):
            total_degree[a["from"]] += 1
        if a.get("to"):
            total_degree[a["to"]] += 1

    node_ids = [n["id"] for n in nodes]
    # A node "qualifies" as a hub either because 2+ arrows converge into it
    # (the classic "N inputs -> one subject" pattern, e.g. sun + water ->
    # plant) or because it simply touches 3+ arrows in any direction (e.g.
    # a heart with both incoming and outgoing connections to several
    # organs). Plain sequential chains (A -> B -> C) trigger neither.
    hub_id: str | None = None
    hub_score = 0
    for nid in node_ids:
        qualifies = indegree.get(nid, 0) >= 2 or total_degree.get(nid, 0) >= 3
        score = total_degree.get(nid, 0)
        if qualifies and score > hub_score:
            hub_id, hub_score = nid, score

    positions: dict[str, tuple[float, float]] = {}

    if hub_id:
        # Radial hub-and-spoke layout: good for "N inputs -> one subject".
        positions[hub_id] = (cx, cy)
        others = [nid for nid in node_ids if nid != hub_id]
        radius = 190
        n = len(others)
        if n == 2:
            # The two-spoke case (e.g. sun + water -> plant) is a special
            # case: evenly spacing 2 points 180 degrees apart starting from
            # "top" puts both spokes directly above/below the hub on the
            # exact same x-coordinate, which visually collides with a wide
            # landscape canvas. Spread them left/right instead.
            angles = [math.pi, 0.0]
        else:
            angles = [(2 * math.pi * i / n) - (math.pi / 2) for i in range(n)]
        for nid, angle in zip(others, angles):
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle) * 0.72
            positions[nid] = (x, y)
    else:
        # Sequential row layout: good for simple chains A -> B -> C.
        margin = 95
        usable = CANVAS_W - 2 * margin
        n = len(node_ids)
        for i, nid in enumerate(node_ids):
            x = margin + (usable * i / (n - 1) if n > 1 else usable / 2)
            y = cy if i % 2 == 0 else cy - 55
            positions[nid] = (x, y)

    return positions, hub_id


def compose_diagram(diagram: dict[str, Any]) -> str:
    """Turn a validated diagram JSON object into a complete <svg> string."""
    elements = diagram.get("elements") or []
    nodes = [e for e in elements if e.get("type") != "arrow" and e.get("id")]
    arrows = [e for e in elements if e.get("type") == "arrow"]

    positions, hub_id = _compute_layout(nodes, arrows)
    node_types = {n["id"]: str(n.get("type", "circle")).lower() for n in nodes}
    hub_y = positions[hub_id][1] if hub_id else None
    body_parts: list[str] = []

    for node in nodes:
        node_id = node["id"]
        if node_id not in positions:
            continue
        x, y = positions[node_id]
        node_type = str(node.get("type", "circle")).lower()
        label = node.get("label", "") or ""
        fill = _PALETTE.get(node_type, _DEFAULT_FILL)

        # A spoke sitting above the hub has its connecting arrow approaching
        # from below, which collides with the default below-shape label —
        # flip the label above the shape in that one situation.
        label_side = "above" if (hub_id and node_id != hub_id and hub_y is not None and y < hub_y - 20) else "below"

        if node_type == "sun":
            rays = "".join(
                f'<line x1="{x + 46*math.cos(a):.1f}" y1="{y + 46*math.sin(a):.1f}" '
                f'x2="{x + 60*math.cos(a):.1f}" y2="{y + 60*math.sin(a):.1f}" '
                f'stroke="{fill}" stroke-width="4" stroke-linecap="round"/>'
                for a in (math.pi * i / 4 for i in range(8))
            )
            body_parts.append(rays + draw_circle(x, y, _PRIMITIVE_SIZES["sun"], fill, label, label_side))
        elif node_type == "plant":
            body_parts.append(draw_plant(x, y, _PRIMITIVE_SIZES["plant"], label, label_side))
        elif node_type == "cloud":
            body_parts.append(
                draw_cloud(x, y, _PRIMITIVE_SIZES["cloud"], _PRIMITIVE_SIZES["cloud"] * 0.55, fill, label, label_side)
            )
        elif node_type == "planet":
            body_parts.append(draw_planet(x, y, _PRIMITIVE_SIZES["planet"], fill, label, label_side=label_side))
        elif node_type == "organ":
            body_parts.append(
                draw_organ(x, y, _PRIMITIVE_SIZES["organ"], _PRIMITIVE_SIZES["organ"] * 0.72, fill, label, label_side)
            )
        elif node_type == "rect":
            w = _PRIMITIVE_SIZES["rect"]
            body_parts.append(draw_rect(x - w / 2, y - 32, w, 64, fill, label))
        elif node_type == "text":
            body_parts.append(draw_text(x, y, label))
        else:  # generic fallback for any type the model invents
            body_parts.append(draw_circle(x, y, _PRIMITIVE_SIZES["circle"], fill, label, label_side))

    # Arrows drawn after nodes so they layer on top; fan out curve when
    # several arrows share an endpoint so labels don't collide.
    arrow_groups: dict[tuple[str, str], int] = {}
    for arrow in arrows:
        from_id, to_id = arrow.get("from"), arrow.get("to")
        if from_id not in positions or to_id not in positions:
            continue
        key = (from_id, to_id)
        idx = arrow_groups.get(key, 0)
        arrow_groups[key] = idx + 1
        x1, y1 = positions[from_id]
        x2, y2 = positions[to_id]

        from_radius = _EFFECTIVE_RADIUS.get(node_types.get(from_id, "circle"), 36)
        to_radius = _EFFECTIVE_RADIUS.get(node_types.get(to_id, "circle"), 36)
        start_x, start_y = _trim_point(x1, y1, x2, y2, from_radius)
        end_x, end_y = _trim_point(x2, y2, x1, y1, to_radius)

        curve = 0 if idx == 0 else (idx * 30 if idx % 2 else -idx * 30)
        body_parts.append(draw_arrow(start_x, start_y, end_x, end_y, label=arrow.get("label", ""), curve=curve))

    defs = (
        '<defs><marker id="arrowhead" markerWidth="10" markerHeight="10" refX="8" refY="5" '
        'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="#374151"/></marker></defs>'
    )

    return (
        f'<svg viewBox="0 0 {CANVAS_W} {CANVAS_H}" xmlns="http://www.w3.org/2000/svg" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;height:100%;background:#f8fafc;border-radius:16px;">'
        f"{defs}{''.join(body_parts)}</svg>"
    )
