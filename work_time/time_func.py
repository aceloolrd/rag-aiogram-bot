from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time


def _parse_hhmm(value: str) -> time:
    """Парсим строку вида '08:30' в datetime.time."""
    value = value.strip()
    hh, mm = value.split(":")
    return time(hour=int(hh), minute=int(mm))


@dataclass(frozen=True)
class WorkTimeWindow:
    start: time
    end: time

    @staticmethod
    def from_strings(start: str, end: str) -> "WorkTimeWindow":
        return WorkTimeWindow(start=_parse_hhmm(start), end=_parse_hhmm(end))

    def is_now_allowed(self) -> bool:
        """True, если текущее локальное время попадает в окно.

        Если окно "через ночь" (например 23:00–07:00), тоже корректно обработаем.
        """
        now_t = datetime.now().time()
        if self.start <= self.end:
            return self.start <= now_t <= self.end
        # Окно через полночь
        return now_t >= self.start or now_t <= self.end
