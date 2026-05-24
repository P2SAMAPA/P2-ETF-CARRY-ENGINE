# P2-ETF-CARRY-ENGINE

**Cross-Asset Carry Engine** — part of the P2Quant Engine Suite (v14).

Implements the Koijen et al. (2018) carry framework adapted for ETFs. Carry is defined as the expected return of an asset assuming prices stay constant. The engine computes three carry sub-signals (yield carry, roll yield carry, equity carry) and blends them into a composite cross-sectional score.

---

## Mathematical Foundation

### Carry Definition (Koijen et al. 2018)

> "Carry of an asset is its expected return, assuming prices stay the same."

For each ETF type, we use the most informative proxy for carry:

### 1. FI & REIT Carry (yield carry)

```
carry_fi(i) = rolling_annualised_return(i, W) − risk_free_rate
```

Rolling total return over window W annualised, minus the 3M T-Bill rate. High value = ETF is generating income carry above risk-free.

Applied to: TLT, VCIT, LQD, HYG, VNQ

### 2. Commodity Roll Yield Carry

```
carry_commodity(i) = −(r_longterm(i) − r_shortterm(i))
```

Backwardation (short-term return > long-term return) = futures curve sloping downward = positive carry for long position. Contango = negative carry.

Applied to: GLD, SLV

### 3. Equity Earnings Yield Carry (Asness et al. 2013)

```
carry_equity(i) = −(r_12m(i) − risk_free_rate)
```

High recent price run-up = expensive = low earnings yield = low carry. Negative of excess 12m return is a value/carry signal.

Applied to: SPY, QQQ, XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, GDX, XME, IWF, XSD, XBI, IWM, IWD, IWO

### Composite Score

All three components are cross-sectionally z-scored within each window, then blended:

```
score_i = 0.50 × z(carry_fi_i)
         + 0.30 × z(carry_commodity_i)
         + 0.20 × z(carry_equity_i)
```

Final composite is cross-sectionally z-scored across all ETFs.

---

## Repository Structure

```
P2-ETF-CARRY-ENGINE/
├── config.py             # Universe, ETF type lists, windows, weights
├── carry_engine.py       # FI/commodity/equity carry + composite score
├── data_manager.py       # HF data loader, price matrix, risk-free rate
├── trainer.py            # Main runner
├── streamlit_app.py      # Two-tab Streamlit dashboard
├── push_results.py       # HuggingFace upload
├── us_calendar.py        # Next trading day
├── requirements.txt
└── .github/workflows/daily.yml
```

---

## Data Requirements

Uses the P2SAMAPA master data parquet (`fi-etf-macro-signal-master-data`).

**Required column:** `DTB3` — 3M T-Bill annualised rate (percent). If your master data uses a different column name for the risk-free rate, update `RISK_FREE_COL` in `config.py`. Falls back to 5.0% flat if column is missing.

---

## Universes

| Universe | Tickers |
|----------|---------|
| FI_COMMODITIES | TLT, VCIT, LQD, HYG, VNQ, GLD, SLV |
| EQUITY_SECTORS | SPY, QQQ, XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, GDX, XME, IWF, XSD, XBI, IWM, IWD, IWO |
| COMBINED | All of the above |

---

## Rolling Windows

| Window | Duration | Signal character |
|--------|----------|-----------------|
| 21d | ~1 month | Very short-term, reactive |
| 63d | ~3 months | **Recommended** — captures quarterly carry cycle |
| 126d | ~6 months | Medium-term carry |
| 252d | ~1 year | Long-run structural carry premium |

---

## Blend Weights

| Component | Weight | Rationale |
|-----------|--------|-----------|
| Yield carry (FI/REIT) | 50% | Most direct carry signal for income-producing ETFs |
| Roll yield (commodities) | 30% | Backwardation/contango is the core commodity carry |
| Equity earnings yield | 20% | Noisier proxy; lower weight |

Weights are tunable in `config.py`.

---

## Output Files (pushed to HuggingFace)

| File | Tab | Content |
|------|-----|---------|
| `carry_engine_YYYY-MM-DD.json` | Tab 1 | Best window per ETF + full scores |
| `carry_engine_windows_YYYY-MM-DD.json` | Tab 2 | Full ranking at every window |

---

## Streamlit App

**Tab 1 — Best Window per ETF**
- Top 3 ETF cards per universe (best carry score across all windows)
- Full ranking table with best window shown
- Carry methodology explanation

**Tab 2 — Explore by Window**
- Window dropdown (21d / 63d / 126d / 252d)
- Window guidance panel (which window suits which regime)
- Top 3 cards + full ranking per universe at selected window

---

## Setup

1. Create GitHub repo `P2-ETF-CARRY-ENGINE`
2. Create HuggingFace dataset `P2SAMAPA/p2-etf-carry-engine-results`
3. Add `HF_TOKEN` as a GitHub Actions secret
4. In repo Settings → Actions → General → set **Workflow permissions** to **Read and write**
5. Push all files to `main`
6. Actions → Run workflow

---

## References

- Koijen, R., Moskowitz, T., Pedersen, L., Vrugt, E. (2018). *Carry*. Journal of Financial Economics.
- Asness, C., Moskowitz, T., Pedersen, L. (2013). *Value and Momentum Everywhere*. Journal of Finance.

**HuggingFace Results:** `P2SAMAPA/p2-etf-carry-engine-results`  
**Part of:** P2Quant Engine Suite · P2SAMAPA
