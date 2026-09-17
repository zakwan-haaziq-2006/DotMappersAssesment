# app/database.py

import pandas as pd
import sqlite3
import os

DB_PATH = "tickets.db"
CSV_PATH = "data/support_tickets.csv"


def load_data():
    # reads the csv and dumps it into sqlite
    df = pd.read_csv(CSV_PATH)
    df["created_at"] = pd.to_datetime(df["created_at"])

    conn = sqlite3.connect(DB_PATH)
    df.to_sql("tickets", conn, if_exists="replace", index=False)
    conn.close()

    print("loaded", len(df), "tickets into", DB_PATH)


def get_connection():
    # just gives you a connection to the already-loaded db
    if not os.path.exists(DB_PATH):
        load_data()
    return sqlite3.connect(DB_PATH)


def get_dataframe():
    # sometimes we want the raw dataframe, not a db connection
    # (anomaly rules use this)
    df = pd.read_csv(CSV_PATH)
    df["created_at"] = pd.to_datetime(df["created_at"])
    return df


if __name__ == "__main__":
    # run this file directly to test it: python app/database.py
    load_data()
    conn = get_connection()
    result = pd.read_sql_query("SELECT COUNT(*) as total FROM tickets", conn)
    print(result)
    conn.close()