# บันทึกโน้ต Markdown เฉพาะโฟลเดอร์ data/notes
import os
import re
import stat
import tempfile
from pathlib import Path

NOTES_ROOT = Path("data/notes")
FILENAME = re.compile(r"^[A-Za-z0-9_-]{1,60}\.md$")


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


def _path(filename: str) -> Path:
    if not isinstance(filename, str) or not FILENAME.fullmatch(filename):
        raise ValueError("filename must be a simple Markdown filename")
    if _is_link_or_reparse(NOTES_ROOT):
        raise ValueError("notes directory cannot be a symlink or reparse point")
    root = NOTES_ROOT.resolve()
    if _is_link_or_reparse(root):
        raise ValueError("notes directory cannot be a symlink or reparse point")
    target = root / filename
    if _is_link_or_reparse(target):
        raise ValueError("note files cannot be symlinks or reparse points")
    resolved = target.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise ValueError("path must remain inside data/notes")
    return resolved


def run(action_id, params):
    if action_id != "save":
        raise ValueError("unsupported action")
    NOTES_ROOT.mkdir(parents=True, exist_ok=True)
    root = NOTES_ROOT.resolve()
    target = _path(params.filename)
    if target.parent.resolve() != root or not target.is_relative_to(root):
        raise ValueError("path must remain inside data/notes")
    content = "# " + params.title + "\n\n" + params.body + "\n"
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=root, prefix=".quick-note-",
            suffix=".tmp", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        if _path(params.filename) != target:
            raise ValueError("note path changed while writing")
        os.replace(temporary_path, target)
        temporary_path = None
        if _is_link_or_reparse(root) or _is_link_or_reparse(target):
            raise ValueError("final note path cannot be a symlink or reparse point")
        resolved_root = root.resolve(strict=True)
        resolved_target = target.resolve(strict=True)
        if (
            not resolved_target.is_relative_to(resolved_root)
            or resolved_target.parent != resolved_root
        ):
            raise ValueError("final note path must remain inside data/notes")
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return {"ok": True, "message": "Saved " + target.name, "verified": False}


def verify(action_id, params, result):
    if action_id != "save" or not result.get("ok"):
        return False
    target = _path(params.filename)
    expected = "# " + params.title + "\n\n" + params.body + "\n"
    return target.is_file() and target.read_text(encoding="utf-8") == expected
