"""Parse FFmpeg's machine-readable -progress output."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Progress:
    seconds: float | None
    fraction: float | None
    speed: float | None
    eta_seconds: float | None
    finalizing: bool


def parse_progress(values: dict[str, str], duration: float | None) -> Progress:
    """Use media timestamp and encoding speed; suppress unsupported ETA claims."""
    try:
        if "out_time_us" in values:
            seconds = int(values["out_time_us"]) / 1_000_000
        elif "out_time_ms" in values:
            # FFmpeg labels this field ms but its values are microseconds.
            seconds = int(values["out_time_ms"]) / 1_000_000
        else:
            seconds = None
    except ValueError:
        seconds = None
    speed_text = values.get("speed", "").rstrip("x")
    try:
        speed = float(speed_text)
        if speed <= 0:
            speed = None
    except ValueError:
        speed = None
    fraction = min(1.0, max(0.0, seconds / duration)) if seconds is not None and duration else None
    done = values.get("progress") == "end"
    finalizing = fraction is not None and fraction >= 0.995 and not done
    eta = max(0.0, (duration - seconds) / speed) if duration and seconds is not None and speed and not finalizing else None
    return Progress(seconds, fraction, speed, eta, finalizing)


class ProgressDecoder:
    """Reassemble QProcess chunks into complete key/value progress events."""

    def __init__(self) -> None:
        self.buffer = ""
        self.values: dict[str, str] = {}

    def feed(self, chunk: str) -> list[dict[str, str]]:
        self.buffer += chunk
        events: list[dict[str, str]] = []
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if "=" not in line:
                continue
            key, value = line.rstrip("\r").split("=", 1)
            self.values[key] = value
            if key == "progress":
                events.append(self.values.copy())
                self.values.clear()
        return events
