import numpy as np
import pandas as pd
from pathlib import Path
import json
from datetime import datetime

import config
import data_manager
from carry_engine import compute_carry_scores_universe


def convert_to_serializable(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating, float)):
        return float(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_to_serializable(v) for v in obj]
    return obj


def main():
    if not config.HF_TOKEN:
        print("HF_TOKEN not set")
        return

    df         = data_manager.load_master_data()
    risk_free  = data_manager.get_risk_free(df)
    today      = datetime.now().strftime("%Y-%m-%d")

    all_results = {}
    all_windows = {}

    for universe_name, tickers in config.UNIVERSES.items():
        print(f"\n=== Universe: {universe_name} (Carry Engine) ===")

        prices = data_manager.prepare_prices(df, tickers)
        available_tickers = [t for t in tickers if t in prices.columns]

        if not available_tickers or prices.empty:
            print("  No price data available")
            all_results[universe_name] = {"top_etfs": []}
            all_windows[universe_name] = {"windows": {}}
            continue

        best_per_etf   = {}
        window_results = {}

        for win in config.WINDOWS:
            min_bars = max(win, 252) + 10
            if len(prices) < min_bars:
                print(f"  Skipping window {win}d (need {min_bars} bars, have {len(prices)})")
                continue

            print(f"  Processing window {win}d...")

            try:
                scores = compute_carry_scores_universe(
                    prices=prices,
                    risk_free=risk_free,
                    tickers=available_tickers,
                    window=win,
                    fi_tickers=config.FI_ETFS,
                    reit_tickers=config.REIT_ETFS,
                    commodity_tickers=config.COMMODITY_ETFS,
                    equity_tickers=config.EQUITY_ETFS,
                    w_yield=config.W_YIELD_CARRY,
                    w_roll=config.W_ROLL_CARRY,
                    w_eq=config.W_EQUITY_CARRY,
                )
            except Exception as e:
                print(f"  Window {win}d failed: {e}")
                import traceback; traceback.print_exc()
                continue

            if scores.empty:
                print(f"  No scores for {win}d")
                continue

            score_dict = {t: float(s) for t, s in scores.items()
                          if t in available_tickers and not np.isnan(s)}
            window_results[win] = score_dict

            sorted_str = dict(sorted(score_dict.items(), key=lambda x: x[1], reverse=True))
            print(f"  Scores: {sorted_str}")

            for etf, score in score_dict.items():
                if etf not in best_per_etf or score > best_per_etf[etf][0]:
                    best_per_etf[etf] = (float(score), win)

        # ── Fallback ──────────────────────────────────────────────────────────
        if not best_per_etf:
            print("  No carry scores — falling back to historical mean return")
            for etf in available_tickers:
                ret = np.log(prices[etf] / prices[etf].shift(1)).iloc[-252:]
                mean_ret = ret.mean()
                if not np.isnan(mean_ret):
                    best_per_etf[etf] = (float(mean_ret), 0)

        if not best_per_etf:
            all_results[universe_name] = {"top_etfs": []}
            all_windows[universe_name] = {"windows": {}}
            continue

        # ── Tab 1: best window per ETF ────────────────────────────────────────
        full_scores = {
            ticker: {"score": float(score), "best_window": int(win)}
            for ticker, (score, win) in best_per_etf.items()
        }
        sorted_etfs = sorted(best_per_etf.items(), key=lambda x: x[1][0], reverse=True)
        top_etfs    = [
            {"ticker": t, "carry_score": float(s), "best_window": int(w)}
            for t, (s, w) in sorted_etfs[:config.TOP_N]
        ]

        print(f"  Top {config.TOP_N}: {[e['ticker'] for e in top_etfs]}")
        for e in top_etfs:
            print(f"    {e['ticker']}: {e['carry_score']:.4f}  (window: {e['best_window']}d)")

        all_results[universe_name] = {
            "top_etfs":       top_etfs,
            "full_scores":    full_scores,
            "window_results": window_results,
            "run_date":       today,
        }

        # ── Tab 2: per-window breakdown ───────────────────────────────────────
        windows_tab2 = {}
        for win, score_dict in window_results.items():
            sorted_win = sorted(score_dict.items(), key=lambda x: x[1], reverse=True)
            windows_tab2[str(win)] = {
                "top_etfs": [
                    {"ticker": t, "carry_score": float(s)}
                    for t, s in sorted_win[:config.TOP_N]
                ],
                "full_ranking": [
                    {"ticker": t, "carry_score": float(s)}
                    for t, s in sorted_win
                ],
            }
        all_windows[universe_name] = {"windows": windows_tab2, "run_date": today}

    # ── Write and push ────────────────────────────────────────────────────────
    Path("results").mkdir(exist_ok=True)

    tab1_path = Path(f"results/carry_engine_{today}.json")
    with open(tab1_path, "w") as f:
        json.dump(convert_to_serializable({
            "run_date":  today,
            "universes": all_results,
        }), f, indent=2)

    tab2_path = Path(f"results/carry_engine_windows_{today}.json")
    with open(tab2_path, "w") as f:
        json.dump(convert_to_serializable({
            "run_date":  today,
            "universes": all_windows,
        }), f, indent=2)

    import push_results
    push_results.push_daily_result(tab1_path)
    push_results.push_daily_result(tab2_path)

    print(f"\n=== Carry Engine complete ===")
    print(f"  Tab 1: {tab1_path.name}")
    print(f"  Tab 2: {tab2_path.name}")


if __name__ == "__main__":
    main()
