# บันทึกโน้ต Markdown เฉพาะโฟลเดอร์ data/notes
import re
from pathlib import Path

NOTES_ROOT = Path("data/notes")
FILENAME = re.compile(r"^[A-Za-z0-9_-]{1,60}\.md$")


def _path(filename: str) -> Path:
    if not isinstance(filename, str) or not FILENAME.fullmatch(filename):
        raise ValueError("filename must be a simple Markdown filename")
    root = NOTES_ROOT.resolve()
    target = (root / filename).resolve()
    if not target.is_relative_to(root):
        raise ValueError("path must remain inside data/notes")
    return target


def run(action_id, params):
    if action_id != "save":
        raise ValueError("unsupported action")
    target = _path(params.filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# " + params.title + "\n\n" + params.body + "\n", encoding="utf-8")
    return {"ok": True, "message": "Saved " + target.name, "verified": False}


def verify(action_id, params, result):
    if action_id != "save" or not result.get("ok"):
        return False
    target = _path(params.filename)
    expected = "# " + params.title + "\n\n" + params.body + "\n"
    return target.is_file() and target.read_text(encoding="utf-8") == expected
