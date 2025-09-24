"""Backtesting utility CLI for HypeBot.

Runs strategies over historical data and reports results. See SPEC/spec.md
for detailed behavior and CLI documentation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency per spec
    yaml = None  # type: ignore

import pandas as pd

from hypebot.config import Config
from hypebot.backtesting.backtester import BackTester, CommissionModel
from hypebot.backtesting.metrics import compute_metrics
from hypebot.backtesting.visualize import plot_equity_curves
from hypebot.indicators.rsi_calculator import RSICalculator
from hypebot.strategy.rsi_strategy import RSIStrategy
from hypebot.strategy.buy_and_hold_strategy import BuyAndHoldStrategy
from hypebot.data.storage import DataStorage
from hypebot.position.manager import PositionManager
from hypebot.position.kelly_criterion import KellyCriterion


def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {dt_str}. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")


def _parse_commission(spec: Optional[str]) -> CommissionModel:
    if not spec:
        return CommissionModel(type="percent", value=0.001)
    try:
        parts = spec.split(":", 1)
        ctype = parts[0].strip()
        cval = float(parts[1]) if len(parts) > 1 else 0.0
        if ctype not in ("fixed", "percent"):
            raise ValueError
        return CommissionModel(type=ctype, value=cval)
    except Exception:
        raise ValueError("--commission must be like 'fixed:0.5' or 'percent:0.001'")


def _load_yaml_config(path: Optional[str]) -> Dict:
    if not path:
        return {}
    if yaml is None:
        raise RuntimeError("PyYAML is required to load a config file. Install PyYAML or omit --config.")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("Config file must contain a top-level mapping")
    return data


def _resolve_args_with_config(args: argparse.Namespace, cfg: Dict) -> Tuple[Dict, Dict]:
    """Merge CLI args with YAML config. Returns (backtest_cfg, strategy_params)."""
    backtest_cfg: Dict = {
        "assets": None,
        "strategy": None,
        "interval": args.interval,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "starting_cash": args.starting_cash,
        "commission": args.commission,
        "output_dir": args.output_dir,
        "show_plot": not args.no_plot,
        "debug": args.debug,
    }
    if cfg:
        bt = cfg.get("backtest") or {}
        # Only fill from config when CLI did not provide a value (CLI precedence)
        for key in ("interval", "start_date", "end_date", "starting_cash", "output_dir", "debug"):
            if backtest_cfg.get(key) is None and bt.get(key) is not None:
                backtest_cfg[key] = bt.get(key)
        # show_plot defaults to True in config unless explicitly false
        if bt.get("show_plot") is not None and args.no_plot is False:
            backtest_cfg["show_plot"] = bool(bt.get("show_plot"))
        # assets and strategy required
        backtest_cfg["assets"] = bt.get("assets")
        backtest_cfg["strategy"] = bt.get("strategy")
        # commission
        if isinstance(bt.get("commission"), dict):
            cdict = bt.get("commission")
            backtest_cfg["commission"] = f"{cdict.get('type')}:{cdict.get('value')}"
    else:
        backtest_cfg["assets"] = args.assets
        backtest_cfg["strategy"] = args.strategy

    strategy_params = (cfg.get("strategy_params") or {}) if cfg else {}
    return backtest_cfg, strategy_params


def _build_strategy(name: str, config: Config, params: Dict, assets: list[str], interval: str):
    key = (name or "").strip().lower()
    if key in ("rsi", "rsi_strategy"):
        period = int(params.get("period", config.trading.rsi_period))
        oversold = float(params.get("oversold", config.trading.rsi_oversold))
        overbought = float(params.get("overbought", config.trading.rsi_overbought))
        rsi_calc = RSICalculator(
            period=period,
            oversold_threshold=oversold,
            overbought_threshold=overbought,
        )
        storage = DataStorage(config.database)
        # Create position manager for strategy initialization
        pm = PositionManager(config.trading, storage, load_existing=False)
        kelly_criterion = KellyCriterion(config.trading)
        return RSIStrategy(
            assets=assets, 
            interval=interval, 
            position_manager=pm,
            rsi_calculator=rsi_calc,
            kelly_criterion=kelly_criterion,
            config=config.trading
        )
    elif key in ("buy_and_hold", "buyandhold", "buy-and-hold"):
        storage = DataStorage(config.database)
        pm = PositionManager(config.trading, storage, load_existing=False)
        return BuyAndHoldStrategy(
            assets=assets,
            interval=interval,
            position_manager=pm
        )
    raise ValueError(f"Unsupported strategy: {name}")


def _print_metrics(name: str, _metrics: Dict[str, float]) -> None:
    def pct(x: float) -> str:
        return f"{x*100:.2f}%"
    print(f"\nResults - {name}")
    print("====================")
    print(f"Total Return:   {pct(_metrics.get('return_pct', 0.0))}")
    print(f"CAGR:           {pct(_metrics.get('cagr', 0.0))}")
    print(f"Vol (annual):   {pct(_metrics.get('vol_annual', 0.0))}")
    print(f"Sharpe:         {_metrics.get('sharpe', 0.0):.2f}")
    print(f"Sortino:        {_metrics.get('sortino', 0.0):.2f}")
    print(f"Max Drawdown:   {pct(_metrics.get('max_drawdown', 0.0))}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run a backtest using HypeBot")
    parser.add_argument("--assets", "-a", type=str, help="Comma-separated symbols, e.g., BTC-USD,ETH-USD")
    parser.add_argument("--strategy", "-s", type=str, help="Strategy name, e.g., rsi")
    parser.add_argument("--interval", "-i", type=str, default="1d", help="Interval: 1h,4h,1d,1w,1mo")
    parser.add_argument("--start-date", "--start", dest="start_date", type=str, default=None)
    parser.add_argument("--end-date", "--end", dest="end_date", type=str, default=None)
    parser.add_argument("--starting-cash", "--cash", dest="starting_cash", type=float, default=10000.0)
    parser.add_argument("--commission", type=str, default=None, help="fixed:0.5 or percent:0.001")
    parser.add_argument("--config", "-c", type=str, default=None, help="YAML config file")
    parser.add_argument("--no-plot", action="store_true", help="Suppress equity curve plot")
    parser.add_argument("--debug", action="store_true", help="Show profiling information")
    # Let YAML override when CLI flag not provided; default applied later
    parser.add_argument("--output-dir", "-o", type=str, default=None)

    args = parser.parse_args(argv)

    # Load config file and merge
    cfg_file_data = _load_yaml_config(args.config) if args.config else {}
    merged, strat_params_all = _resolve_args_with_config(args, cfg_file_data)

    # Validate required fields
    if not merged.get("assets") or not merged.get("strategy"):
        print("Error: --assets and --strategy are required (or provide them via --config).", file=sys.stderr)
        return 2

    if isinstance(merged["assets"], str):
        assets = [s.strip() for s in merged["assets"].split(",") if s and s.strip()]
    else:
        assets = [s.strip() for s in merged["assets"] if s and s.strip()]
    strategy_name = str(merged["strategy"]).strip()
    interval = str(merged["interval"]).strip()
    start = _parse_datetime(merged.get("start_date"))
    end = _parse_datetime(merged.get("end_date"))
    starting_cash = float(merged.get("starting_cash", 10000.0))
    commission = _parse_commission(merged.get("commission"))
    # Use CLI > YAML > fallback default
    output_dir = str(merged.get("output_dir") or "./backtest_results")
    show_plot = bool(merged.get("show_plot", True))
    debug = bool(merged.get("debug", False))

    os.makedirs(output_dir, exist_ok=True)

    if debug:
        logging.basicConfig(level=logging.DEBUG)

    # Build runtime config (do not call validate here; backtests don't require live API keys)
    config = Config.from_env()

    # Construct strategy
    strat_params = strat_params_all.get(strategy_name, {})
    strategy = _build_strategy(strategy_name, config, strat_params, assets=assets, interval=interval)

    # Run the backtest with control strategy
    bt = BackTester(config=config, commission=commission, starting_cash=starting_cash)

    t0 = time.perf_counter()
    results = None
    try:
        # BackTester.run_with_control is async; run it
        import asyncio

        async def _run():
            return await bt.run_with_control(
                strategies=[strategy], 
                assets=assets, 
                interval=interval, 
                start=start, 
                end=end
            )

        results = asyncio.run(_run())
    finally:
        elapsed_s = time.perf_counter() - t0

    # Get the main strategy result
    strategy_name = strategy.__class__.__name__
    result = results.get(strategy_name)
    equity_curve = result.equity_curve

    # Compute and print metrics for main strategy
    periods_per_year = {
        "1h": 24 * 365,
        "4h": 6 * 365,
        "1d": 252,
        "1w": 52,
        "1mo": 12,
    }.get(interval, 252)
    metrics = compute_metrics(equity_curve, risk_free_rate=config.trading.risk_free_rate, periods_per_year=periods_per_year)
    _print_metrics(strategy_name, metrics)

    print(f"Elapsed: {elapsed_s:.2f}s | Points: {len(equity_curve)}")

    # Save outputs for main strategy
    # 1) Equity curve CSV
    ecsv_path = os.path.join(output_dir, f"equity_{strategy_name.replace(' ', '_')}.csv")
    equity_curve.to_csv(ecsv_path, header=["equity"])  # index are timestamps

    # 2) Metrics JSON
    mjson_path = os.path.join(output_dir, f"metrics_{strategy_name.replace(' ', '_')}.json")
    with open(mjson_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # 3) Trades/Orders CSV (capture executed orders as trade-like log)
    trades_csv_path = os.path.join(output_dir, f"trades_{strategy_name.replace(' ', '_')}.csv")
    try:
        rows = []
        if hasattr(result, "orders") and isinstance(result.orders, list):  # type: ignore
            for o in result.orders:  # type: ignore
                rows.append({
                    "timestamp": getattr(o, "timestamp", None),
                    "symbol": getattr(o, "symbol", None),
                    "side": getattr(o, "side", None),
                    "order_type": getattr(o, "order_type", None),
                    "quantity": getattr(o, "quantity", None),
                    "price": getattr(o, "price", None),
                    "filled_quantity": getattr(o, "filled_quantity", None),
                    "average_fill_price": getattr(o, "average_fill_price", None),
                    "status": getattr(o, "status", None),
                    "order_id": getattr(o, "order_id", None),
                })
        df_trades = pd.DataFrame(rows)
        if "timestamp" in df_trades.columns:
            df_trades["timestamp"] = pd.to_datetime(df_trades["timestamp"])  # will handle None
        df_trades.to_csv(trades_csv_path, index=False)
        print(f"Saved trades CSV: {trades_csv_path}")
    except Exception as e:
        print(f"Warning: failed to write trades CSV: {e}")

    # Plot will be generated in the buy-and-hold section if available

    # 5) Debug info
    if debug and isinstance(result.snapshots.attrs.get("profile"), dict):  # type: ignore
        profile = result.snapshots.attrs.get("profile")  # type: ignore
        print("\nProfiling Info:")
        for k, v in profile.items():
            try:
                print(f"- {k}: {v}")
            except Exception:
                pass

    print(f"Saved equity CSV: {ecsv_path}")
    print(f"Saved metrics JSON: {mjson_path}")

    # Process buy-and-hold control strategy if provided
    control_result = results.get("BuyAndHoldStrategy")
    control_equity_curve = None
    if control_result is not None:
        control_equity_curve = control_result.equity_curve
        # Compute metrics for buy-and-hold
        control_metrics = compute_metrics(control_equity_curve, risk_free_rate=config.trading.risk_free_rate, periods_per_year=periods_per_year)
        _print_metrics("BuyAndHoldStrategy", control_metrics)
        # Save buy-and-hold outputs
        # 1) Equity curve CSV
        control_ecsv_path = os.path.join(output_dir, "equity_buy_and_hold.csv")
        control_equity_curve.to_csv(control_ecsv_path, header=["equity"])
        # 2) Metrics JSON
        control_mjson_path = os.path.join(output_dir, "metrics_buy_and_hold.json")
        with open(control_mjson_path, "w", encoding="utf-8") as f:
            json.dump(control_metrics, f, indent=2)
        # 3) Trades CSV for buy-and-hold
        control_trades_csv_path = os.path.join(output_dir, "trades_buy_and_hold.csv")
        try:
            if hasattr(control_result, "orders") and isinstance(control_result.orders, list) and len(control_result.orders) > 0:
                rows = []
                for o in control_result.orders:
                    try:
                        rows.append({
                            "timestamp": getattr(o, "timestamp", None),
                            "symbol": getattr(o, "symbol", None),
                            "side": getattr(o, "side", None),
                            "order_type": getattr(o, "order_type", None),
                            "quantity": getattr(o, "quantity", None),
                            "price": getattr(o, "price", None),
                            "filled_quantity": getattr(o, "filled_quantity", None),
                            "average_fill_price": getattr(o, "average_fill_price", None),
                            "status": getattr(o, "status", None),
                            "order_id": getattr(o, "order_id", None),
                        })
                    except Exception:
                        continue
                if rows:
                    df_trades = pd.DataFrame(rows)
                    if "timestamp" in df_trades.columns:
                        df_trades["timestamp"] = pd.to_datetime(df_trades["timestamp"])
                    df_trades.to_csv(control_trades_csv_path, index=False)
                    print(f"Saved buy-and-hold trades CSV: {control_trades_csv_path}")
        except Exception as e:
            print(f"Warning: failed to write buy-and-hold trades CSV: {e}")
        print(f"Saved buy-and-hold equity CSV: {control_ecsv_path}")
        print(f"Saved buy-and-hold metrics JSON: {control_mjson_path}")
    
    # Update the plot (include control if available)
    if show_plot and not equity_curve.empty:
        plot_path = os.path.join(output_dir, f"equity_{strategy_name.replace(' ', '_')}.png")
        combined_curves = {strategy_name: equity_curve}
        if control_equity_curve is not None:
            combined_curves["BuyAndHoldStrategy"] = control_equity_curve
        plot_equity_curves(combined_curves, title=f"Equity Curves - {strategy_name} vs Buy & Hold", filepath=plot_path)
        print(f"Saved combined plot: {plot_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())


