"""ETL for the UCI "Online Retail" dataset.

Source: UCI Machine Learning Repository, dataset #352.
  https://archive.ics.uci.edu/dataset/352/online+retail
  Direct download: https://archive.ics.uci.edu/static/public/352/online+retail.zip
  License: CC BY 4.0 (Creative Commons Attribution 4.0 International)
  Citation: Chen, Daqing. "Online Retail." UCI Machine Learning Repository,
            2015. https://doi.org/10.24432/C5BW33
  Content: 541,909 UK online-retailer transactions, 2010-12-01 to 2011-12-09.

Downloads + caches the raw file once, then aggregates to a daily revenue
time series (cancellations and non-positive quantity/price rows removed),
cached as parquet so subsequent app restarts don't re-parse the 540k-row
spreadsheet.
"""
import os
import zipfile

import pandas as pd
import requests

SOURCE_URL = "https://archive.ics.uci.edu/static/public/352/online+retail.zip"


def ensure_online_retail_daily(data_dir: str) -> pd.Series:
    raw_dir = os.path.join(data_dir, "raw")
    processed_dir = os.path.join(data_dir, "processed")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)

    parquet_path = os.path.join(processed_dir, "online_retail_daily.parquet")
    if os.path.exists(parquet_path):
        return pd.read_parquet(parquet_path)["revenue"]

    zip_path = os.path.join(raw_dir, "online_retail.zip")
    xlsx_path = os.path.join(raw_dir, "Online Retail.xlsx")

    if not os.path.exists(xlsx_path):
        if not os.path.exists(zip_path):
            resp = requests.get(SOURCE_URL, timeout=180)
            resp.raise_for_status()
            with open(zip_path, "wb") as f:
                f.write(resp.content)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(raw_dir)

    df = pd.read_excel(xlsx_path)
    df = df[~df["InvoiceNo"].astype(str).str.startswith("C")]  # drop cancellations
    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]
    df["revenue"] = df["Quantity"] * df["UnitPrice"]
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])

    daily = df.set_index("InvoiceDate")["revenue"].resample("D").sum()
    daily = daily.asfreq("D").fillna(0.0)
    daily.to_frame("revenue").to_parquet(parquet_path)
    return daily
