"""
Plotly renderer for "math" visual_type.

Interprets the LLM-produced diagram JSON (chart_type/x/y/title/labels) into
a Plotly Figure. Falls back to a simple placeholder figure if the data is
malformed, so a bad model response never crashes the smart board UI.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

_ACCENT = "#6366f1"


def _placeholder_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        showarrow=False,
        font={"size": 16, "color": "#6b7280"},
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
    )
    fig.update_layout(
        xaxis={"visible": False},
        yaxis={"visible": False},
        height=380,
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
    )
    return fig


def build_figure(diagram: dict[str, Any]) -> go.Figure:
    try:
        chart_type = str(diagram.get("chart_type", "line")).lower()
        title = diagram.get("title", "")
        x = diagram.get("x") or []
        y = diagram.get("y") or []
        x_label = diagram.get("x_label", "")
        y_label = diagram.get("y_label", "")

        if not x or not y or len(x) != len(y):
            return _placeholder_figure("No chart data was generated for this topic.")

        fig = go.Figure()
        if chart_type == "bar":
            fig.add_trace(go.Bar(x=x, y=y, marker_color=_ACCENT))
        elif chart_type == "scatter":
            fig.add_trace(go.Scatter(x=x, y=y, mode="markers", marker={"size": 11, "color": _ACCENT}))
        elif chart_type == "pie":
            fig.add_trace(go.Pie(labels=x, values=y))
        else:  # default: line
            fig.add_trace(
                go.Scatter(x=x, y=y, mode="lines+markers", line={"color": _ACCENT, "width": 3}, marker={"size": 8})
            )

        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label,
            height=420,
            margin={"l": 40, "r": 20, "t": 50, "b": 40},
            plot_bgcolor="#f8fafc",
            paper_bgcolor="#ffffff",
            font={"size": 14},
        )
        return fig
    except Exception:
        return _placeholder_figure("Couldn't render this chart — try rephrasing the question.")
