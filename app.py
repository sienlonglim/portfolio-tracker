import streamlit as st

from pages.utils.database import (
    get_connection,
    load_positions,
    save_positions
)
from pages.utils.login import check_login


# --- Tabs ------------------------------------------------------------------
def positions_tab(con):
    st.subheader("Positions")
    st.caption("Edit cells, add rows, or delete rows.")

    df = load_positions(con)

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        width="stretch",
        key="editor",
        column_config={
            "id": st.column_config.NumberColumn("id", disabled=True, help="auto-assigned"),
            "holder": st.column_config.TextColumn("holder", help="who owns the stock"),
            "shares": st.column_config.NumberColumn("shares", format="%.4f"),
            "buy_date": st.column_config.DateColumn("buy_date"),
            "buy_price": st.column_config.NumberColumn("buy_price", format="%.2f"),
            "close_price": st.column_config.NumberColumn("close_price", format="%.2f"),
            "close_date": st.column_config.DateColumn("close_date"),
        },
    )

    if st.button("💾 Save to MotherDuck", type="primary"):
        try:
            save_positions(con, edited)
            st.success("Saved.")
            st.rerun()
        except Exception as e:
            st.error(f"Save failed: {e}")


def visualisation_tab(con):
    st.subheader("Visualisation")
    st.info("Coming soon. Charts go here.")


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
        visualisation_tab(con)


if __name__ == "__main__":
    main()
