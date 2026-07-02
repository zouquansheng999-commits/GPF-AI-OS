from __future__ import annotations

import json
from pathlib import Path

from config import DATA_DIR


WATCHLIST_PATH = DATA_DIR / "watchlist.json"


def load_watchlist(path: Path = WATCHLIST_PATH) -> dict[str, list[str]]:
    with path.open("r", encoding="utf-8") as watchlist_file:
        raw_watchlist = json.load(watchlist_file)

    if not isinstance(raw_watchlist, dict):
        raise ValueError("watchlist.json must contain an object of theme names to ticker lists")

    watchlist: dict[str, list[str]] = {}
    for theme, tickers in raw_watchlist.items():
        if not isinstance(theme, str) or not theme.strip():
            raise ValueError("watchlist themes must be non-empty strings")
        if not isinstance(tickers, list):
            raise ValueError(f"watchlist theme {theme!r} must contain a list of tickers")

        normalized_tickers: list[str] = []
        for ticker in tickers:
            if not isinstance(ticker, str) or not ticker.strip():
                raise ValueError(f"watchlist theme {theme!r} contains an invalid ticker")
            normalized_tickers.append(ticker.strip().upper())

        watchlist[theme.strip()] = normalized_tickers

    return watchlist


def all_tickers(watchlist: dict[str, list[str]] | None = None) -> list[str]:
    configured_watchlist = watchlist or load_watchlist()
    tickers: list[str] = []
    seen: set[str] = set()

    for theme_tickers in configured_watchlist.values():
        for ticker in theme_tickers:
            symbol = ticker.strip().upper()
            if symbol not in seen:
                tickers.append(symbol)
                seen.add(symbol)

    return tickers


def theme_for_ticker(
    ticker: str,
    watchlist: dict[str, list[str]] | None = None,
) -> str:
    symbol = ticker.strip().upper()
    configured_watchlist = watchlist or load_watchlist()

    for theme, theme_tickers in configured_watchlist.items():
        if symbol in {theme_ticker.upper() for theme_ticker in theme_tickers}:
            return theme

    return "General Market"
