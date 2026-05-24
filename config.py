import os

HF_TOKEN    = os.environ.get("HF_TOKEN", "")
DATA_REPO   = "P2SAMAPA/fi-etf-macro-signal-master-data"
OUTPUT_REPO = "P2SAMAPA/p2-etf-carry-engine-results"

UNIVERSES = {
    "FI_COMMODITIES": ["TLT", "VCIT", "LQD", "HYG", "VNQ", "GLD", "SLV"],
    "EQUITY_SECTORS": [
        "SPY", "QQQ", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY",
        "XLP", "XLU", "GDX", "XME", "IWF", "XSD", "XBI", "IWM", "IWD", "IWO"
    ],
    "COMBINED": [
        "TLT", "VCIT", "LQD", "HYG", "VNQ", "GLD", "SLV",
        "SPY", "QQQ", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY",
        "XLP", "XLU", "GDX", "XME", "IWF", "XSD", "XBI", "IWM", "IWD", "IWO"
    ],
}

# ── Carry proxy definitions ────────────────────────────────────────────────────
# For each ETF, the carry signal is derived from:
#   FI ETFs:         yield spread vs 3M T-Bill (DTB3)
#   Commodity ETFs:  roll yield proxy (price momentum slope vs spot)
#   Equity ETFs:     earnings yield proxy (1 / trailing P/E approximated via
#                    12m price return momentum — higher price = lower E/P = lower carry)
#
# We use three sub-signals and blend them by ETF type:
#   carry_fi     = (ETF_yield_proxy - risk_free_rate)  normalised
#   carry_roll   = negative of 12m return (high = expensive = low roll carry)
#   carry_equity = dividend yield proxy (negative of 12m total return minus risk free)

FI_ETFS        = ["TLT", "VCIT", "LQD", "HYG"]     # duration / credit carry
REIT_ETFS      = ["VNQ"]                             # dividend carry
COMMODITY_ETFS = ["GLD", "SLV"]                     # roll yield carry
EQUITY_ETFS    = [
    "SPY", "QQQ", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY",
    "XLP", "XLU", "GDX", "XME", "IWF", "XSD", "XBI", "IWM", "IWD", "IWO"
]

# Risk-free rate column in master data (3M T-Bill annualised %)
RISK_FREE_COL = "DTB3"

# Rolling windows for carry estimation
WINDOWS = [21, 63, 126, 252]

# Blend weights for composite carry score
W_YIELD_CARRY  = 0.50    # yield / income carry (FI, REIT)
W_ROLL_CARRY   = 0.30    # roll yield / momentum carry (commodities)
W_EQUITY_CARRY = 0.20    # equity earnings yield carry

# Score lookback for z-scoring
SCORE_LOOKBACK = 21

TOP_N = 3
