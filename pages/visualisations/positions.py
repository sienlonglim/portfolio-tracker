import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st


def visualisation_tab(
    connection: duckdb.DuckDBPyConnection,
    load_portfolio_position_gain_loss: callable,
) -> None:
    st.subheader("Visualisation")
    df: pd.DataFrame = load_portfolio_position_gain_loss(connection)
    if df.empty:
        st.info("No positions yet. Add some in the Positions tab.")
        return

    # Selection, filtering, and aggregations
    all_holders = sorted(df["holder"].dropna().unique().tolist())
    f1, f2, f3, f4 = st.columns([3, 1.5, 1, 0.5])
    with f1:
        selected_holders = st.multiselect(
            "Holders to include",
            options=all_holders,
            default=all_holders,
            help="Untick a holder to exclude their positions from everything below.",
        )
    with f2:
        top_n = st.number_input(
            "Top N positions to show",
            min_value=1,
            max_value=50,
            value=15,
            step=1,
        )
    with f3:
        display_mode = st.radio(
            "Display Mode",
            options=["$", "%"],
            horizontal=True,
            help="% of Portfolio is relative to total open market value.",
        )
    with f4:
        ascending_order = st.toggle(
            label="Asc",
            help="Whether to sort the positions in ascending order based on market value.",
        )
    pct_mode = display_mode == "%"

    # Filter the data based on options
    holder_mask = df["holder"].isin(selected_holders)
    df_filtered = df.loc[holder_mask, :].copy()
    all_positions_gain_loss, benchmark_gain_loss = (
        df_filtered["gain_loss"].sum(),
        df_filtered["benchmark_gain_loss"].sum(),
    )
    if df_filtered.empty:
        st.info("No positions for the selected holder(s).")
        return

    # Handle closed positions, set cost_basis and market_value to 0 but leave gain loss intact for closed positions
    open_position_mask = df_filtered["is_open_position"].fillna(False)
    df_filtered.loc[~open_position_mask, ["cost_basis", "market_value"]] = 0
    open_positions_count = int(open_position_mask.sum())

    # Get metrics and breakdowns
    total_open_cost_basis, total_open_value = (
        df_filtered["cost_basis"].sum(),
        df_filtered["market_value"].sum(),
    )
    df_breakdown = (
        df_filtered.groupby("ticker", as_index=False)[
            ["cost_basis", "gain_loss", "market_value"]
        ]
        .sum()
        .sort_values("market_value", ascending=ascending_order)
    )

    # Metric display
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Open Cost Basis", f"${total_open_cost_basis:,.0f}")
    k2.metric("Open Market Value", f"${total_open_value:,.0f}")
    k3.metric("Open Positions", open_positions_count)
    k4.metric("Distinct tickers", df_filtered["ticker"].nunique())

    k1.metric("All Position Gain/Loss", f"${all_positions_gain_loss:,.0f}")
    k2.metric("Benchmark Gain/Loss", f"${benchmark_gain_loss:,.0f}")
    st.divider()

    # Position Chart
    label = "% of Portfolio" if pct_mode else "Portfolio value ($)"
    st.markdown(
        f"#### Top {top_n} ticker positions by {label}",
        help="Gain/Loss includes all open and closed positions",
    )

    df_top = df_breakdown.head(top_n).copy()
    if pct_mode:
        denominator = total_open_value if total_open_value != 0 else 1
        df_top["open_cost_basis"] = df_top["cost_basis"] / denominator * 100
        df_top["gain_loss"] = df_top["gain_loss"] / denominator * 100
        text_auto = ".1f"
    else:
        df_top["open_cost_basis"] = df_top["cost_basis"]
        text_auto = ".2s"

    df_plot = df_top.melt(
        id_vars="ticker",
        value_vars=["open_cost_basis", "gain_loss"],
        var_name="component",
        value_name="value",
    )
    df_plot["component"] = df_plot["component"].map(
        {
            "open_cost_basis": "Open Cost Basis",
            "gain_loss": "All Gain/Loss",
        }
    )

    fig3 = px.bar(
        df_plot,
        x="value",
        y="ticker",
        color="component",
        orientation="h",
        text_auto=text_auto,
        category_orders={
            "component": ["Open Cost Basis", "All Gain/Loss"],
        },
    )
    fig3.update_layout(barmode="relative", legend_title_text=None)
    fig3.update_xaxes(title=label)
    fig3.update_yaxes(categoryorder="total ascending", title=None)
    st.plotly_chart(fig3, width="content")

    st.divider()
