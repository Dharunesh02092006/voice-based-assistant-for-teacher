"""
Bonus feature: "Generate Illustration" button.

The declared tech stack has no dedicated image-generation API (only SVG
generation, Mermaid, Plotly, and HTML/CSS cards) — so the bonus illustration
is itself a freeform, artistic SVG, produced by prompting Gemini 2.5 Flash
to emit SVG markup directly as text. This is a deliberately different style
of prompt than prompts/visual.txt: instead of a precise labeled diagram, it
asks for a colorful, decorative, classroom-poster-style scene.

This illustration is always shown *beside*, never instead of, the primary
educational visual (enforced in app.py's layout, not here).
"""

from __future__ import annotations

import re

from llms.gemini_llm import GeminiLLM
from utils.logger import get_logger

logger = get_logger(__name__)

_SVG_TAG_RE = re.compile(r"<svg[\s\S]*?</svg>", re.IGNORECASE)
_SVG_OPEN_TAG_RE = re.compile(r"<svg\b[^>]*>", re.IGNORECASE)


def _normalize_svg_sizing(svg_markup: str) -> str:
    """Force consistent width:100%;height:100% sizing on the root <svg>,
    overriding whatever (or however little) sizing the model included.
    This is more robust than a prompt instruction alone, since a freeform
    LLM response can't be guaranteed to follow it — and incorrect sizing
    here causes real clipping once embedded in a fixed-height iframe."""
    match = _SVG_OPEN_TAG_RE.search(svg_markup)
    if not match:
        return svg_markup
    open_tag = match.group(0)
    cleaned = re.sub(r'\s(style|width|height|preserveAspectRatio)="[^"]*"', "", open_tag, flags=re.IGNORECASE)
    cleaned = cleaned[:-1] + ' preserveAspectRatio="xMidYMid meet" style="width:100%;height:100%;">'
    return svg_markup[: match.start()] + cleaned + svg_markup[match.end() :]


_ILLUSTRATION_PROMPT = """You are a children's educational illustrator. Create ONE colorful, friendly, \
classroom-poster-style SVG illustration about: "{topic}".

Rules:
- Respond with ONLY a single valid <svg>...</svg> element — no markdown fences, no explanation, nothing else.
- Use viewBox="0 0 400 300".
- Use bright, cheerful, flat-design colors suitable for Class 6-10 students.
- Compose the scene from basic shapes only: circle, rect, ellipse, path, polygon, text.
- Do not include <script>, <foreignObject>, external links, or external image references.
"""


def _fallback_svg(topic: str) -> str:
    """A simple, always-renderable placeholder used when Gemini is
    unavailable or returns something unusable."""
    safe_topic = (topic or "Topic")[:40].replace("&", "and").replace("<", "").replace(">", "")
    return f"""<svg viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet" style="width:100%;height:100%;background:#fef9c3;border-radius:16px;">
<circle cx="200" cy="115" r="55" fill="#fbbf24" stroke="#92400e" stroke-width="3"/>
<rect x="178" y="168" width="44" height="50" rx="8" fill="#fde68a" stroke="#92400e" stroke-width="3"/>
<text x="200" y="260" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="600" fill="#78350f">{safe_topic}</text>
</svg>"""


def _extract_svg(raw_text: str) -> str | None:
    match = _SVG_TAG_RE.search(raw_text or "")
    return match.group(0) if match else None


def generate_illustration(topic: str, gemini_llm: GeminiLLM | None = None) -> str:
    """Return SVG markup illustrating `topic`. Always returns something
    renderable — falls back to a simple procedural SVG if Gemini is
    unconfigured, errors out, or returns invalid markup."""
    llm = gemini_llm or GeminiLLM()

    if not llm.is_configured:
        logger.info("Gemini not configured; using procedural fallback illustration.")
        return _fallback_svg(topic)

    try:
        raw_text = llm.generate_raw(_ILLUSTRATION_PROMPT.format(topic=topic), temperature=0.8)
        svg = _extract_svg(raw_text)
        if svg:
            return _normalize_svg_sizing(svg)
        logger.warning("Gemini illustration response had no valid <svg>; using fallback.")
        return _fallback_svg(topic)
    except Exception as exc:  # noqa: BLE001 — illustration is a bonus, never block the lesson
        logger.error("Illustration generation failed: %s", exc)
        return _fallback_svg(topic)
