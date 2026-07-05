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
    f1, f2, f3 = st.columns([2, 1, 1])
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
            "Show as",
            options=["$ Absolute", "% of Portfolio"],
            horizontal=True,
        )
    pct_mode = display_mode == "% of Portfolio"

    holder_mask = df["holder"].isin(selected_holders)
    df_filtered = df.loc[holder_mask, :]
    all_positions_gain_loss, benchmark_gain_loss = (
        df_filtered["gain_loss"].sum(),
        df_filtered["benchmark_gain_loss"].sum(),
    )
    if df_filtered.empty:
        st.info("No positions for the selected holder(s).")
        return

    open_position_mask = df_filtered["is_open_position"]
    df_filtered = df_filtered.loc[open_position_mask, :]
    total_open_cost_basis, total_open_value = (
        df_filtered["cost_basis"].sum(),
        df_filtered["market_value"].sum(),
    )
    df_breakdown = (
        df_filtered.groupby("ticker")["market_value"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    # Metrics
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Open Cost Basis", f"${total_open_cost_basis:,.0f}")
    k2.metric("Open Market Value", f"${total_open_value:,.0f}")
    k3.metric("Open Positions", len(df_filtered))
    k4.metric("Distinct tickers", df_filtered["ticker"].nunique())

    k1.metric("All Position Gain/Loss", f"${all_positions_gain_loss:,.0f}")
    k2.metric("Benchmark Gain/Loss", f"${benchmark_gain_loss:,.0f}")
    st.divider()

    # Position Chart
    label = "% of Portfolio" if pct_mode else "Portfolio value ($)"
    st.markdown(f"#### Top {top_n} ticker positions by {label}")

    if pct_mode:
        df_breakdown["market_value"] = (
            df_breakdown["market_value"] / total_open_value * 100
        )
        fig3 = px.bar(
            df_breakdown.head(top_n),
            x="market_value",
            y="ticker",
            orientation="h",
            text_auto=".1f",
        )
    else:
        fig3 = px.bar(
            df_breakdown.head(top_n),
            x="market_value",
            y="ticker",
            orientation="h",
            text_auto=".2s",
        )
    fig3.update_xaxes(title=label)
    fig3.update_yaxes(categoryorder="total ascending", title=None)
    st.plotly_chart(fig3, width="content")

    st.divider()

    # c1, c2 = st.columns(2)
    # with c1:
    #     by_asset = (
    #         df.groupby("asset_class")["market_value"].sum()
    #         .sort_values(ascending=False).reset_index()
    #     )
    #     fig = px.pie(
    #         by_asset, names="asset_class", values="market_value", hole=0.55,
    #         title="Allocation by Asset Class",
    #     )
    #     fig.update_traces(textinfo="percent+label")
    #     st.plotly_chart(fig, width="content")

    # with c2:
    #     by_sector = (
    #         df.groupby("sector")["market_value"].sum()
    #         .sort_values(ascending=False).reset_index()
    #     )
    #     fig2 = px.pie(
    #         by_sector, names="sector", values="market_value", hole=0.55,
    #         title="Allocation by Sector",
    #     )
    #     fig2.update_traces(textinfo="percent+label")
    #     st.plotly_chart(fig2, width="content")
