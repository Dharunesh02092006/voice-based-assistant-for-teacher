"""
HTML/CSS renderers for "comparison" and "timeline" visual_types.

Per the required project structure there is no separate timeline renderer
file, so both card-style components live here together.
"""

from __future__ import annotations

from html import escape
from typing import Any


def _esc(text: Any) -> str:
    return escape(str(text), quote=True)


_CARD_STYLE = """
<style>
  .vta-cards-wrap { font-family: 'Segoe UI', Arial, sans-serif; padding: 4px; }
  .vta-cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 18px;
  }
  .vta-card {
    background: #ffffff;
    border: 2px solid #e2e8f0;
    border-radius: 16px;
    padding: 18px 20px;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
  }
  .vta-card h3 {
    margin: 0 0 12px 0;
    font-size: 19px;
    color: #312e81;
  }
  .vta-card ul { margin: 0; padding-left: 20px; }
  .vta-card li { margin-bottom: 8px; font-size: 15px; color: #1f2937; line-height: 1.4; }
</style>
"""

_TIMELINE_STYLE = """
<style>
  .vta-timeline-wrap { font-family: 'Segoe UI', Arial, sans-serif; padding: 8px 4px; overflow-x: auto; }
  .vta-timeline { display: flex; align-items: flex-start; min-width: max-content; padding: 10px 0; }
  .vta-timeline-event { display: flex; flex-direction: column; align-items: center; width: 200px; position: relative; }
  .vta-timeline-event:not(:first-child)::before {
    content: ""; position: absolute; top: 10px; left: -100px; width: 100px; height: 3px; background: #c7d2fe;
  }
  .vta-dot { width: 18px; height: 18px; border-radius: 50%; background: #6366f1; border: 3px solid #ffffff; box-shadow: 0 0 0 2px #6366f1; margin-bottom: 10px; }
  .vta-date { font-weight: 700; color: #4338ca; font-size: 14px; margin-bottom: 4px; }
  .vta-event-title { font-weight: 600; color: #1f2937; font-size: 15px; text-align: center; margin-bottom: 4px; }
  .vta-event-desc { font-size: 13px; color: #4b5563; text-align: center; line-height: 1.35; }
</style>
"""


def render_comparison(diagram: dict[str, Any]) -> str:
    items = diagram.get("items") or []
    if not items:
        return _CARD_STYLE + '<div class="vta-cards-wrap"><p>No comparison data available.</p></div>'

    cards = []
    for item in items:
        title = _esc(item.get("title", "Item"))
        points = item.get("points") or []
        li_html = "".join(f"<li>{_esc(p)}</li>" for p in points)
        cards.append(f'<div class="vta-card"><h3>{title}</h3><ul>{li_html}</ul></div>')

    return f'{_CARD_STYLE}<div class="vta-cards-wrap"><div class="vta-cards-grid">{"".join(cards)}</div></div>'


def render_timeline(diagram: dict[str, Any]) -> str:
    events = diagram.get("events") or []
    if not events:
        return _TIMELINE_STYLE + '<div class="vta-timeline-wrap"><p>No timeline data available.</p></div>'

    nodes = []
    for event in events:
        date = _esc(event.get("date", ""))
        title = _esc(event.get("title", ""))
        desc = _esc(event.get("description", ""))
        nodes.append(
            f'<div class="vta-timeline-event"><div class="vta-dot"></div>'
            f'<div class="vta-date">{date}</div>'
            f'<div class="vta-event-title">{title}</div>'
            f'<div class="vta-event-desc">{desc}</div></div>'
        )

    return f'{_TIMELINE_STYLE}<div class="vta-timeline-wrap"><div class="vta-timeline">{"".join(nodes)}</div></div>'
