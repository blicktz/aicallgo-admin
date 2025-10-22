# Admin Board - Phase 2: Read-Only Pages (Data Display)
## Detailed Implementation Plan

**Document Version**: 1.0
**Created**: 2025-10-22
**Estimated Time**: 4-5 days
**Phase Status**: Ready to implement

---

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Stage 1: Foundation Components](#stage-1-foundation-components)
4. [Stage 2: Service Layer](#stage-2-service-layer)
5. [Stage 3: Pages Implementation](#stage-3-pages-implementation)
6. [Technical Considerations](#technical-considerations)
7. [Testing Strategy](#testing-strategy)
8. [Success Criteria](#success-criteria)
9. [Post-Phase 2 Decisions](#post-phase-2-decisions)

---

## Overview

### Objectives
Phase 2 builds on the completed Phase 1 foundation to add **read-only data visualization** capabilities. This phase focuses on:
- Building reusable UI components for consistent design
- Creating service layer abstractions for database queries
- Implementing five main pages for viewing system data
- Establishing patterns for Phase 3 (data manipulation)

### Deliverables
- ✅ Dashboard with live metrics and charts
- ✅ User browsing and search functionality
- ✅ Business profile viewing
- ✅ Call log viewing with transcripts
- ✅ Billing data monitoring

### Architecture Principles
1. **Reusability**: Build components once, use everywhere
2. **Consistency**: Match web-backend patterns and nextjs-frontend design
3. **Performance**: Cache aggressively, paginate everything
4. **Maintainability**: Clear separation of concerns (components → services → database)

---

## Prerequisites

### Phase 1 Completion Checklist
Before starting Phase 2, verify these are complete:
- [x] Authentication system working (bcrypt, session-based)
- [x] Database connection established (async SQLAlchemy)
- [x] Custom CSS matching frontend theme
- [x] Project structure created (all directories exist)
- [x] Database models imported from web-backend
- [x] `.env` configured with DATABASE_URL and admin credentials

### Required Dependencies
Verify these are in `requirements.txt`:
```
streamlit>=1.30.0
sqlalchemy>=2.0.0
asyncpg>=0.29.0
pandas>=2.0.0
plotly>=5.18.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
bcrypt>=4.0.0
passlib>=1.7.4
pytz>=2023.3
phonenumbers>=8.13.0
humanize>=4.9.0
```

---

## Stage 1: Foundation Components
**Timeline**: Day 1
**Priority**: HIGH (all pages depend on these)

### 1.1 Create `utils/formatters.py`

**Purpose**: Centralized formatting utilities for consistent data display

**Functions to implement**:

```python
"""
Formatting utilities for consistent data display across admin board.
"""
from decimal import Decimal
from datetime import datetime, timedelta
import pytz
import phonenumbers
import humanize
from typing import Optional


def format_currency(amount: Optional[Decimal | float | int], currency: str = "USD") -> str:
    """
    Format number as currency with proper symbol and decimals.

    Args:
        amount: Amount to format (can be None)
        currency: Currency code (default: USD)

    Returns:
        Formatted string like "$1,234.56" or "$0.00" if None

    Examples:
        format_currency(1234.56) -> "$1,234.56"
        format_currency(None) -> "$0.00"
        format_currency(-50.25) -> "-$50.25"
    """
    if amount is None:
        return "$0.00"

    if currency == "USD":
        return f"${abs(amount):,.2f}" if amount >= 0 else f"-${abs(amount):,.2f}"

    return f"{amount:,.2f} {currency}"


def format_datetime(
    dt: Optional[datetime],
    timezone: str = "America/Los_Angeles",
    format_str: str = "%Y-%m-%d %H:%M %Z"
) -> str:
    """
    Format datetime with timezone conversion.

    Args:
        dt: Datetime to format (can be None)
        timezone: IANA timezone name
        format_str: strftime format string

    Returns:
        Formatted datetime string or "N/A" if None

    Examples:
        format_datetime(datetime.now()) -> "2024-10-22 14:30 PDT"
    """
    if dt is None:
        return "N/A"

    # Ensure datetime is timezone-aware
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    # Convert to specified timezone
    tz = pytz.timezone(timezone)
    local_dt = dt.astimezone(tz)

    return local_dt.strftime(format_str)


def format_date(dt: Optional[datetime], format_str: str = "%Y-%m-%d") -> str:
    """
    Format datetime as date only.

    Args:
        dt: Datetime to format (can be None)
        format_str: strftime format string

    Returns:
        Formatted date string or "N/A" if None
    """
    if dt is None:
        return "N/A"
    return dt.strftime(format_str)


def format_phone(phone: Optional[str], country: str = "US") -> str:
    """
    Format phone number to display format.

    Args:
        phone: Phone number in E.164 or any format
        country: Country code for parsing

    Returns:
        Formatted phone like "+1 (555) 123-4567" or original if parse fails

    Examples:
        format_phone("+15551234567") -> "+1 (555) 123-4567"
        format_phone("5551234567") -> "+1 (555) 123-4567"
    """
    if not phone:
        return "N/A"

    try:
        parsed = phonenumbers.parse(phone, country)
        return phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
        )
    except Exception:
        return phone  # Return original if parsing fails


def format_duration(seconds: Optional[int | float]) -> str:
    """
    Format duration in seconds to HH:MM:SS.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration like "01:23:45" or "N/A" if None

    Examples:
        format_duration(3665) -> "01:01:05"
        format_duration(45) -> "00:00:45"
    """
    if seconds is None:
        return "N/A"

    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def humanize_datetime(dt: Optional[datetime]) -> str:
    """
    Convert datetime to human-readable relative time.

    Args:
        dt: Datetime to humanize

    Returns:
        Humanized string like "2 hours ago" or "in 3 days"

    Examples:
        humanize_datetime(datetime.now() - timedelta(hours=2)) -> "2 hours ago"
    """
    if dt is None:
        return "N/A"

    # Ensure both datetimes are timezone-aware for comparison
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    now = datetime.now(pytz.utc)
    return humanize.naturaltime(now - dt)


def format_number_abbrev(num: Optional[int | float], decimals: int = 1) -> str:
    """
    Format large numbers with abbreviations (K, M, B).

    Args:
        num: Number to format
        decimals: Number of decimal places

    Returns:
        Abbreviated string like "1.2K", "3.4M", "5.6B"

    Examples:
        format_number_abbrev(1234) -> "1.2K"
        format_number_abbrev(1234567) -> "1.2M"
        format_number_abbrev(123) -> "123"
    """
    if num is None:
        return "0"

    num = float(num)

    if num < 1000:
        return f"{int(num)}"
    elif num < 1_000_000:
        return f"{num/1000:.{decimals}f}K"
    elif num < 1_000_000_000:
        return f"{num/1_000_000:.{decimals}f}M"
    else:
        return f"{num/1_000_000_000:.{decimals}f}B"


def format_percentage(value: Optional[float], decimals: int = 1) -> str:
    """
    Format number as percentage.

    Args:
        value: Value to format (0.25 = 25%)
        decimals: Number of decimal places

    Returns:
        Formatted percentage like "25.0%"
    """
    if value is None:
        return "0.0%"

    return f"{value * 100:.{decimals}f}%"


def format_status_badge(status: str) -> str:
    """
    Get emoji for common status values.

    Args:
        status: Status string

    Returns:
        Status with emoji prefix

    Examples:
        format_status_badge("active") -> "✅ Active"
        format_status_badge("failed") -> "❌ Failed"
    """
    status_map = {
        "active": "✅",
        "inactive": "⏸️",
        "trialing": "🎯",
        "past_due": "⚠️",
        "canceled": "❌",
        "unpaid": "💳",
        "answered_by_ai": "🤖",
        "forwarded": "📞",
        "missed": "📵",
        "voicemail": "📧",
    }

    emoji = status_map.get(status.lower(), "ℹ️")
    return f"{emoji} {status.title()}"
```

**Testing checklist**:
- [ ] Test with None values
- [ ] Test with negative numbers (currency, duration)
- [ ] Test with international phone numbers
- [ ] Test with various timezones
- [ ] Test edge cases (0, very large numbers)

---

### 1.2 Create `components/cards.py`

**Purpose**: Reusable card components for metrics and information display

**Components to implement**:

```python
"""
Card components for metrics and information display.
"""
import streamlit as st
from typing import Optional


def metric_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    delta_color: str = "normal",
    help_text: Optional[str] = None
):
    """
    Display a metric card with optional change indicator.

    Args:
        label: Metric label (e.g., "Total Users")
        value: Main metric value (e.g., "1,247")
        delta: Change indicator (e.g., "+12 (7d)")
        delta_color: "normal", "inverse", or "off"
        help_text: Optional tooltip text

    Usage:
        metric_card("Total Users", "1,247", "+12 (7d)")
    """
    st.metric(
        label=label,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=help_text
    )


def stat_card(title: str, value: str, icon: str = "📊", description: Optional[str] = None):
    """
    Display a larger featured statistic card.

    Args:
        title: Card title
        value: Large display value
        icon: Emoji icon
        description: Optional description text

    Usage:
        stat_card("Revenue This Month", "$24,567", "💰", "Up 15% from last month")
    """
    st.markdown(
        f"""
        <div style="padding: 1.5rem; background: white; border-radius: 0.5rem;
                    border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <span style="font-size: 1.5rem;">{icon}</span>
                <h3 style="margin: 0; color: #1f2937; font-size: 0.875rem; font-weight: 600;">
                    {title}
                </h3>
            </div>
            <div style="font-size: 2rem; font-weight: 700; color: #111827; margin-bottom: 0.25rem;">
                {value}
            </div>
            {f'<div style="color: #6b7280; font-size: 0.875rem;">{description}</div>' if description else ''}
        </div>
        """,
        unsafe_allow_html=True
    )


def info_card(title: str, content: str, icon: str = "ℹ️", color: str = "blue"):
    """
    Display an informational card.

    Args:
        title: Card title
        content: Main content text
        icon: Emoji icon
        color: "blue", "green", "yellow", "red"

    Usage:
        info_card("Note", "This is read-only", "⚠️", "yellow")
    """
    color_map = {
        "blue": {"bg": "#eff6ff", "border": "#3b82f6", "text": "#1e40af"},
        "green": {"bg": "#f0fdf4", "border": "#22c55e", "text": "#15803d"},
        "yellow": {"bg": "#fefce8", "border": "#eab308", "text": "#a16207"},
        "red": {"bg": "#fef2f2", "border": "#ef4444", "text": "#b91c1c"},
    }

    colors = color_map.get(color, color_map["blue"])

    st.markdown(
        f"""
        <div style="padding: 1rem; background: {colors['bg']}; border-radius: 0.5rem;
                    border-left: 4px solid {colors['border']}; margin: 1rem 0;">
            <div style="display: flex; align-items: flex-start; gap: 0.75rem;">
                <span style="font-size: 1.25rem;">{icon}</span>
                <div>
                    <div style="font-weight: 600; color: {colors['text']}; margin-bottom: 0.25rem;">
                        {title}
                    </div>
                    <div style="color: {colors['text']}; font-size: 0.875rem;">
                        {content}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def alert_card(message: str, type: str = "info", dismissible: bool = False):
    """
    Display an alert message.

    Args:
        message: Alert message
        type: "info", "success", "warning", "error"
        dismissible: Show close button

    Usage:
        alert_card("Database connected successfully", "success")
    """
    if type == "info":
        st.info(message)
    elif type == "success":
        st.success(message)
    elif type == "warning":
        st.warning(message)
    elif type == "error":
        st.error(message)
```

**Testing checklist**:
- [ ] Test all card types render correctly
- [ ] Verify colors match design system
- [ ] Test with various content lengths
- [ ] Verify responsive layout

---

### 1.3 Create `components/tables.py`

**Purpose**: Enhanced table components with sorting, filtering, and styling

**Components to implement**:

```python
"""
Table components for data display with enhanced functionality.
"""
import streamlit as st
import pandas as pd
from typing import Optional, List, Dict, Any


def render_dataframe(
    df: pd.DataFrame,
    height: Optional[int] = None,
    hide_index: bool = True,
    column_config: Optional[Dict[str, Any]] = None
):
    """
    Render a styled pandas DataFrame.

    Args:
        df: DataFrame to display
        height: Optional fixed height in pixels
        hide_index: Hide DataFrame index
        column_config: Streamlit column configuration

    Usage:
        render_dataframe(users_df, height=400)
    """
    st.dataframe(
        df,
        height=height,
        hide_index=hide_index,
        column_config=column_config,
        use_container_width=True
    )


def sortable_table(
    df: pd.DataFrame,
    default_sort_column: str,
    default_sort_ascending: bool = True
) -> pd.DataFrame:
    """
    Display table with sortable columns.

    Args:
        df: DataFrame to display
        default_sort_column: Column to sort by default
        default_sort_ascending: Sort direction

    Returns:
        Sorted DataFrame

    Usage:
        sorted_df = sortable_table(users_df, "created_at", False)
    """
    # Sort column selector
    col1, col2 = st.columns([3, 1])

    with col1:
        sort_column = st.selectbox(
            "Sort by",
            options=df.columns.tolist(),
            index=df.columns.tolist().index(default_sort_column)
        )

    with col2:
        sort_ascending = st.checkbox("Ascending", value=default_sort_ascending)

    # Sort DataFrame
    sorted_df = df.sort_values(by=sort_column, ascending=sort_ascending)

    # Display
    render_dataframe(sorted_df)

    return sorted_df


def paginated_table(
    df: pd.DataFrame,
    rows_per_page: int = 50,
    show_page_selector: bool = True
) -> pd.DataFrame:
    """
    Display table with pagination controls.

    Args:
        df: DataFrame to display
        rows_per_page: Number of rows per page
        show_page_selector: Show page number selector

    Returns:
        Current page DataFrame

    Usage:
        page_df = paginated_table(users_df, rows_per_page=25)
    """
    total_rows = len(df)
    total_pages = (total_rows + rows_per_page - 1) // rows_per_page

    if total_pages <= 1:
        render_dataframe(df)
        return df

    # Initialize page number in session state
    if "current_page" not in st.session_state:
        st.session_state.current_page = 0

    # Pagination controls
    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:
        if st.button("◀ Previous", disabled=st.session_state.current_page == 0):
            st.session_state.current_page -= 1
            st.rerun()

    with col2:
        if show_page_selector:
            page_num = st.selectbox(
                "Page",
                options=range(total_pages),
                index=st.session_state.current_page,
                format_func=lambda x: f"Page {x + 1} of {total_pages}"
            )
            if page_num != st.session_state.current_page:
                st.session_state.current_page = page_num
                st.rerun()
        else:
            st.markdown(
                f"<div style='text-align: center;'>Page {st.session_state.current_page + 1} of {total_pages}</div>",
                unsafe_allow_html=True
            )

    with col3:
        if st.button("Next ▶", disabled=st.session_state.current_page >= total_pages - 1):
            st.session_state.current_page += 1
            st.rerun()

    # Calculate page slice
    start_idx = st.session_state.current_page * rows_per_page
    end_idx = min(start_idx + rows_per_page, total_rows)

    # Display current page
    page_df = df.iloc[start_idx:end_idx]
    render_dataframe(page_df)

    # Show row count
    st.caption(f"Showing rows {start_idx + 1}-{end_idx} of {total_rows}")

    return page_df


def filterable_table(
    df: pd.DataFrame,
    searchable_columns: List[str],
    filter_columns: Optional[Dict[str, List[str]]] = None
) -> pd.DataFrame:
    """
    Display table with search and filter capabilities.

    Args:
        df: DataFrame to display
        searchable_columns: Columns to include in text search
        filter_columns: Dict of {column_name: [options]} for dropdown filters

    Returns:
        Filtered DataFrame

    Usage:
        filtered_df = filterable_table(
            users_df,
            searchable_columns=["email", "full_name"],
            filter_columns={"plan": ["all", "trial", "professional"]}
        )
    """
    filtered_df = df.copy()

    # Search bar
    search_query = st.text_input("🔍 Search", placeholder="Search...")

    if search_query:
        # Search across specified columns
        mask = pd.Series([False] * len(filtered_df))
        for col in searchable_columns:
            if col in filtered_df.columns:
                mask |= filtered_df[col].astype(str).str.contains(
                    search_query, case=False, na=False
                )
        filtered_df = filtered_df[mask]

    # Filter dropdowns
    if filter_columns:
        filter_cols = st.columns(len(filter_columns))

        for idx, (col_name, options) in enumerate(filter_columns.items()):
            with filter_cols[idx]:
                selected = st.selectbox(
                    f"Filter by {col_name.replace('_', ' ').title()}",
                    options=options
                )

                if selected and selected.lower() != "all":
                    filtered_df = filtered_df[
                        filtered_df[col_name].astype(str).str.lower() == selected.lower()
                    ]

    # Display filtered table
    render_dataframe(filtered_df)

    return filtered_df
```

**Testing checklist**:
- [ ] Test pagination with various dataset sizes
- [ ] Test sorting with different column types
- [ ] Test search with special characters
- [ ] Verify filters work correctly

---

### 1.4 Create `components/charts.py`

**Purpose**: Plotly charts with custom theme matching frontend

**Components to implement**:

```python
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
```

**Testing checklist**:
- [ ] Test all chart types with sample data
- [ ] Verify custom colors are applied
- [ ] Test with empty/null data
- [ ] Verify responsiveness

---

## Stage 2: Service Layer
**Timeline**: Day 1-2
**Priority**: HIGH (pages consume these services)

### 2.1 Create `services/user_service.py`

**Purpose**: User data access layer with read operations

**Implementation**:

```python
"""
User service for database operations.
Provides read-only operations for Phase 2.
"""
from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Business, Subscription, CreditBalance
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


async def get_users(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    search_query: Optional[str] = None,
    plan_filter: Optional[str] = None,
    status_filter: Optional[str] = None
) -> List[User]:
    """
    Get users with pagination and filters.

    Args:
        session: Database session
        limit: Maximum number of results
        offset: Pagination offset
        search_query: Search in email/name
        plan_filter: Filter by subscription plan
        status_filter: Filter by is_active status

    Returns:
        List of User objects with relationships loaded
    """
    try:
        query = select(User)

        # Apply search filter
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.where(
                or_(
                    User.email.ilike(search_pattern),
                    User.full_name.ilike(search_pattern)
                )
            )

        # Apply status filter
        if status_filter and status_filter.lower() != "all":
            is_active = status_filter.lower() == "active"
            query = query.where(User.is_active == is_active)

        # TODO: Add plan filter after joining with subscriptions
        # This requires more complex query with join

        # Order by creation date (newest first)
        query = query.order_by(desc(User.created_at))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await session.execute(query)
        users = result.scalars().all()

        return list(users)

    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise


async def get_user_by_id(session: AsyncSession, user_id: str) -> Optional[User]:
    """
    Get user by ID with all relationships loaded.

    Args:
        session: Database session
        user_id: User UUID

    Returns:
        User object or None if not found
    """
    try:
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}")
        raise


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    """
    Get user by email address.

    Args:
        session: Database session
        email: User email

    Returns:
        User object or None if not found
    """
    try:
        query = select(User).where(User.email == email)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error fetching user by email {email}: {e}")
        raise


async def get_user_stats(session: AsyncSession) -> Dict[str, Any]:
    """
    Get user statistics for dashboard.

    Returns:
        Dict with user metrics:
        - total_users: Total user count
        - active_users: Users with is_active=True
        - new_users_7d: Users created in last 7 days
        - new_users_30d: Users created in last 30 days
    """
    try:
        # Total users
        total_query = select(func.count(User.id))
        total_result = await session.execute(total_query)
        total_users = total_result.scalar()

        # Active users
        active_query = select(func.count(User.id)).where(User.is_active == True)
        active_result = await session.execute(active_query)
        active_users = active_result.scalar()

        # New users in last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_7d_query = select(func.count(User.id)).where(User.created_at >= week_ago)
        new_7d_result = await session.execute(new_7d_query)
        new_users_7d = new_7d_result.scalar()

        # New users in last 30 days
        month_ago = datetime.utcnow() - timedelta(days=30)
        new_30d_query = select(func.count(User.id)).where(User.created_at >= month_ago)
        new_30d_result = await session.execute(new_30d_query)
        new_users_30d = new_30d_result.scalar()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "new_users_7d": new_users_7d,
            "new_users_30d": new_users_30d,
        }

    except Exception as e:
        logger.error(f"Error fetching user stats: {e}")
        raise


async def get_recent_signups(session: AsyncSession, limit: int = 10) -> List[User]:
    """
    Get most recent user signups.

    Args:
        session: Database session
        limit: Number of recent users to fetch

    Returns:
        List of recently created User objects
    """
    try:
        query = select(User).order_by(desc(User.created_at)).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    except Exception as e:
        logger.error(f"Error fetching recent signups: {e}")
        raise
```

**Reference**: `web-backend/app/crud/crud_user.py` for patterns

---

### 2.2 Create `services/business_service.py`

**Purpose**: Business data access layer

**Implementation**: Similar structure to user_service.py with these functions:
- `get_businesses(limit, offset, search_query, industry_filter)`
- `get_business_by_id(business_id)`
- `get_businesses_by_user(user_id)`
- `get_business_stats()`

**Reference**: `web-backend/app/crud/crud_business.py`

---

### 2.3 Create `services/call_log_service.py`

**Purpose**: Call log data access layer

**Implementation**: Functions needed:
- `get_call_logs(limit, offset, filters)`
- `get_call_log_by_id(call_id)`
- `get_call_stats(date_range)`
- `get_calls_by_business(business_id, limit)`
- `get_calls_by_user(user_id, limit)`
- `get_recent_calls(limit)`

**Reference**: `web-backend/app/crud/crud_call_log.py`

---

### 2.4 Create `services/billing_service.py`

**Purpose**: Billing and subscription data access

**Implementation**: Functions needed:
- `get_subscriptions(limit, offset, status_filter)`
- `get_subscription_by_user(user_id)`
- `get_invoices(limit, offset, status_filter)`
- `get_invoices_by_user(user_id)`
- `get_billing_stats(date_range)`
- `get_credit_balance(user_id)`

**Reference**: `web-backend/app/crud/crud_stripe.py` and `web-backend/app/models/credit_models.py`

---

## Stage 3: Pages Implementation
**Timeline**: Day 2-4
**Priority**: Build in order of user value

### 3.1 Create `pages/1_📊_Dashboard.py`

**Priority**: 1 (Most visible page)

**Layout Structure**:
```python
"""
Dashboard - System overview with KPIs and charts
"""
import streamlit as st
import asyncio
from config.auth import require_auth
from database.connection import get_async_session
from services.user_service import get_user_stats, get_recent_signups
from services.billing_service import get_billing_stats
from services.call_log_service import get_call_stats
from components.cards import metric_card, info_card
from components.charts import line_chart, area_chart
from utils.formatters import format_currency, format_number_abbrev, humanize_datetime
import pandas as pd

# Auth check
if not require_auth():
    st.stop()

# Page config
st.title("📊 Dashboard")
st.markdown("System overview and key metrics")

# Auto-refresh toggle
col1, col2 = st.columns([3, 1])
with col2:
    auto_refresh = st.checkbox("Auto-refresh (60s)", value=False)
    if auto_refresh:
        st.rerun()  # Simple auto-refresh

# Load data
@st.cache_data(ttl=60)
def load_dashboard_data():
    """Load all dashboard data with caching"""
    async def fetch_data():
        async with get_async_session() as session:
            user_stats = await get_user_stats(session)
            billing_stats = await get_billing_stats(session, date_range=30)
            call_stats = await get_call_stats(session, date_range=30)
            recent_users = await get_recent_signups(session, limit=5)

            return {
                "user_stats": user_stats,
                "billing_stats": billing_stats,
                "call_stats": call_stats,
                "recent_users": recent_users,
            }

    return asyncio.run(fetch_data())

with st.spinner("Loading dashboard..."):
    data = load_dashboard_data()

# KPI Cards Row
st.markdown("### Key Metrics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    metric_card(
        "Total Users",
        format_number_abbrev(data["user_stats"]["total_users"]),
        f"+{data['user_stats']['new_users_7d']} (7d)",
        help_text="Total registered users"
    )

with col2:
    metric_card(
        "Active Subscriptions",
        format_number_abbrev(data["billing_stats"]["active_subs"]),
        delta=None,
        help_text="Non-trial, active subscriptions"
    )

with col3:
    metric_card(
        "Calls (30d)",
        format_number_abbrev(data["call_stats"]["total_calls"]),
        delta=None,
        help_text="Total calls in last 30 days"
    )

with col4:
    metric_card(
        "Revenue (30d)",
        format_currency(data["billing_stats"]["revenue_30d"]),
        delta=None,
        help_text="Total revenue from paid invoices"
    )

st.divider()

# Charts Row
st.markdown("### Trends")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    # Calls over time chart (mock data for now)
    # TODO: Implement actual time series query in call_log_service
    calls_df = pd.DataFrame({
        "date": pd.date_range(start="2024-09-22", periods=30, freq="D"),
        "calls": [50 + i * 2 for i in range(30)]  # Mock data
    })
    line_chart(calls_df, "date", "calls", "Calls Over Time (30 days)")

with chart_col2:
    # Revenue trend chart (mock data for now)
    # TODO: Implement actual revenue time series query
    revenue_df = pd.DataFrame({
        "date": pd.date_range(start="2024-09-22", periods=30, freq="D"),
        "revenue": [800 + i * 10 for i in range(30)]  # Mock data
    })
    area_chart(revenue_df, "date", ["revenue"], "Revenue Trend (30 days)", stacked=False)

st.divider()

# Activity Feeds Row
st.markdown("### Recent Activity")
feed_col1, feed_col2 = st.columns(2)

with feed_col1:
    st.markdown("#### 🆕 New Signups")
    if data["recent_users"]:
        for user in data["recent_users"]:
            st.markdown(f"- **{user.email}**")
            st.caption(f"  {humanize_datetime(user.created_at)}")
    else:
        st.info("No recent signups")

with feed_col2:
    st.markdown("#### ⚠️ Alerts")
    # TODO: Implement alert logic in billing_service
    # - Trial expirations (<24h)
    # - Failed payments
    # - Low credit balances (<$5)
    st.info("No active alerts")

# Refresh button
if st.button("🔄 Refresh Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
```

**Data requirements**:
- User stats (total, active, new signups)
- Billing stats (MRR, revenue, active subs)
- Call stats (total, by status)
- Time series data for charts (requires new service methods)

---

### 3.2 Create `pages/2_👥_Users.py`

**Priority**: 2 (High-traffic page)

**Key features**:
- Search bar with debounced input
- Plan and status filters
- 70/30 split layout (table/detail panel)
- Sortable columns
- Pagination
- Export to CSV

**Implementation outline**:
```python
import streamlit as st
from services.user_service import get_users, get_user_by_id
from services.business_service import get_businesses_by_user
from components.tables import filterable_table, paginated_table
from utils.formatters import format_datetime, format_currency, format_status_badge

# Auth check
if not require_auth():
    st.stop()

st.title("👥 Users")

# Search and filters
search_query = st.text_input("🔍 Search by email or name")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    plan_filter = st.selectbox("Plan", ["all", "trial", "professional", "scale"])
with col2:
    status_filter = st.selectbox("Status", ["all", "active", "inactive"])
with col3:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

# Load users
@st.cache_data(ttl=60)
def load_users(search, plan, status, page_num, per_page):
    async def fetch():
        async with get_async_session() as session:
            offset = page_num * per_page
            return await get_users(
                session,
                limit=per_page,
                offset=offset,
                search_query=search if search else None,
                plan_filter=plan if plan != "all" else None,
                status_filter=status if status != "all" else None
            )
    return asyncio.run(fetch())

# Main layout: table + detail panel
table_col, detail_col = st.columns([7, 3])

with table_col:
    st.markdown("### User List")
    users = load_users(search_query, plan_filter, status_filter, 0, 50)

    # Convert to DataFrame
    users_df = pd.DataFrame([
        {
            "Email": u.email,
            "Name": u.full_name or "N/A",
            "Plan": "TODO",  # Need subscription join
            "Status": format_status_badge("active" if u.is_active else "inactive"),
            "Created": format_datetime(u.created_at),
            "ID": str(u.id)
        }
        for u in users
    ])

    # Clickable rows (use session state to track selection)
    if not users_df.empty:
        selected_row = st.dataframe(
            users_df.drop(columns=["ID"]),
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row"
        )

        # Get selected user ID
        if selected_row and len(selected_row["selection"]["rows"]) > 0:
            selected_idx = selected_row["selection"]["rows"][0]
            selected_user_id = users_df.iloc[selected_idx]["ID"]
            st.session_state["selected_user_id"] = selected_user_id

with detail_col:
    st.markdown("### User Details")

    if "selected_user_id" in st.session_state:
        # Load full user details
        @st.cache_data(ttl=60)
        def load_user_details(user_id):
            async def fetch():
                async with get_async_session() as session:
                    user = await get_user_by_id(session, user_id)
                    businesses = await get_businesses_by_user(session, user_id)
                    # TODO: Load credit balance, recent calls
                    return {"user": user, "businesses": businesses}
            return asyncio.run(fetch())

        details = load_user_details(st.session_state["selected_user_id"])
        user = details["user"]

        # Display user info
        st.markdown(f"**Email:** {user.email}")
        st.markdown(f"**Name:** {user.full_name or 'N/A'}")
        st.markdown(f"**Status:** {format_status_badge('active' if user.is_active else 'inactive')}")
        st.markdown(f"**Created:** {format_datetime(user.created_at)}")

        st.divider()

        st.markdown("**Businesses:**")
        if details["businesses"]:
            for biz in details["businesses"]:
                st.markdown(f"- {biz.business_name}")
        else:
            st.caption("No businesses")

        st.divider()

        st.markdown("**Quick Actions:**")
        st.button("⚡ Edit Entitlements", disabled=True, help="Coming in Phase 3")
        st.button("💰 Adjust Credits", disabled=True, help="Coming in Phase 3")
        st.button("📞 View Call Logs", disabled=True)
    else:
        st.info("Select a user from the table to view details")

# Export button
if st.button("📥 Export to CSV"):
    csv = users_df.to_csv(index=False)
    st.download_button(
        "Download CSV",
        csv,
        "users.csv",
        "text/csv",
        key='download-csv'
    )
```

---

### 3.3 Create `pages/3_🏢_Businesses.py`

**Priority**: 3

**Key features**:
- Search by business name
- Industry filter
- Business hours display
- Core services list
- Call statistics (30-day)

**Similar implementation pattern to Users page**

---

### 3.4 Create `pages/4_📞_Call_Logs.py`

**Priority**: 4

**Key features**:
- Date range picker (last 7d, 30d, 90d, custom)
- Status filter (answered_by_ai, forwarded, missed, voicemail)
- Phone number search
- Expandable transcript viewer
- Recording playback link (if exists)

**Special considerations**:
- Transcripts can be very long - use `st.expander()` for each call
- Format phone numbers properly
- Show duration in HH:MM:SS format

---

### 3.5 Create `pages/5_💳_Billing.py`

**Priority**: 5

**Key features**:
- KPI cards for billing metrics
- Subscriptions table with status badges
- Invoices table with payment status
- Click-through to Stripe dashboard (external link)
- Read-only warning banner

**Important**:
- Display warning that this is read-only (Phase 3 adds mutations)
- Link Stripe IDs to Stripe dashboard for deeper investigation
- Show credit balances inline with users

---

## Technical Considerations

### Database Query Optimization

1. **Eager Loading with selectinload()**:
```python
from sqlalchemy.orm import selectinload

# Load user with relationships
query = select(User).options(
    selectinload(User.businesses),
    selectinload(User.subscriptions),
    selectinload(User.credit_balance)
).where(User.id == user_id)
```

2. **Pagination**:
```python
# Always use limit and offset
query = query.limit(50).offset(page_num * 50)
```

3. **Filtering**:
```python
# Use indexed columns for filtering
query = query.where(User.email.ilike(f"%{search}%"))
```

4. **Caching**:
```python
# Cache expensive queries
@st.cache_data(ttl=60)  # Cache for 60 seconds
def load_data():
    # ... query logic
    pass
```

### Error Handling

1. **Wrap async calls**:
```python
try:
    result = await session.execute(query)
    return result.scalars().all()
except Exception as e:
    logger.error(f"Database error: {e}")
    st.error("Failed to load data. Please try again.")
    return []
```

2. **Graceful degradation**:
```python
# Show empty state instead of crashing
if not data:
    st.info("No data available")
    return
```

3. **User-friendly errors**:
```python
# Don't expose internal errors to users
st.error("Unable to connect to database. Please contact support.")
```

### Performance

1. **Lazy loading for detail panels** - only query when row clicked
2. **Implement pagination** - never load all records at once
3. **Cache query results** - use `@st.cache_data` with appropriate TTL
4. **Limit relationship loading** - only load what's displayed

### Design Consistency

1. **Colors**: Use variables from `static/custom.css`
2. **Spacing**: Consistent padding and margins
3. **Typography**: Match font sizes and weights
4. **Icons**: Use emoji consistently across pages

---

## Testing Strategy

### Component Testing

**Formatters** (`utils/formatters.py`):
- [ ] Test `format_currency` with None, 0, negative, large numbers
- [ ] Test `format_datetime` with various timezones
- [ ] Test `format_phone` with E.164, national, invalid formats
- [ ] Test `format_duration` with edge cases (0, very large)

**Cards** (`components/cards.py`):
- [ ] Verify all card types render correctly
- [ ] Test with long content (text overflow)
- [ ] Verify colors match design system

**Tables** (`components/tables.py`):
- [ ] Test pagination with 0, 1, many pages
- [ ] Test sorting with different data types
- [ ] Test filtering with special characters

**Charts** (`components/charts.py`):
- [ ] Test with empty datasets
- [ ] Test with single data point
- [ ] Verify custom theme colors applied

### Service Testing

**Database Queries**:
- [ ] Test pagination boundaries (first page, last page, beyond last)
- [ ] Test search with special characters, Unicode
- [ ] Verify no N+1 query problems (check logs)
- [ ] Test filters with various combinations

**Connection to Staging**:
```bash
# Port-forward to staging database
kubectl port-forward svc/postgres -n aicallgo-staging 5432:5432

# Update .env
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# Test queries
poetry run python -m services.user_service
```

### Page Testing

**Dashboard**:
- [ ] Verify all KPIs load correctly
- [ ] Charts render with real data
- [ ] Auto-refresh works
- [ ] Recent activity displays correctly

**Users**:
- [ ] Search returns correct results
- [ ] Filters work (plan, status)
- [ ] Detail panel loads on row click
- [ ] Export to CSV works

**Businesses**:
- [ ] Search and filters work
- [ ] Business hours display correctly
- [ ] Services list renders

**Call Logs**:
- [ ] Date range filtering works
- [ ] Status filter works
- [ ] Transcript expander works
- [ ] Phone numbers formatted correctly

**Billing**:
- [ ] Subscriptions table loads
- [ ] Invoices table loads
- [ ] Stripe links open correctly
- [ ] Credit balances display

### End-to-End Testing

1. **Navigation flow**:
   - [ ] Can navigate between all pages
   - [ ] Sidebar navigation works
   - [ ] Back button works

2. **Authentication**:
   - [ ] Login required for all pages
   - [ ] Session timeout works
   - [ ] Logout clears session

3. **Performance**:
   - [ ] Pages load in < 3 seconds
   - [ ] No JavaScript errors in console
   - [ ] Responsive at different screen sizes

---

## Success Criteria

### Functional Requirements
✅ All 5 pages render without errors
✅ Data displays correctly from staging database
✅ Search and filtering work on all applicable pages
✅ Charts render with proper theme and interactivity
✅ Navigation between pages works smoothly
✅ Export to CSV functions properly

### Performance Requirements
✅ Initial page load < 3 seconds
✅ Cached queries respond < 500ms
✅ No N+1 query problems
✅ Database connection pool stable

### Code Quality Requirements
✅ Follows established patterns from Phase 1
✅ Error handling in all service methods
✅ Logging for debugging
✅ Type hints on all functions
✅ Docstrings on public functions

### User Experience Requirements
✅ Consistent design across all pages
✅ Helpful error messages (no stack traces)
✅ Loading indicators for async operations
✅ Empty states for no data
✅ Tooltips on metrics for clarity

---

## Post-Phase 2 Decisions

### Evaluation Criteria

After completing Phase 2, evaluate the following:

1. **Streamlit Performance**:
   - Are page loads fast enough?
   - Does caching work effectively?
   - Any memory issues with long sessions?

2. **User Experience**:
   - Is the UI intuitive for admins?
   - Are there missing UI components?
   - Does the design feel polished?

3. **Development Velocity**:
   - Was development fast with Streamlit?
   - Are we fighting the framework?
   - Can we easily add Phase 3 features?

### Decision Matrix

| Factor | Keep Streamlit | Migrate to Flask-Admin |
|--------|---------------|------------------------|
| **UX is acceptable** | ✅ Continue | ❌ Consider migration |
| **Performance is good** | ✅ Continue | ⚠️ Optimize first |
| **Easy to add CRUD** | ✅ Continue | ❌ Consider migration |
| **Need richer components** | ⚠️ Evaluate | ✅ Migration beneficial |
| **Team comfortable** | ✅ Continue | ❌ Avoid unless necessary |

### Recommendation

**If staying with Streamlit**:
- Proceed to Phase 3 (Entitlements & Credits)
- Focus on form validation and transaction safety
- Add audit logging for all mutations

**If migrating to Flask-Admin**:
- Create migration plan document
- Prototype one page (e.g., Users) in Flask-Admin
- Compare development effort and UX
- Make final decision before Phase 3

---

## Appendix

### Useful Commands

```bash
# Run admin board locally
cd services/admin-board
poetry run streamlit run app.py

# Port-forward to staging database
kubectl port-forward svc/postgres -n aicallgo-staging 5432:5432

# Run with specific .env file
cd services/admin-board
poetry run streamlit run app.py --server.port 8501

# Clear Streamlit cache
# In app: st.cache_data.clear()

# Check database connection
poetry run python -c "from database.connection import check_db_health; import asyncio; print(asyncio.run(check_db_health()))"
```

### Common Pitfalls

1. **Async/Sync mixing**: Always use `asyncio.run()` to call async functions from Streamlit
2. **Session state**: Remember Streamlit reruns entire script on each interaction
3. **Caching**: Be careful with mutable objects in `@st.cache_data`
4. **Database connections**: Always use context managers (`async with`)
5. **Large datasets**: Always paginate, never load all records

### Resources

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Plotly Python](https://plotly.com/python/)
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/en/20/)
- [Web Backend CLAUDE.md](../../../web-backend/CLAUDE.md)
- [Implementation Plan](./IMPLEMENTATION_PLAN.md)

---

**End of Phase 2 Detailed Plan**
