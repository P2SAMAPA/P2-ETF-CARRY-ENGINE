import os

HF_TOKEN    = os.environ.get("HF_TOKEN", "")
DATA_REPO   = "P2SAMAPA/fi-etf-macro-signal-master-data"
OUTPUT_REPO = "P2SAMAPA/p2-etf-carry-engine-results"

UNIVERSES = {
    "FI_COMMODITIES": ["TLT", "VCIT", "LQD", "HYG", "VNQ", "GLD", "SLV"],
    "EQUITY_SECTORS": [
        "SPY", "QQQ", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY",
        "XLP", "XLU", "GDX", "XME", "IWF", "XSD", "XBI",
        "IWM", "IWD", "IWO", "XLB", "XLRE",
    ],
    "COMBINED": [
        "TLT", "VCIT", "LQD", "HYG", "VNQ", "GLD", "SLV",
        "SPY", "QQQ", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY",
        "XLP", "XLU", "GDX", "XME", "IWF", "XSD", "XBI",
        "IWM", "IWD", "IWO", "XLB", "XLRE",
    ],
}

# ETF type classification for carry sub-signals
FI_ETFS        = ["TLT", "VCIT", "LQD", "HYG"]      # duration / credit carry
REIT_ETFS      = ["VNQ", "XLRE"]                     # dividend / REIT carry
COMMODITY_ETFS = ["GLD", "SLV"]                      # roll yield carry
EQUITY_ETFS    = [
    "SPY", "QQQ", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY",
    "XLP", "XLU", "GDX", "XME", "IWF", "XSD", "XBI",
    "IWM", "IWD", "IWO", "XLB",
]

# Risk-free rate — TBILL_3M is the actual column name in master data
RISK_FREE_COL = "TBILL_3M"

# Rolling windows
WINDOWS = [21, 63, 126, 252]

# Blend weights for composite carry score
W_YIELD_CARRY  = 0.50
W_ROLL_CARRY   = 0.30
W_EQUITY_CARRY = 0.20

SCORE_LOOKBACK = 21
TOP_N = 3
