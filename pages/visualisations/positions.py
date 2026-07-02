import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st


def visualisation_tab(
    connection: duckdb.DuckDBPyConnection,
    load_positions: callable,  # Change to load the fct table with latest prices instead
) -> None:
    st.subheader("Visualisation")
    df: pd.DataFrame = load_positions(connection)
    if df.empty:
        st.info("No positions yet. Add some in the Positions tab.")
        return

    df_open_positions = df[df["close_date"].isna()].copy()
    if df_open_positions.empty:
        st.info("No open positions to visualise.")
        return

    # Holder and pct selection
    all_holders = sorted(df_open_positions["holder"].dropna().unique().tolist())
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

    df_open_positions = df_open_positions[
        df_open_positions["holder"].isin(selected_holders)
    ]
    if df_open_positions.empty:
        st.info("No open positions for the selected holder(s).")
        return

    df_open_positions["open_market_value"] = (
        df_open_positions["shares"] * df_open_positions["buy_price"]
    )
    # df_open_positions["asset_class"] = df_open_positions["asset_class"].fillna("Unclassified")
    # df_open_positions["sector"] = df_open_positions["sector"].fillna("Unclassified")
    total_value = df_open_positions["open_market_value"].sum()

    # Metrics
    k1, k2, k3, k4 = st.columns(4)
    if pct_mode:
        k1.metric("Open Market Value", "100%", help=f"= ${total_value:,.0f}")
    else:
        k1.metric("Open Market Value", f"${total_value:,.0f}")
    k2.metric("Open Positions", len(df_open_positions))
    k3.metric("Distinct Symbols", df_open_positions["sym"].nunique())
    k4.metric("Holders", df_open_positions["holder"].nunique())
    st.divider()

    # Position Chart
    label = "% of Portfolio" if pct_mode else "Portfolio value ($)"
    st.markdown(f"#### Top {top_n} open positions by {label}")
    df_open_positions_breakdown = (
        df_open_positions.groupby("sym")["open_market_value"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    if pct_mode:
        df_open_positions_breakdown["open_market_value"] = (
            df_open_positions_breakdown["open_market_value"] / total_value * 100
        )
        fig3 = px.bar(
            df_open_positions_breakdown.head(top_n),
            x="open_market_value",
            y="sym",
            orientation="h",
            text_auto=".1f",
        )
    else:
        fig3 = px.bar(
            df_open_positions_breakdown.head(top_n),
            x="open_market_value",
            y="sym",
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
    #         df_open_positions.groupby("asset_class")["open_market_value"].sum()
    #         .sort_values(ascending=False).reset_index()
    #     )
    #     fig = px.pie(
    #         by_asset, names="asset_class", values="open_market_value", hole=0.55,
    #         title="Allocation by Asset Class",
    #     )
    #     fig.update_traces(textinfo="percent+label")
    #     st.plotly_chart(fig, width="content")

    # with c2:
    #     by_sector = (
    #         df_open_positions.groupby("sector")["open_market_value"].sum()
    #         .sort_values(ascending=False).reset_index()
    #     )
    #     fig2 = px.pie(
    #         by_sector, names="sector", values="open_market_value", hole=0.55,
    #         title="Allocation by Sector",
    #     )
    #     fig2.update_traces(textinfo="percent+label")
    #     st.plotly_chart(fig2, width="content")
