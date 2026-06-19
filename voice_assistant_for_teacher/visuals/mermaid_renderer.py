"""
Mermaid renderer for "process" visual_type.

Streamlit has no native Mermaid support, so we build a small self-contained
HTML snippet that loads mermaid.js from a CDN and renders the diagram
client-side. visual_router.py embeds this via st.iframe.
"""

from __future__ import annotations

from html import escape

_MERMAID_CDN = "https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.1/mermaid.min.js"


def render_mermaid_html(mermaid_code: str, theme: str = "default") -> str:
    """Build a full HTML document embedding a single Mermaid diagram."""
    safe_code = escape(mermaid_code or "flowchart LR\nA[No diagram available]")
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    body {{ margin: 0; background: #f8fafc; font-family: 'Segoe UI', Arial, sans-serif; }}
    .mermaid-wrap {{ display: flex; justify-content: center; padding: 12px; }}
  </style>
</head>
<body>
  <div class="mermaid-wrap">
    <pre class="mermaid">{safe_code}</pre>
  </div>
  <script src="{_MERMAID_CDN}"></script>
  <script>
    mermaid.initialize({{ startOnLoad: true, theme: "{theme}", securityLevel: "loose" }});
  </script>
</body>
</html>
"""
