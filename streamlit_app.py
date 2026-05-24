import streamlit as st
import pandas as pd
import json
from huggingface_hub import HfFileSystem
import config
from us_calendar import next_trading_day

st.set_page_config(page_title="Carry Engine", layout="wide")

st.markdown("""
<style>
.main-header { font-size:2.4rem; font-weight:700; color:#7d6608; margin-bottom:0.3rem; }
.sub-header  { font-size:1.1rem; color:#555; margin-bottom:1.5rem; }
.uni-title   { font-size:1.4rem; font-weight:600; margin-top:1rem; margin-bottom:0.8rem;
               padding-left:0.5rem; border-left:5px solid #b7950b; }
.etf-card    { background:linear-gradient(135deg,#7d6608 0%,#2c3e50 100%); color:white;
               border-radius:14px; padding:1rem; margin:0.4rem; text-align:center;
               box-shadow:0 4px 6px rgba(0,0,0,0.2); }
.win-card    { background:linear-gradient(135deg,#6e2f1a 0%,#7d6608 100%); color:white;
               border-radius:14px; padding:1rem; margin:0.4rem; text-align:center;
               box-shadow:0 4px 6px rgba(0,0,0,0.2); }
.carry-box   { background:#fef9e7; border-radius:10px; padding:0.8rem 1.2rem;
               margin-bottom:1rem; border-left:4px solid #b7950b; }
.etf-ticker  { font-size:1.3rem; font-weight:bold; }
.etf-score   { font-size:0.88rem; margin-top:0.25rem; opacity:0.9; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">💰 Cross-Asset Carry Engine</div>',
            unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Koijen et al. (2018) carry framework · '
    'FI yield carry + Commodity roll yield + Equity earnings yield · '
    'Multi-window cross-sectional z-score ranking</div>',
    unsafe_allow_html=True)

st.sidebar.markdown("## 💰 Carry Engine")
st.sidebar.markdown(f"**Next Trading Day:** `{next_trading_day()}`")
st.sidebar.markdown(f"**Windows:** {config.WINDOWS}")
st.sidebar.markdown(
    f"**Weights:** Yield {config.W_YIELD_CARRY:.0%} | "
    f"Roll {config.W_ROLL_CARRY:.0%} | "
    f"Equity {config.W_EQUITY_CARRY:.0%}")

HF_TOKEN    = config.HF_TOKEN
OUTPUT_REPO = config.OUTPUT_REPO


@st.cache_data(ttl=3600)
def list_repo_files():
    fs = HfFileSystem(token=HF_TOKEN)
    try:
        return [f["name"] for f in fs.ls(f"datasets/{OUTPUT_REPO}",
                                          detail=True, recursive=True)
                if f["type"] == "file"]
    except Exception as e:
        return [f"Error: {e}"]


def find_latest(files, prefix):
    matches = sorted([f for f in files if f.endswith(".json") and prefix in f],
                     reverse=True)
    return matches[0] if matches else None


@st.cache_data(ttl=3600)
def load_json(path):
    fs = HfFileSystem(token=HF_TOKEN)
    try:
        with fs.open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


files     = list_repo_files()
tab1_path = find_latest(files, "carry_engine_2")
tab2_path = find_latest(files, "carry_engine_windows_")

if not tab1_path:
    st.error("No results found. Run trainer.py first.")
    st.stop()

data1 = load_json(tab1_path)
if "error" in data1:
    st.error(f"Error loading data: {data1['error']}")
    st.stop()

data2      = load_json(tab2_path) if tab2_path else None
universes1 = data1["universes"]
universes2 = data2["universes"] if data2 and "error" not in data2 else None

st.sidebar.markdown(f"**Run date:** `{data1.get('run_date','?')}`")

tab1, tab2 = st.tabs(["🏆 Best Window per ETF", "🔍 Explore by Window"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("🏆 Top ETFs — Cross-Asset Carry Signal")

    with st.expander("📖 Carry Signal Methodology", expanded=True):
        st.markdown("""
**Carry** = expected return assuming prices stay constant (Koijen et al. 2018).

| ETF Type | Carry Proxy | Logic |
|----------|------------|-------|
| **FI ETFs** (TLT, LQD, HYG, VCIT) | Rolling yield minus 3M T-Bill | Income carry over risk-free rate |
| **REIT** (VNQ) | Rolling yield minus 3M T-Bill | Dividend yield carry |
| **Commodities** (GLD, SLV) | Roll yield = -(long-term return − short-term return) | Backwardation = positive carry |
| **Equity ETFs** (SPY, XLK…) | Negative of excess 12m return | High price run-up = expensive = low carry |

All components are cross-sectionally z-scored per window, then blended:
**Score = 50% yield carry + 30% roll carry + 20% equity carry** → final z-score.
        """)

    for universe_name, uni_data in universes1.items():
        top_etfs = uni_data.get("top_etfs", [])
        if not top_etfs:
            continue
        st.markdown(
            f'<div class="uni-title">{universe_name.replace("_"," ").title()}</div>',
            unsafe_allow_html=True)
        cols = st.columns(3)
        for idx, etf in enumerate(top_etfs):
            with cols[idx]:
                st.markdown(f"""
<div class="etf-card">
  <div class="etf-ticker">{etf['ticker']}</div>
  <div class="etf-score">carry score = {etf['carry_score']:.4f}</div>
  <div class="etf-score">best window = {etf.get('best_window','N/A')}d</div>
</div>
""", unsafe_allow_html=True)

        with st.expander(f"📋 Full ranking — {universe_name}"):
            full = uni_data.get("full_scores", {})
            if full:
                rows = []
                for t, info in full.items():
                    score = info.get("score", info) if isinstance(info, dict) else info
                    win   = info.get("best_window", "N/A") if isinstance(info, dict) else "N/A"
                    rows.append({"ETF": t, "Carry Score": score, "Best Window (d)": win})
                df = pd.DataFrame(rows).sort_values("Carry Score", ascending=False)
                st.dataframe(df, use_container_width=True, hide_index=True)
        st.divider()

    st.caption(f"Run date: {data1.get('run_date','?')} · "
               "Koijen et al. (2018) carry framework · "
               "Scores are cross-sectional z-scores.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("🔍 Explore Carry Rankings by Window")

    if not universes2:
        st.warning("Window-level detail not found. Re-run trainer to generate "
                   "`carry_engine_windows_<date>.json`.")
        st.stop()

    all_wins = set()
    for ud in universes2.values():
        all_wins.update(ud.get("windows", {}).keys())
    win_options = sorted([int(w) for w in all_wins])

    if not win_options:
        st.error("No window data available.")
        st.stop()

    default_idx  = win_options.index(63) if 63 in win_options else 0
    selected_win = st.selectbox(
        "Select lookback window",
        options=win_options,
        index=default_idx,
        format_func=lambda w: f"{w}d  (~{round(w/21)} months)",
    )
    win_key = str(selected_win)

    with st.expander("ℹ️ Window guidance", expanded=False):
        st.markdown("""
- **21d** — very short-term carry; sensitive to recent price moves
- **63d** — 3-month carry; good for regime-aware carry
- **126d** — 6-month carry; balanced between signal and noise
- **252d** — 1-year carry; most stable, closest to structural carry premium
        """)

    st.markdown(f"### Carry Rankings at **{selected_win}d** window")

    for universe_name in ["FI_COMMODITIES", "EQUITY_SECTORS", "COMBINED"]:
        label = {"FI_COMMODITIES": "🏦 FI & Commodities",
                 "EQUITY_SECTORS": "📈 Equity Sectors",
                 "COMBINED":       "🌐 Combined"}.get(universe_name, universe_name)

        st.markdown(f'<div class="uni-title">{label}</div>', unsafe_allow_html=True)

        uni_data = universes2.get(universe_name, {})
        win_data = uni_data.get("windows", {}).get(win_key)

        if not win_data:
            st.info(f"No data for {universe_name} at {selected_win}d.")
            st.divider()
            continue

        cols = st.columns(3)
        for idx, etf in enumerate(win_data.get("top_etfs", [])):
            with cols[idx]:
                st.markdown(f"""
<div class="win-card">
  <div class="etf-ticker">{etf['ticker']}</div>
  <div class="etf-score">carry score = {etf['carry_score']:.4f}</div>
  <div class="etf-score">window = {selected_win}d</div>
</div>
""", unsafe_allow_html=True)

        with st.expander(f"📋 Full ranking — {label} @ {selected_win}d"):
            rows = win_data.get("full_ranking", [])
            if rows:
                df = pd.DataFrame(rows)
                df.columns = ["ETF", "Carry Score"]
                df.insert(0, "Rank", range(1, len(df) + 1))
                st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()

    st.caption(f"Window: {selected_win}d · Run date: {data2.get('run_date','?')}")
