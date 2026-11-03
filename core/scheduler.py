# รัน alert engine แบบ sleep-based loop แยกจาก Streamlit เพื่อใช้ CPU ต่ำ
from __future__ import annotations

import argparse
from pathlib import Path
from threading import Event

from core.alerts import AlertEngine
from core.db import DEFAULT_DB_PATH


def run_scheduler(
    db_path: str | Path = DEFAULT_DB_PATH,
    interval_seconds: int = 60,
    stop_event: Event | None = None,
) -> None:
    event = stop_event or Event()
    engine = AlertEngine(db_path)
    while not event.is_set():
        engine.evaluate()
        event.wait(max(30, min(60, interval_seconds)))


def main() -> None:
    parser = argparse.ArgumentParser(description="MasterControl alert scheduler")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    run_scheduler(args.db, args.interval)


if __name__ == "__main__":
    main()
