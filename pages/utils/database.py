import datetime as dt
from zoneinfo import ZoneInfo

import duckdb
import pandas as pd
import streamlit as st

COLUMNS = [
    "id", "holder", "account", "sym", "shares",
    "buy_date", "buy_price", "close_price", "close_date",
]
EDIT_FIELDS = COLUMNS[1:]
DB_COLUMNS = COLUMNS + ["last_edited"]


@st.cache_resource
def get_connection():
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
            last_edited TIMESTAMP
        )
        """
    )
    return con


def load_positions(con) -> pd.DataFrame:
    df = con.execute(f"SELECT {', '.join(DB_COLUMNS)} FROM raw.portfolio_positions ORDER BY id").df()
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


def save_positions(con, edited: pd.DataFrame):
    df = edited.copy()

    # assign ids to new rows (null/blank id)
    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    used = set(df["id"].dropna().astype(int))
    next_id = (max(used) + 1) if used else 1
    new_ids = []
    for v in df["id"]:
        if pd.isna(v):
            while next_id in used:
                next_id += 1
            used.add(next_id)
            new_ids.append(next_id)
            next_id += 1
        else:
            new_ids.append(int(v))
    df["id"] = new_ids

    old = con.execute(f"SELECT {', '.join(DB_COLUMNS)} FROM raw.portfolio_positions").df()
    old_by_id = {int(r["id"]): r for _, r in old.iterrows()} if not old.empty else {}
    now = dt.datetime.now(tz=ZoneInfo("Asia/Singapore"))

    def stamp(row):
        prev = old_by_id.get(int(row["id"]))
        if prev is None:
            return now
        for f in EDIT_FIELDS:
            a, b = row[f], prev[f]
            if pd.isna(a) and pd.isna(b):
                continue
            if a != b:
                return now
        return prev["last_edited"]

    df["last_edited"] = df.apply(stamp, axis=1)
    df["last_edited"] = pd.to_datetime(df["last_edited"], errors="coerce")

    df = df[DB_COLUMNS]

    # full reconcile: editor grid is source of truth
    con.register("edited_positions", df)
    con.execute("BEGIN")
    try:
        con.execute("DELETE FROM raw.portfolio_positions")
        con.execute(f"INSERT INTO raw.portfolio_positions SELECT {', '.join(DB_COLUMNS)} FROM edited_positions")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.unregister("edited_positions")
