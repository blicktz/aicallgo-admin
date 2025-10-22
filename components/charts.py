"""
Chart components using Plotly with custom theme.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional, List


# Custom theme matching nextjs-frontend
CHART_THEME = {
    "primary": "#5f8a4e",  # Green from tailwind.config.ts
    "secondary": "#7c3aed",  # Purple
    "background": "#ffffff",
    "grid": "#e5e7eb",
    "text": "#1f2937",
}


def line_chart(
    df: pd.DataFrame,
    x_column: str,
    y_column: str,
    title: str,
    x_title: Optional[str] = None,
    y_title: Optional[str] = None,
    height: int = 400
):
    """
    Create a line chart.

    Args:
        df: DataFrame with data
        x_column: X-axis column name
        y_column: Y-axis column name
        title: Chart title
        x_title: X-axis label
        y_title: Y-axis label
        height: Chart height in pixels

    Usage:
        line_chart(calls_df, "date", "count", "Calls Over Time")
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df[x_column],
        y=df[y_column],
        mode='lines+markers',
        line=dict(color=CHART_THEME["primary"], width=2),
        marker=dict(size=6, color=CHART_THEME["primary"]),
        name=y_column
    ))

    fig.update_layout(
        title=title,
        xaxis_title=x_title or x_column,
        yaxis_title=y_title or y_column,
        height=height,
        plot_bgcolor=CHART_THEME["background"],
        paper_bgcolor=CHART_THEME["background"],
        font=dict(color=CHART_THEME["text"]),
        hovermode='x unified',
        showlegend=False
    )

    fig.update_xaxes(showgrid=True, gridcolor=CHART_THEME["grid"])
    fig.update_yaxes(showgrid=True, gridcolor=CHART_THEME["grid"])

    st.plotly_chart(fig, use_container_width=True)


def bar_chart(
    df: pd.DataFrame,
    x_column: str,
    y_column: str,
    title: str,
    orientation: str = "v",
    height: int = 400
):
    """
    Create a bar chart.

    Args:
        df: DataFrame with data
        x_column: X-axis column name
        y_column: Y-axis column name
        title: Chart title
        orientation: "v" for vertical, "h" for horizontal
        height: Chart height in pixels

    Usage:
        bar_chart(industry_df, "industry", "count", "Users by Industry")
    """
    fig = go.Figure()

    if orientation == "v":
        fig.add_trace(go.Bar(
            x=df[x_column],
            y=df[y_column],
            marker=dict(color=CHART_THEME["primary"])
        ))
    else:
        fig.add_trace(go.Bar(
            y=df[x_column],
            x=df[y_column],
            marker=dict(color=CHART_THEME["primary"]),
            orientation='h'
        ))

    fig.update_layout(
        title=title,
        height=height,
        plot_bgcolor=CHART_THEME["background"],
        paper_bgcolor=CHART_THEME["background"],
        font=dict(color=CHART_THEME["text"]),
        showlegend=False
    )

    fig.update_xaxes(showgrid=True, gridcolor=CHART_THEME["grid"])
    fig.update_yaxes(showgrid=True, gridcolor=CHART_THEME["grid"])

    st.plotly_chart(fig, use_container_width=True)


def area_chart(
    df: pd.DataFrame,
    x_column: str,
    y_columns: List[str],
    title: str,
    stacked: bool = True,
    height: int = 400
):
    """
    Create an area chart (useful for trends over time).

    Args:
        df: DataFrame with data
        x_column: X-axis column name
        y_columns: List of Y-axis column names
        title: Chart title
        stacked: Stack areas if True
        height: Chart height in pixels

    Usage:
        area_chart(revenue_df, "date", ["mrr", "one_time"], "Revenue Trend")
    """
    fig = go.Figure()

    colors = [CHART_THEME["primary"], CHART_THEME["secondary"]]

    for idx, y_col in enumerate(y_columns):
        fig.add_trace(go.Scatter(
            x=df[x_column],
            y=df[y_col],
            mode='lines',
            name=y_col,
            stackgroup='one' if stacked else None,
            fillcolor=colors[idx % len(colors)],
            line=dict(width=0.5, color=colors[idx % len(colors)])
        ))

    fig.update_layout(
        title=title,
        height=height,
        plot_bgcolor=CHART_THEME["background"],
        paper_bgcolor=CHART_THEME["background"],
        font=dict(color=CHART_THEME["text"]),
        hovermode='x unified'
    )

    fig.update_xaxes(showgrid=True, gridcolor=CHART_THEME["grid"])
    fig.update_yaxes(showgrid=True, gridcolor=CHART_THEME["grid"])

    st.plotly_chart(fig, use_container_width=True)


def pie_chart(
    df: pd.DataFrame,
    labels_column: str,
    values_column: str,
    title: str,
    donut: bool = True,
    height: int = 400
):
    """
    Create a pie or donut chart.

    Args:
        df: DataFrame with data
        labels_column: Column with labels
        values_column: Column with values
        title: Chart title
        donut: Create donut chart if True
        height: Chart height in pixels

    Usage:
        pie_chart(plan_df, "plan_name", "user_count", "Users by Plan")
    """
    fig = go.Figure()

    fig.add_trace(go.Pie(
        labels=df[labels_column],
        values=df[values_column],
        hole=0.4 if donut else 0,
        marker=dict(colors=[CHART_THEME["primary"], CHART_THEME["secondary"]])
    ))

    fig.update_layout(
        title=title,
        height=height,
        paper_bgcolor=CHART_THEME["background"],
        font=dict(color=CHART_THEME["text"])
    )

    st.plotly_chart(fig, use_container_width=True)
