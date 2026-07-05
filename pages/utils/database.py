import datetime as dt
from zoneinfo import ZoneInfo

import duckdb
import numpy as np
import pandas as pd
import streamlit as st

COLUMNS = [
    "id",
    "holder",
    "account",
    "sym",
    "shares",
    "buy_date",
    "buy_price",
    "close_price",
    "close_date",
]
EDIT_FIELDS = COLUMNS[1:]
DB_COLUMNS = COLUMNS + ["last_edited"]


@st.cache_resource
def get_connection() -> duckdb.DuckDBPyConnection:
    token = st.secrets["motherduck"]["token"]
    db = st.secrets["motherduck"].get("database")
    con = duckdb.connect(f"md:{db}?motherduck_token={token}")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS raw.portfolio_positions (
            id          INTEGER PRIMARY KEY,
            holder      VARCHAR,
            account     VARCHAR,
            sym         VARCHAR,
            shares      DOUBLE,
            buy_date    DATE,
            buy_price   DOUBLE,
            close_price DOUBLE,
            close_date  DATE,
            last_edited TIMESTAMPTZ
        )
        """
    )
    return con


def load_positions(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.execute(
        f"SELECT {', '.join(DB_COLUMNS)} FROM raw.portfolio_positions ORDER BY id"
    ).df()
    if df.empty:
        df = pd.DataFrame(columns=DB_COLUMNS)
    for c in ("buy_date", "close_date", "last_edited"):
        df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in ("shares", "buy_price", "close_price"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["id"] = pd.to_numeric(df["id"], errors="coerce").astype("Int64")
    for c in ("holder", "account", "sym"):
        df[c] = df[c].astype("string")
    return df


def _assign_ids(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assigns unique IDs to rows in the DataFrame. If a row already has an ID, it is preserved.
    If a row does not have an ID, a new unique ID is assigned. The function ensures that IDs are unique and sequential, starting from 1.
    """
    df = df.copy()
    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    used_ids = set(df["id"].dropna().astype(int))
    next_id = (max(used_ids) + 1) if used_ids else 1
    new_ids = []
    for id in df["id"]:
        if pd.isna(id):
            while next_id in used_ids:
                next_id += 1
            used_ids.add(next_id)
            new_ids.append(next_id)
            next_id += 1
        else:
            new_ids.append(int(id))
    df["id"] = new_ids
    return df


def save_positions(con: duckdb.DuckDBPyConnection, df_edited: pd.DataFrame):
    df = _assign_ids(df_edited)

    # Retrieve the old data from the database to compare and determine which rows have changed
    df_old = con.execute(
        f"SELECT {', '.join(DB_COLUMNS)} FROM raw.portfolio_positions"
    ).df()
    old_row_data_lookup = (
        {int(r["id"]): r for _, r in df_old.iterrows()} if not df_old.empty else {}
    )
    now = dt.datetime.now(tz=ZoneInfo("UTC"))

    def _update_timestamp(row):
        old_data_row = old_row_data_lookup.get(int(row["id"]))
        if old_data_row is None:
            # Update if the row is new (not present in the old data)
            return now
        for field in EDIT_FIELDS:
            current_data, old_data_value = row[field], old_data_row[field]
            if pd.isna(current_data) and pd.isna(old_data_value):
                continue
            if current_data != old_data_value:
                # Update if any of the fields have changed
                return now
        return old_data_row["last_edited"]

    df["last_edited"] = df.apply(_update_timestamp, axis=1)
    df["last_edited"] = pd.to_datetime(df["last_edited"], errors="coerce", utc=True)

    df = df[DB_COLUMNS]

    # Full reconcile: editor grid as the source of truth
    con.register("edited_positions", df)
    con.execute("BEGIN")
    try:
        con.execute("DELETE FROM raw.portfolio_positions")
        con.execute(
            f"INSERT INTO raw.portfolio_positions SELECT {', '.join(DB_COLUMNS)} FROM edited_positions"
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.unregister("edited_positions")


def apply_stock_split(
    df: pd.DataFrame, symbol: str, split_ratio: float
) -> pd.DataFrame:
    """
    Applies a stock split to the given DataFrame for the specified symbol and split ratio.
    The function adjusts the number of shares, buy price, and close price accordingly.
    Parameters:
    - df: The DataFrame containing the stock positions.
    - symbol: The stock symbol for which the split is to be applied.
    - split_ratio: The ratio of the stock split (e.g., 2.0 for a 2-for-1 split).
    Returns:
    - A new DataFrame with the stock split applied.
    """
    if split_ratio <= 0:
        raise ValueError("Split ratio must be greater than zero.")

    out = df.copy()
    mask = out["sym"] == symbol

    out.loc[mask, "shares"] = out.loc[mask, "shares"] * split_ratio
    out.loc[mask, "buy_price"] = out.loc[mask, "buy_price"] / split_ratio
    out.loc[mask, "close_price"] = np.where(
        out.loc[mask, "close_price"].notna(),
        out.loc[mask, "close_price"] / split_ratio,
        out.loc[mask, "close_price"],
    )
    return out
