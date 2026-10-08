import streamlit as st

from pages.utils.database import (
    apply_stock_split,
    get_connection,
    load_portfolio_position_gain_loss,
    load_raw_positions,
    save_positions,
)
from pages.utils.login import check_login
from pages.visualisations.positions import visualisation_tab


# --- Tabs ------------------------------------------------------------------
def positions_tab(con):
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Positions")
        st.caption("Edit cells, add rows, or delete rows.")
    with col2, st.container(horizontal=True, horizontal_alignment="right"):
        if st.button(
            "🔄 Refresh",
            type="primary",
            use_container_width=False,
            help="Clear cache and refresh data",
        ):
            st.cache_data.clear()
            st.rerun()

    if "df_split_preview" not in st.session_state:
        st.session_state.df_split_preview = None
    if "split_applied" not in st.session_state:
        st.session_state.split_applied = False

    df = load_raw_positions(con)

    df_edited = st.data_editor(
        df,
        num_rows="dynamic",
        width="stretch",
        key="editor",
        column_config={
            "id": st.column_config.NumberColumn(
                "id", disabled=True, help="auto-assigned"
            ),
            "holder": st.column_config.TextColumn("holder", help="who owns the stock"),
            "shares": st.column_config.NumberColumn("shares", format="%.4f"),
            "buy_date": st.column_config.DateColumn("buy_date"),
            "buy_price": st.column_config.NumberColumn("buy_price", format="%.2f"),
            "close_price": st.column_config.NumberColumn("close_price", format="%.2f"),
            "close_date": st.column_config.DateColumn("close_date"),
        },
    )
    st.divider()

    if st.toggle("Show stock split options", value=False):
        with st.form("stock_split_form"):
            selected_symbol = st.selectbox(
                "Stock Symbol", options=sorted(df_edited["sym"].dropna().unique())
            )
            split_ratio = st.number_input(
                "Split Ratio", min_value=0.0001, step=0.1, format="%.4f", value=2.0
            )
            preview_submit = st.form_submit_button("Perform stock split")

        if preview_submit:
            try:
                st.session_state.df_split_preview = apply_stock_split(
                    df=df_edited, symbol=selected_symbol, split_ratio=split_ratio
                )
                st.session_state.split_applied = True
                st.success(
                    f"Preview generated for {selected_symbol} at ratio {split_ratio}."
                )
            except Exception as e:
                st.session_state.df_split_preview = None
                st.session_state.split_applied = False
                st.error(f"Stock split failed: {e}")

    if st.session_state.split_applied and st.session_state.df_split_preview is not None:
        st.info("Before")
        st.dataframe(df_edited[df_edited["sym"] == selected_symbol], width="stretch")
        st.info("After. Preview only. Review below and save to MotherDuck.")
        df_preview = st.session_state.df_split_preview[
            st.session_state.df_split_preview["sym"] == selected_symbol
        ]
        st.dataframe(df_preview, width="stretch")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 Save preview to MotherDuck", type="primary"):
                try:
                    save_positions(con, st.session_state.df_split_preview)
                    st.session_state.df_split_preview = None
                    st.session_state.split_applied = False
                    st.success(
                        "Saved. Remember to rerun price data to get split adjusted prices.",
                        icon="✅",
                    )
                except Exception as e:
                    st.error(f"Save failed: {e}")

        with col2:
            if st.button("Discard preview"):
                st.session_state.df_split_preview = None
                st.session_state.split_applied = False
                st.rerun()
    else:
        if st.button("💾 Save current edits to MotherDuck", type="primary"):
            try:
                save_positions(con, df_edited)
                st.success("Saved.", icon="✅")
            except Exception as e:
                st.error(f"Save failed: {e}")


# --- Main ------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Stock Positions", layout="wide")
    if not check_login():
        return

    con = get_connection()

    st.title("📈 Stock Positions")
    with st.sidebar:
        st.write(f"Signed in as **{st.secrets['auth']['username']}**")
        if st.button("Sign out"):
            st.session_state.clear()
            st.rerun()

    tab_pos, tab_viz = st.tabs(["Positions", "Visualisation"])
    with tab_pos:
        positions_tab(con)
    with tab_viz:
        visualisation_tab(con, load_portfolio_position_gain_loss)


if __name__ == "__main__":
    main()
