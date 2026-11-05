# บันทึกโน้ต Markdown เฉพาะโฟลเดอร์ data/notes
import os
import re
import tempfile
from pathlib import Path

NOTES_ROOT = Path("data/notes")
FILENAME = re.compile(r"^[A-Za-z0-9_-]{1,60}\.md$")


def _path(filename: str) -> Path:
    if not isinstance(filename, str) or not FILENAME.fullmatch(filename):
        raise ValueError("filename must be a simple Markdown filename")
    root = NOTES_ROOT.resolve()
    target = root / filename
    if target.is_symlink():
        raise ValueError("symbolic links are not allowed for note files")
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
        if target.is_symlink() or not target.resolve(strict=True).is_relative_to(root):
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
