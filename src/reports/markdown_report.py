from __future__ import annotations

from pathlib import Path

from src.radar.daily_radar import DailyRadarReport, RadarSignal


class MarkdownReport:
    def __init__(self, app_name: str, app_version: str) -> None:
        self.app_name = app_name
        self.app_version = app_version

    def render(self, report: DailyRadarReport) -> str:
        lines = [
            f"# {self.app_name} Daily Radar",
            "",
            f"- Version: {self.app_version}",
            f"- Generated at: {report.generated_at.isoformat()}",
            "- Data policy: public data only",
            "- Research mode: informational, not trading advice",
            "",
            "## Top Signals",
            "",
        ]

        if report.signals:
            lines.extend(self._signals_table(report.signals))
        else:
            lines.append("No usable public market data was collected.")

        lines.extend(
            [
                "",
                "## Methodology",
                "",
            ]
        )
        for item in report.methodology:
            lines.append(f"- {item}")

        if report.errors:
            lines.extend(
                [
                    "",
                    "## Collection Errors",
                    "",
                ]
            )
            for ticker, error in sorted(report.errors.items()):
                lines.append(f"- {ticker}: {error}")

        lines.extend(
            [
                "",
                "## Source Notes",
                "",
                "- Market data source: Yahoo Finance public chart API.",
                "- No brokerage, private account, or proprietary feed data is used.",
                "",
            ]
        )
        return "\n".join(lines)

    def write(self, report: DailyRadarReport, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(report), encoding="utf-8")
        return path

    def _signals_table(self, signals: list[RadarSignal]) -> list[str]:
        lines = [
            "| Rank | Ticker | Theme | Last Price | 1-Period Change | Volume Ratio | Score | Observed At |",
            "| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]

        for rank, signal in enumerate(signals, start=1):
            lines.append(
                "| {rank} | {ticker} | {theme} | {last_price} | {change} | {volume_ratio} | {score} | {observed_at} |".format(
                    rank=rank,
                    ticker=signal.ticker,
                    theme=signal.theme,
                    last_price=self._format_float(signal.last_price),
                    change=self._format_pct(signal.price_change_pct),
                    volume_ratio=self._format_ratio(signal.volume_ratio),
                    score=self._format_float(signal.score),
                    observed_at=signal.observed_at.date().isoformat(),
                )
            )

        return lines

    @staticmethod
    def _format_float(value: float | None) -> str:
        if value is None:
            return "n/a"
        return f"{value:.2f}"

    @staticmethod
    def _format_pct(value: float | None) -> str:
        if value is None:
            return "n/a"
        return f"{value:.2f}%"

    @staticmethod
    def _format_ratio(value: float | None) -> str:
        if value is None:
            return "n/a"
        return f"{value:.2f}x"
