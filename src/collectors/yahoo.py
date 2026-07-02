from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"


@dataclass(frozen=True)
class MarketBar:
    timestamp: datetime
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: int | None


@dataclass(frozen=True)
class MarketSnapshot:
    ticker: str
    currency: str | None
    exchange: str | None
    instrument_type: str | None
    bars: list[MarketBar]
    source: str = "Yahoo Finance public chart API"


class YahooFinanceError(RuntimeError):
    """Raised when public Yahoo Finance data cannot be collected."""


class YahooFinanceCollector:
    def __init__(self, timeout_seconds: int = 20) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch_history(
        self,
        ticker: str,
        range_value: str = "5d",
        interval: str = "1d",
    ) -> MarketSnapshot:
        symbol = ticker.strip().upper()
        if not symbol:
            raise ValueError("ticker must not be empty")

        payload = self._get_chart_payload(
            ticker=symbol,
            range_value=range_value,
            interval=interval,
        )
        return self._parse_snapshot(symbol, payload)

    def fetch_many(
        self,
        tickers: list[str],
        range_value: str = "5d",
        interval: str = "1d",
    ) -> tuple[list[MarketSnapshot], dict[str, str]]:
        snapshots: list[MarketSnapshot] = []
        errors: dict[str, str] = {}

        for ticker in tickers:
            symbol = ticker.strip().upper()
            if not symbol:
                continue
            try:
                snapshots.append(
                    self.fetch_history(
                        ticker=symbol,
                        range_value=range_value,
                        interval=interval,
                    )
                )
            except (YahooFinanceError, ValueError) as exc:
                errors[symbol] = str(exc)

        return snapshots, errors

    def _get_chart_payload(
        self,
        ticker: str,
        range_value: str,
        interval: str,
    ) -> dict[str, Any]:
        query = urlencode(
            {
                "range": range_value,
                "interval": interval,
                "includePrePost": "false",
                "events": "div,splits",
            }
        )
        url = f"{YAHOO_CHART_URL.format(ticker=ticker)}?{query}"
        request = Request(
            url,
            headers={
                "User-Agent": "GPF-AI-OS/0.1 public research collector",
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise YahooFinanceError(f"Yahoo Finance HTTP {exc.code}") from exc
        except URLError as exc:
            raise YahooFinanceError(f"Yahoo Finance request failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise YahooFinanceError("Yahoo Finance request timed out") from exc
        except json.JSONDecodeError as exc:
            raise YahooFinanceError("Yahoo Finance returned invalid JSON") from exc

    def _parse_snapshot(self, ticker: str, payload: dict[str, Any]) -> MarketSnapshot:
        chart = payload.get("chart", {})
        error = chart.get("error")
        if error:
            description = error.get("description") or error.get("code") or "unknown error"
            raise YahooFinanceError(f"Yahoo Finance error for {ticker}: {description}")

        results = chart.get("result") or []
        if not results:
            raise YahooFinanceError(f"No Yahoo Finance chart data for {ticker}")

        result = results[0]
        meta = result.get("meta", {})
        timestamps = result.get("timestamp") or []
        quote_blocks = result.get("indicators", {}).get("quote") or []
        if not quote_blocks:
            raise YahooFinanceError(f"No OHLCV quote data for {ticker}")

        quote = quote_blocks[0]
        bars = self._parse_bars(timestamps=timestamps, quote=quote)
        if not bars:
            raise YahooFinanceError(f"No usable market bars for {ticker}")

        return MarketSnapshot(
            ticker=ticker,
            currency=meta.get("currency"),
            exchange=meta.get("exchangeName"),
            instrument_type=meta.get("instrumentType"),
            bars=bars,
        )

    def _parse_bars(self, timestamps: list[int], quote: dict[str, Any]) -> list[MarketBar]:
        bars: list[MarketBar] = []
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        for index, timestamp in enumerate(timestamps):
            close = self._get_float(closes, index)
            if close is None:
                continue
            bars.append(
                MarketBar(
                    timestamp=datetime.fromtimestamp(timestamp, tz=timezone.utc),
                    open=self._get_float(opens, index),
                    high=self._get_float(highs, index),
                    low=self._get_float(lows, index),
                    close=close,
                    volume=self._get_int(volumes, index),
                )
            )

        return bars

    @staticmethod
    def _get_float(values: list[Any], index: int) -> float | None:
        if index >= len(values) or values[index] is None:
            return None
        return float(values[index])

    @staticmethod
    def _get_int(values: list[Any], index: int) -> int | None:
        if index >= len(values) or values[index] is None:
            return None
        return int(values[index])
