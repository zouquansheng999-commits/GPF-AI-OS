from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.collectors.yahoo import MarketSnapshot, YahooFinanceCollector
from src.knowledge.watchlist import load_watchlist, theme_for_ticker


@dataclass(frozen=True)
class RadarSignal:
    ticker: str
    theme: str
    last_price: float
    previous_close: float | None
    price_change_pct: float | None
    latest_volume: int | None
    average_volume: float | None
    volume_ratio: float | None
    score: float
    source: str
    observed_at: datetime


@dataclass(frozen=True)
class DailyRadarReport:
    generated_at: datetime
    signals: list[RadarSignal]
    errors: dict[str, str]
    methodology: list[str]


class DailyRadar:
    def __init__(
        self,
        collector: YahooFinanceCollector | None = None,
        watchlist: dict[str, list[str]] | None = None,
    ) -> None:
        self.collector = collector or YahooFinanceCollector()
        self.watchlist = watchlist or load_watchlist()

    def run(
        self,
        tickers: list[str],
        range_value: str = "5d",
        interval: str = "1d",
    ) -> DailyRadarReport:
        snapshots, errors = self.collector.fetch_many(
            tickers=tickers,
            range_value=range_value,
            interval=interval,
        )
        signals = [self._build_signal(snapshot) for snapshot in snapshots]
        signals.sort(key=lambda signal: signal.score, reverse=True)

        return DailyRadarReport(
            generated_at=datetime.now(timezone.utc),
            signals=signals,
            errors=errors,
            methodology=[
                "Collect public OHLCV data from Yahoo Finance.",
                "Compare the latest close with the previous usable close.",
                "Compare latest volume with the available average volume window.",
                "Rank signals with a simple explainable score: price momentum plus volume confirmation.",
            ],
        )

    def _build_signal(self, snapshot: MarketSnapshot) -> RadarSignal:
        latest = snapshot.bars[-1]
        previous = snapshot.bars[-2] if len(snapshot.bars) >= 2 else None
        prior_bars = snapshot.bars[:-1] or snapshot.bars
        volume_values = [bar.volume for bar in prior_bars if bar.volume is not None]

        price_change_pct = None
        if previous and previous.close:
            price_change_pct = ((latest.close - previous.close) / previous.close) * 100

        average_volume = None
        volume_ratio = None
        if latest.volume is not None and volume_values:
            average_volume = sum(volume_values) / len(volume_values)
            if average_volume > 0:
                volume_ratio = latest.volume / average_volume

        return RadarSignal(
            ticker=snapshot.ticker,
            theme=theme_for_ticker(snapshot.ticker, self.watchlist),
            last_price=latest.close,
            previous_close=previous.close if previous else None,
            price_change_pct=price_change_pct,
            latest_volume=latest.volume,
            average_volume=average_volume,
            volume_ratio=volume_ratio,
            score=self._score(price_change_pct=price_change_pct, volume_ratio=volume_ratio),
            source=snapshot.source,
            observed_at=latest.timestamp,
        )

    @staticmethod
    def _score(price_change_pct: float | None, volume_ratio: float | None) -> float:
        momentum = price_change_pct or 0.0
        volume_confirmation = 0.0
        if volume_ratio is not None:
            volume_confirmation = min(max(volume_ratio - 1.0, -1.0), 2.0) * 2.5
        return round(momentum + volume_confirmation, 2)
