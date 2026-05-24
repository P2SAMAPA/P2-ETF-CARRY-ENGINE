"""
Cross-Asset Carry Engine
========================
Implements the Koijen et al. (2018) carry framework adapted for ETFs.

Carry definition:
-----------------
"Carry" is the expected return of an asset assuming prices stay constant.
For each ETF type we use the most informative available proxy:

  FI ETFs (TLT, VCIT, LQD, HYG):
      carry = rolling_yield_proxy - risk_free_rate
      yield proxy = annualised rolling return over `window` days
      (since we lack direct bond yield data per ETF, we use
      rolling total return as a yield approximation — this is
      consistent with the Koijen et al. bond carry literature)

  REIT ETFs (VNQ):
      carry = same rolling yield proxy minus risk free (high dividend)

  Commodity ETFs (GLD, SLV):
      carry = roll yield proxy = spot_return(1m) - spot_return(12m)
      Negative roll = backwardation (positive carry for long position)
      Positive roll = contango (negative carry)
      Approximated as: -(r_12m - r_1m) normalised

  Equity ETFs (SPY, XLK, etc.):
      carry = earnings yield proxy = -(12m price return - risk_free)
      High recent price run-up → expensive → low earnings yield → low carry
      This is a value/carry signal consistent with Asness et al. (2013)

Composite score:
----------------
All three carry components are computed, cross-sectionally z-scored
per window, then blended by weight and re-z-scored.

References:
-----------
Koijen, R., Moskowitz, T., Pedersen, L., Vrugt, E. (2018).
    Carry. Journal of Financial Economics.
Asness, C., Moskowitz, T., Pedersen, L. (2013).
    Value and Momentum Everywhere. Journal of Finance.
"""

import numpy as np
import pandas as pd
from scipy.stats import zscore as sp_zscore


# ── Helper ────────────────────────────────────────────────────────────────────

def _xsz(series: pd.Series) -> pd.Series:
    """Cross-sectional z-score of a Series, robust to short series."""
    s = series.dropna()
    if len(s) < 2:
        return series
    mu, sd = s.mean(), s.std()
    if sd < 1e-10:
        return pd.Series(0.0, index=series.index)
    return (series - mu) / sd


def _rolling_return(prices: pd.DataFrame, window: int) -> pd.DataFrame:
    """Log return over `window` days, annualised."""
    log_ret = np.log(prices / prices.shift(window))
    return log_ret * (252 / window)   # annualise


# ── Carry components ──────────────────────────────────────────────────────────

def fi_carry(prices: pd.DataFrame,
             tickers: list,
             risk_free: pd.Series,
             window: int) -> pd.Series:
    """
    FI / REIT carry: rolling annualised return minus risk-free rate.
    Higher value = more income carry = higher score.
    """
    avail = [t for t in tickers if t in prices.columns]
    if not avail:
        return pd.Series(dtype=float)

    roll_ret = _rolling_return(prices[avail], window)

    # Align risk-free rate
    rf = risk_free.reindex(roll_ret.index).ffill() / 100.0   # percent → decimal

    carry = roll_ret.subtract(rf, axis=0)
    return carry.iloc[-1].dropna()


def commodity_carry(prices: pd.DataFrame,
                    tickers: list,
                    window: int) -> pd.Series:
    """
    Commodity roll-yield proxy: negative of (long-term return - short-term return).
    Backwardation (short > long) = positive carry for long position.
    Window controls the short-term leg; long-term is 4x window.
    """
    avail = [t for t in tickers if t in prices.columns]
    if not avail:
        return pd.Series(dtype=float)

    short_win = max(window, 21)
    long_win  = min(short_win * 4, 252)

    r_short = _rolling_return(prices[avail], short_win)
    r_long  = _rolling_return(prices[avail], long_win)

    # Roll yield ≈ -(r_long - r_short): if price has risen more over long
    # horizon than short horizon, futures curve is in contango → negative carry
    roll_yield = -(r_long - r_short)
    return roll_yield.iloc[-1].dropna()


