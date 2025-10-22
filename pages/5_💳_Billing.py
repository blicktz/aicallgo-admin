"""
Billing - Read-only monitoring of subscriptions and invoices
"""
import streamlit as st
import asyncio
import pandas as pd
from config.auth import require_auth
from database.connection import get_async_session
from services.billing_service import (
    get_subscriptions,
    get_invoices,
    get_billing_stats,
    get_subscription_by_user,
    get_invoices_by_user
)
from services.user_service import get_user_by_id
from components.cards import metric_card, info_card
from utils.formatters import format_datetime, format_currency, format_status_badge

# Auth check
if not require_auth():
    st.stop()

st.title("💳 Billing")
st.markdown("Monitor subscriptions, invoices, and revenue")

# Warning banner
info_card(
    "Read-Only Mode",
    "This page displays billing data in read-only mode. Use the Stripe Dashboard for making changes to subscriptions or invoices.",
    "ℹ️",
    "blue"
)

st.divider()

# Billing stats
st.markdown("### Billing Metrics")

@st.cache_data(ttl=60)
def load_billing_stats():
    """Load billing statistics"""
    async def fetch():
        async with get_async_session() as session:
            return await get_billing_stats(session, date_range=30)
    return asyncio.run(fetch())

try:
    billing_stats = load_billing_stats()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_card(
            "Active Subscriptions",
            str(billing_stats["active_subs"]),
            help_text="Non-trial active subscriptions"
        )

    with col2:
        metric_card(
            "Trial Subscriptions",
            str(billing_stats["trial_subs"]),
            help_text="Subscriptions in trial period"
        )

    with col3:
        metric_card(
            "Revenue (30d)",
            format_currency(billing_stats["revenue_30d"]),
            help_text="Total revenue from paid invoices (30 days)"
        )

    with col4:
        metric_card(
            "Est. MRR",
            format_currency(billing_stats["mrr"]),
            help_text="Estimated Monthly Recurring Revenue"
        )

except Exception as e:
    st.error(f"Failed to load billing stats: {str(e)}")

st.divider()

# Tabs for subscriptions and invoices
tab1, tab2 = st.tabs(["📋 Subscriptions", "📄 Invoices"])

with tab1:
    st.markdown("### Subscriptions")

    # Filters
    col1, col2 = st.columns([3, 1])
    with col1:
        sub_status_filter = st.selectbox(
            "Status",
            ["all", "active", "trialing", "past_due", "canceled", "unpaid"],
            key="sub_status_filter"
        )
    with col2:
        if st.button("🔄 Refresh Subscriptions"):
            st.cache_data.clear()
            st.rerun()

    # Load subscriptions
    @st.cache_data(ttl=60)
    def load_subscriptions(status):
        """Load subscriptions with filters"""
        async def fetch():
            async with get_async_session() as session:
                return await get_subscriptions(
                    session,
                    limit=100,
                    offset=0,
                    status_filter=status if status != "all" else None
                )
        return asyncio.run(fetch())

    try:
        subscriptions = load_subscriptions(sub_status_filter)

        if not subscriptions:
            st.info("No subscriptions found")
        else:
            # Convert to DataFrame
            subscriptions_df = pd.DataFrame([
                {
                    "Stripe ID": sub.stripe_subscription_id,
                    "Plan": sub.stripe_plan_id,
                    "Status": sub.status,
                    "Current Period End": format_datetime(sub.current_period_end, format_str="%Y-%m-%d") if sub.current_period_end else "N/A",
                    "Cancel at Period End": "Yes" if sub.cancel_at_period_end else "No",
                    "Created": format_datetime(sub.created_at, format_str="%Y-%m-%d"),
                    "User ID": str(sub.user_id)
                }
                for sub in subscriptions
            ])

            # Display table
            st.dataframe(
                subscriptions_df,
                use_container_width=True,
                hide_index=True,
                height=500
            )

            st.caption(f"Showing {len(subscriptions)} subscriptions")

            # Stripe dashboard link
            st.markdown("**View in Stripe Dashboard:** [Subscriptions](https://dashboard.stripe.com/subscriptions)")

    except Exception as e:
        st.error(f"Failed to load subscriptions: {str(e)}")

    # Export subscriptions
    if st.button("📥 Export Subscriptions to CSV", key="export_subs"):
        try:
            subscriptions = load_subscriptions(sub_status_filter)
            csv = subscriptions_df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                "subscriptions.csv",
                "text/csv",
                key='download-subs-csv'
            )
        except Exception as e:
            st.error(f"Failed to export: {str(e)}")

with tab2:
    st.markdown("### Invoices")

    # Filters
    col1, col2 = st.columns([3, 1])
    with col1:
        inv_status_filter = st.selectbox(
            "Status",
            ["all", "paid", "open", "void", "uncollectible"],
            key="inv_status_filter"
        )
    with col2:
        if st.button("🔄 Refresh Invoices"):
            st.cache_data.clear()
            st.rerun()

    # Load invoices
    @st.cache_data(ttl=60)
    def load_invoices(status):
        """Load invoices with filters"""
        async def fetch():
            async with get_async_session() as session:
                return await get_invoices(
                    session,
                    limit=100,
                    offset=0,
                    status_filter=status if status != "all" else None
                )
        return asyncio.run(fetch())

    try:
        invoices = load_invoices(inv_status_filter)

        if not invoices:
            st.info("No invoices found")
        else:
            # Convert to DataFrame
            invoices_df = pd.DataFrame([
                {
                    "Stripe ID": inv.stripe_invoice_id,
                    "Amount Paid": format_currency(inv.amount_paid / 100 if inv.amount_paid else 0),
                    "Amount Due": format_currency(inv.amount_due / 100 if inv.amount_due else 0),
                    "Currency": inv.currency.upper(),
                    "Status": inv.status,
                    "Due Date": format_datetime(inv.due_date, format_str="%Y-%m-%d") if inv.due_date else "N/A",
                    "Created": format_datetime(inv.created_at, format_str="%Y-%m-%d"),
                    "User ID": str(inv.user_id)
                }
                for inv in invoices
            ])

            # Display table
            st.dataframe(
                invoices_df,
                use_container_width=True,
                hide_index=True,
                height=500
            )

            st.caption(f"Showing {len(invoices)} invoices")

            # Stripe dashboard link
            st.markdown("**View in Stripe Dashboard:** [Invoices](https://dashboard.stripe.com/invoices)")

    except Exception as e:
        st.error(f"Failed to load invoices: {str(e)}")

    # Export invoices
    if st.button("📥 Export Invoices to CSV", key="export_invs"):
        try:
            invoices = load_invoices(inv_status_filter)
            csv = invoices_df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                "invoices.csv",
                "text/csv",
                key='download-invs-csv'
            )
        except Exception as e:
            st.error(f"Failed to export: {str(e)}")

st.divider()

# Quick links
st.markdown("### Quick Links")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("🔗 [Stripe Dashboard](https://dashboard.stripe.com)")
with col2:
    st.markdown("🔗 [Customers](https://dashboard.stripe.com/customers)")
with col3:
    st.markdown("🔗 [Products](https://dashboard.stripe.com/products)")
