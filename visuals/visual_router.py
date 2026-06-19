"""
Visual Router.

    Process          -> Mermaid
    Science Diagram   -> Dynamic SVG
    Math              -> Plotly
    Comparison        -> HTML Cards
    Timeline          -> Timeline Component

This is the only module that actually calls Streamlit display functions for
diagrams — every renderer module above it (svg_renderer, mermaid_renderer,
plotly_renderer, cards_renderer) is a pure function that just builds content,
which keeps them independently testable.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from utils.logger import get_logger
from visuals import cards_renderer, mermaid_renderer, plotly_renderer, svg_renderer

logger = get_logger(__name__)

_DeltaGeneratorOrNone = Any


def wrap_svg_document(svg_markup: str) -> str:
    """Wrap a raw <svg>...</svg> fragment in a minimal HTML document.

    The SVG itself is styled width:100%;height:100% so it scales to fit
    whatever box it's given (via preserveAspectRatio, no distortion or
    clipping) — but percentage heights only resolve correctly if html/body
    *also* have an explicit height in the chain, which a bare srcdoc
    fragment doesn't get by default. Without this wrapper the SVG inflates
    to track the iframe's (often much wider) width instead of its fixed
    pixel height, and gets clipped.
    """
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<style>html,body{margin:0;height:100%;overflow:hidden;}</style>"
        f"</head><body>{svg_markup}</body></html>"
    )


def _show_html(html: str, height: int, scrolling: bool, container: _DeltaGeneratorOrNone) -> None:
    # st.iframe replaced the deprecated st.components.v1.html — it embeds an
    # HTML string in an iframe the same way, just without a `scrolling` flag
    # (browsers show scrollbars on overflow by default regardless).
    del scrolling
    if container is not None:
        with container:
            st.iframe(html, height=height)
    else:
        st.iframe(html, height=height)


def render(visual_type: str, diagram: dict[str, Any] | None, container: _DeltaGeneratorOrNone = None) -> bool:
    """Render `diagram` according to `visual_type` inside `container`
    (defaults to the main app body if no container is given).

    Returns True if a visual was rendered, False if there was nothing to
    show (visual_type == "none" / missing diagram) or rendering failed.
    """
    if not diagram or visual_type in (None, "", "none"):
        return False

    try:
        if visual_type == "process":
            html = mermaid_renderer.render_mermaid_html(diagram.get("mermaid", ""))
            _show_html(html, height=420, scrolling=True, container=container)
            return True

        if visual_type == "science_diagram":
            svg = svg_renderer.compose_diagram(diagram)
            _show_html(wrap_svg_document(svg), height=460, scrolling=False, container=container)
            return True

        if visual_type == "math":
            fig = plotly_renderer.build_figure(diagram)
            if container is not None:
                with container:
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.plotly_chart(fig, use_container_width=True)
            return True

        if visual_type == "comparison":
            html = cards_renderer.render_comparison(diagram)
            _show_html(html, height=340, scrolling=True, container=container)
            return True

        if visual_type == "timeline":
            html = cards_renderer.render_timeline(diagram)
            _show_html(html, height=280, scrolling=True, container=container)
            return True

        logger.warning("Unknown visual_type '%s' received by visual router.", visual_type)
        return False

    except Exception as exc:  # noqa: BLE001 — a broken diagram must never crash the lesson
        logger.error("Rendering failed for visual_type=%s: %s", visual_type, exc)
        target = container if container is not None else st
        target.warning("Couldn't render the visual for this topic — showing the text explanation only.")
        return False


def render_keypoints_fallback(key_points: list[str], container: _DeltaGeneratorOrNone = None) -> None:
    """Used when there's no visual to show at all — keep the smart board
    from looking empty by surfacing the key takeaways as a simple list."""
    target = container if container is not None else st
    if not key_points:
        return
    with target:
        st.markdown("\n".join(f"- {point}" for point in key_points))