def equity_carry(prices: pd.DataFrame,
                 tickers: list,
                 risk_free: pd.Series,
                 window: int) -> pd.Series:
    """
    Equity earnings yield proxy: -(annualised 12m return - risk_free).
    High recent returns → expensive → low carry.
    We use 252-day return regardless of window to approximate trailing earnings yield,
    then cross-sectionally z-score to remove level bias.
    """
    avail = [t for t in tickers if t in prices.columns]
    if not avail:
        return pd.Series(dtype=float)

    r_12m = _rolling_return(prices[avail], 252)
    rf    = risk_free.reindex(r_12m.index).ffill() / 100.0

    excess_ret = r_12m.subtract(rf, axis=0)
    # Negate: high excess return over past year = lower earnings yield = lower carry
    carry = -excess_ret
    return carry.iloc[-1].dropna()


# ── Composite score ───────────────────────────────────────────────────────────

def compute_carry_scores(prices: pd.DataFrame,
                         risk_free: pd.Series,
                         fi_tickers: list,
                         reit_tickers: list,
                         commodity_tickers: list,
                         equity_tickers: list,
                         window: int,
                         w_yield: float = 0.50,
                         w_roll:  float = 0.30,
                         w_eq:    float = 0.20) -> pd.Series:
    """
    Compute composite carry score for all ETFs.

    Parameters
    ----------
    prices         : DataFrame of ETF price levels, indexed by date.
    risk_free      : Series of annualised 3M T-Bill rate (percent), indexed by date.
    fi_tickers     : FI and REIT ETF list.
    reit_tickers   : REIT-specific ETFs (dividend carry).
    commodity_tickers : Commodity ETF list.
    equity_tickers : Equity ETF list.
    window         : lookback window (days).
    w_yield/w_roll/w_eq : blend weights.

    Returns
    -------
    pd.Series {ticker: composite_carry_score}, cross-sectionally z-scored.
    """
    if len(prices) < max(window, 252) + 5:
        return pd.Series(dtype=float)

    all_scores = {}

    # FI + REIT carry (yield minus risk-free)
    fi_all = fi_tickers + reit_tickers
    fi_raw = fi_carry(prices, fi_all, risk_free, window)
    fi_z   = _xsz(fi_raw)
    for t, v in fi_z.items():
        all_scores[t] = all_scores.get(t, 0.0) + w_yield * v

    # Commodity roll-yield carry
    com_raw = commodity_carry(prices, commodity_tickers, window)
    com_z   = _xsz(com_raw)
    for t, v in com_z.items():
        all_scores[t] = all_scores.get(t, 0.0) + w_roll * v

    # Equity earnings-yield carry
    eq_raw = equity_carry(prices, equity_tickers, risk_free, window)
    eq_z   = _xsz(eq_raw)
    for t, v in eq_z.items():
        all_scores[t] = all_scores.get(t, 0.0) + w_eq * v

    composite = pd.Series(all_scores).dropna()
    if len(composite) < 2:
        return composite

    # Final cross-sectional z-score
    return _xsz(composite)


def compute_carry_scores_universe(prices: pd.DataFrame,
                                  risk_free: pd.Series,
                                  tickers: list,
                                  window: int,
                                  fi_tickers: list,
                                  reit_tickers: list,
                                  commodity_tickers: list,
                                  equity_tickers: list,
                                  w_yield: float = 0.50,
                                  w_roll:  float = 0.30,
                                  w_eq:    float = 0.20) -> pd.Series:
    """
    Wrapper that filters to only tickers present in this universe.
    """
    fi_u    = [t for t in fi_tickers        if t in tickers]
    reit_u  = [t for t in reit_tickers      if t in tickers]
    com_u   = [t for t in commodity_tickers if t in tickers]
    eq_u    = [t for t in equity_tickers    if t in tickers]

    return compute_carry_scores(
        prices, risk_free,
        fi_u, reit_u, com_u, eq_u,
        window, w_yield, w_roll, w_eq,
    )
