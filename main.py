from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

from config import APP_NAME, DATA_DIR, LOG_DIR, VERSION
from src.collectors.yahoo import YahooFinanceCollector
from src.radar.daily_radar import DailyRadar
from src.reports.markdown_report import MarkdownReport


DEFAULT_TICKERS = [
    "NVDA",
    "MSFT",
    "AAPL",
    "GOOGL",
    "AMD",
    "TSM",
    "ASML",
    "SMR",
    "PLTR",
    "SPY",
    "QQQ",
]


def configure_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIR / "gpf-ai-os.log", encoding="utf-8"),
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gpf-ai-os",
        description="Run the GPF-AI-OS Sprint 1 public-data daily radar.",
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=DEFAULT_TICKERS,
        help="Ticker symbols to scan. Defaults to a public AI infrastructure watchlist.",
    )
    parser.add_argument(
        "--range",
        default="5d",
        choices=["1d", "5d", "1mo", "3mo"],
        help="Yahoo Finance chart range to request.",
    )
    parser.add_argument(
        "--interval",
        default="1d",
        choices=["1d", "1h", "30m", "15m"],
        help="Yahoo Finance chart interval to request.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional Markdown report path. Defaults to data/reports/daily_radar_<UTC date>.md.",
    )
    return parser.parse_args()


def default_report_path() -> Path:
    report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return DATA_DIR / "reports" / f"daily_radar_{report_date}.md"


def main() -> int:
    configure_logging()
    logger = logging.getLogger(__name__)
    args = parse_args()
    output_path = args.output or default_report_path()

    logger.info("running daily radar for %d tickers", len(args.tickers))
    collector = YahooFinanceCollector()
    radar = DailyRadar(collector=collector)
    report = radar.run(
        tickers=args.tickers,
        range_value=args.range,
        interval=args.interval,
    )

    renderer = MarkdownReport(app_name=APP_NAME, app_version=VERSION)
    renderer.write(report=report, path=output_path)

    logger.info("daily radar report written to %s", output_path)
    print(f"Report written: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
