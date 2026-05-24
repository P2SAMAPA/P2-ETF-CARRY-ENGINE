import pandas as pd
import numpy as np
from huggingface_hub import hf_hub_download
import config


def load_master_data() -> pd.DataFrame:
    path = hf_hub_download(
        repo_id=config.DATA_REPO,
        filename="master_data.parquet",
        repo_type="dataset",
        token=config.HF_TOKEN,
    )
    df = pd.read_parquet(path)
    if df.index.name != "date":
        df.index.name = "date"
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
    df.index = pd.to_datetime(df.index)
    df.sort_index(inplace=True)
    return df


def prepare_prices(df: pd.DataFrame, tickers: list) -> pd.DataFrame:
    """Return price levels (not returns) for carry computation."""
    prices = pd.DataFrame(index=df.index)
    for ticker in tickers:
        if ticker in df.columns:
            col = df[ticker]
            if not col.isna().all():
                prices[ticker] = col.ffill()
    return prices.dropna(how="all")


def get_risk_free(df: pd.DataFrame) -> pd.Series:
    """Return 3M T-Bill rate series (annualised %)."""
    col = config.RISK_FREE_COL
    if col not in df.columns:
        # Fallback: return flat 5% series
        return pd.Series(5.0, index=df.index)
    return df[col].ffill().fillna(5.0)
