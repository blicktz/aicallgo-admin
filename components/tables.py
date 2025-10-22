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
