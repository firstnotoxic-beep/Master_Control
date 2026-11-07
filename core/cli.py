# CLI แบบเบาสำหรับเรียกใช้คำสั่ง MasterControl ที่มีอยู่
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path

from core.commands import handle_command
from core.db import DEFAULT_DB_PATH


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a MasterControl command without opening the dashboard."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"SQLite database path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="MasterControl command, for example: skills or 'status'",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command_text = " ".join(args.command).strip()
    if not command_text:
        parser.print_usage(sys.stderr)
        return 2

    try:
        result = handle_command(command_text, args.db)
    except (OSError, RuntimeError, ValueError, sqlite3.Error) as error:
        print(f"MasterControl command failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
