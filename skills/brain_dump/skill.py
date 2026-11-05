# จับข้อความอิสระเป็นบันทึกแบบเพิ่มอย่างเดียวใน data/brain_dump
from __future__ import annotations

import os
import re
import stat
import uuid
from datetime import UTC, datetime
from pathlib import Path

DATA_ROOT = Path("data")
BRAIN_DUMP_ROOT = DATA_ROOT / "brain_dump"
_MAX_TEXT_LENGTH = 5000
_MAX_SEARCH_LENGTH = 100
_MAX_LIST_LIMIT = 20
_FILENAME_PATTERN = re.compile(r"^\d{8}T\d{12}Z-[a-f0-9]{32}\.md$")


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction) and is_junction():
        return True
    try:
        attributes = path.lstat().st_file_attributes
    except (AttributeError, FileNotFoundError):
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _safe_root(*, create: bool = False) -> Path:
    if _is_link_or_reparse(DATA_ROOT):
        raise ValueError("data directory cannot be a symlink or reparse point")
    if create:
        DATA_ROOT.mkdir(parents=True, exist_ok=True)
    if not DATA_ROOT.is_dir():
        raise ValueError("data directory does not exist")
    data_root = DATA_ROOT.resolve(strict=True)
    if _is_link_or_reparse(BRAIN_DUMP_ROOT):
        raise ValueError("brain dump directory cannot be a symlink or reparse point")
    if create:
        BRAIN_DUMP_ROOT.mkdir(exist_ok=True)
    if not BRAIN_DUMP_ROOT.is_dir():
        raise ValueError("brain dump directory does not exist")
    root = BRAIN_DUMP_ROOT.resolve(strict=True)
    if root.parent != data_root or _is_link_or_reparse(root):
        raise ValueError("brain dump path must remain inside data/brain_dump")
    return root


def _safe_note_path(filename: str, root: Path) -> Path:
    if not isinstance(filename, str) or not _FILENAME_PATTERN.fullmatch(filename):
        raise ValueError("invalid brain dump filename")
    target = root / filename
    if _is_link_or_reparse(target):
        raise ValueError("brain dump files cannot be symlinks or reparse points")
    resolved = target.resolve(strict=False)
    if resolved.parent != root or not resolved.is_relative_to(root):
        raise ValueError("brain dump file must remain inside data/brain_dump")
    return resolved


def _note_files() -> list[Path]:
    root = _safe_root()
    files = []
    for entry in root.iterdir():
        if entry.suffix.lower() != ".md":
            continue
        target = _safe_note_path(entry.name, root)
        if _is_link_or_reparse(entry) or not target.is_file():
            raise ValueError("brain dump entries must be regular files")
        if target.resolve(strict=True).parent != root:
            raise ValueError("brain dump file must remain inside data/brain_dump")
        files.append(target)
    return sorted(files, key=lambda item: item.name, reverse=True)


def _validate_text(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("text must be a string")
    text = value.strip()
    if not text:
        raise ValueError("text cannot be empty")
    if len(text) > _MAX_TEXT_LENGTH:
        raise ValueError(f"text cannot exceed {_MAX_TEXT_LENGTH} characters")
    if any(ord(character) < 32 and character not in "\n\t" for character in text):
        raise ValueError("text contains unsupported control characters")
    if "\x7f" in text:
        raise ValueError("text contains unsupported control characters")
    return text


def _validate_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit must be an integer")
    if not 1 <= limit <= _MAX_LIST_LIMIT:
        raise ValueError(f"limit must be between 1 and {_MAX_LIST_LIMIT}")
    return limit


def _validate_keyword(keyword: str) -> str:
    if not isinstance(keyword, str):
        raise TypeError("keyword must be a string")
    value = keyword.strip()
    if not value:
        raise ValueError("search keyword cannot be empty")
    if len(value) > _MAX_SEARCH_LENGTH:
        raise ValueError(f"keyword cannot exceed {_MAX_SEARCH_LENGTH} characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError("keyword contains unsupported control characters")
    return value


def _capture(text: str) -> str:
    content = _validate_text(text)
    root = _safe_root(create=True)
    timestamp = datetime.now(UTC)
    stamp = timestamp.strftime("%Y%m%dT%H%M%S%fZ")
    filename = f"{stamp}-{uuid.uuid4().hex}.md"
    target = _safe_note_path(filename, root)
    record = f"# {timestamp.isoformat()}\n\n{content}\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(target, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as note_file:
        if not stat.S_ISREG(os.fstat(note_file.fileno()).st_mode):
            raise ValueError("brain dump target must be a regular file")
        note_file.write(record)
        note_file.flush()
        os.fsync(note_file.fileno())
    if _safe_root() != root or _safe_note_path(filename, root) != target:
        raise ValueError("brain dump path changed while writing")
    if _is_link_or_reparse(root) or _is_link_or_reparse(target):
        raise ValueError("final brain dump path cannot be a symlink or reparse point")
    resolved_root = root.resolve(strict=True)
    resolved_target = target.resolve(strict=True)
    if (
        resolved_target.parent != resolved_root
        or not resolved_target.is_relative_to(resolved_root)
    ):
        raise ValueError("final brain dump path must remain inside data/brain_dump")
    return filename


def run(action_id, params):
    if action_id == "capture":
        filename = _capture(params.text)
        return {"ok": True, "message": f"Captured: {filename}", "verified": False}

    if action_id == "list":
        limit = _validate_limit(params.limit)
        files = _note_files()[:limit]
        if not files:
            message = "No brain dump notes yet."
        else:
            entries = [
                f"## {path.name}\n{path.read_text(encoding='utf-8').rstrip()}"
                for path in files
            ]
            message = f"Latest {len(files)} brain dump note(s):\n" + "\n\n".join(entries)
        return {"ok": True, "message": message, "verified": False}

    if action_id == "search":
        keyword = _validate_keyword(params.keyword).casefold()
        matches = []
        for path in _note_files():
            content = path.read_text(encoding="utf-8")
            if keyword in content.casefold():
                matches.append(f"## {path.name}\n{content.rstrip()}")
            if len(matches) >= _MAX_LIST_LIMIT:
                break
        message = (
            f"Found {len(matches)} note(s) for '{params.keyword.strip()}':\n"
            + ("\n\n".join(matches) if matches else "No matches.")
        )
        return {"ok": True, "message": message, "verified": False}

    raise ValueError("unsupported action")


def verify(action_id, params, result):
    if not result.get("ok"):
        return False
    if action_id == "capture":
        content = _validate_text(params.text)
        filename = result.get("message", "").removeprefix("Captured: ")
        root = _safe_root()
        target = _safe_note_path(filename, root)
        return target.is_file() and target.read_text(encoding="utf-8").endswith(
            f"\n\n{content}\n"
        )
    if action_id == "list":
        _validate_limit(params.limit)
        _note_files()
        return True
    if action_id == "search":
        _validate_keyword(params.keyword)
        _note_files()
        return True
    return False
