# app/anomalies.py

import pandas as pd
from app.database import get_dataframe


def get_stale_tickets(df, ref_date):
    # rule 1: high/critical priority tickets still open/escalated
    # and been sitting for more than 24 hours
    stale_list = []

    for i, row in df.iterrows():
        if row["status"] not in ["Open", "Escalated"]:
            continue
        if row["priority"] not in ["High", "Critical"]:
            continue

        hours_open = (ref_date - row["created_at"]).total_seconds() / 3600
        if hours_open > 24:
            stale_list.append(row)

    result = pd.DataFrame(stale_list)
    if len(result) > 0:
        result["reason"] = "stale_high_priority"
    return result


def get_slow_tickets(df):
    # rule 2: resolved tickets that took way longer than usual for their category
    resolved = df[df["status"] == "Resolved"]

    slow_list = []
    for cat in resolved["category"].unique():
        cat_tickets = resolved[resolved["category"] == cat]
        cutoff = cat_tickets["resolution_time_hrs"].quantile(0.90)

        slow_cat = cat_tickets[cat_tickets["resolution_time_hrs"] > cutoff]
        slow_list.append(slow_cat)

    result = pd.concat(slow_list)
    result["reason"] = "slow_resolution"
    return result


def get_all_anomalies():
    # this is what the API will actually call
    df = get_dataframe()
    ref_date = df["created_at"].max()

    stale = get_stale_tickets(df, ref_date)
    slow = get_slow_tickets(df)

    combined = pd.concat([stale, slow])
    cols = ["ticket_id", "priority", "status", "category", "reason"]
    return combined[cols].to_dict(orient="records")


if __name__ == "__main__":
    # run this file directly to test it: python app/anomalies.py
    anomalies = get_all_anomalies()
    print("found", len(anomalies), "anomalies")
    for a in anomalies[:5]:
        print(a)