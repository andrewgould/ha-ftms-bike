"""Running totals, like a smart plug's energy counter, for the ride and for all time.

The console's distance, calories and elapsed time count from when it woke, and drop
back to zero whenever an app starts or ends a workout, so they can't be used as
totals directly. Instead each reading adds what changed since the last one, and a
reading lower than the last counts as a fresh start from zero. Work is power
integrated over time, which the console doesn't count at all.

No Home Assistant imports, so the tests can load it on its own.
"""

from __future__ import annotations

# Console counters, keyed as ftms.parse_indoor_bike_data names them: metres, kcal, seconds.
COUNTERS = ("distance", "energy", "elapsed")
FIELDS = (*COUNTERS, "work")  # work is in joules
# Longest gap between power readings to count as continuous. Consoles stop sending
# when nobody pedals, so a longer gap is a pause, not minutes at the last power.
MAX_GAP = 5.0


def _zeros() -> dict[str, float]:
    return dict.fromkeys(FIELDS, 0.0)


class Tally:
    def __init__(self, saved: dict | None = None) -> None:
        saved = saved or {}
        self.total = _zeros() | saved.get("total", {})
        self.ride = _zeros() | saved.get("ride", {})
        self._last: dict[str, float] = {}
        self._power: float | None = None
        self._power_at = 0.0

    def as_dict(self) -> dict:
        return {"total": self.total, "ride": self.ride}

    def start_ride(self) -> None:
        self.ride = _zeros()
        self.stop()

    def stop(self) -> None:
        """Forget the last readings, so the next ones start a new baseline."""
        self._last = {}
        self._power = None

    def add(self, fields: dict[str, float], now: float) -> bool:
        """Count one notification's fields. now is in seconds (monotonic). True if anything grew."""
        changes = _zeros()
        for key in COUNTERS:
            if key not in fields:
                continue
            value, last = fields[key], self._last.get(key)
            self._last[key] = value
            if last is None:
                continue  # the first reading is only a baseline
            changes[key] = value - last if value >= last else value
        if "power" in fields:
            if self._power is not None:
                changes["work"] = self._power * min(now - self._power_at, MAX_GAP)
            self._power, self._power_at = max(fields["power"], 0), now
        grew = False
        for key, change in changes.items():
            if change > 0:
                self.ride[key] += change
                self.total[key] += change
                grew = True
        return grew
