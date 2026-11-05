# จัดการรายการงานในไฟล์ Markdown ภายใต้ data/tasks
from __future__ import annotations

import os
import re
import stat
import tempfile
from pathlib import Path

TASKS_ROOT = Path("data/tasks")
TASKS_FILE_NAME = "tasks.md"
_DESCRIPTION_LIMIT = 80
_TASK_LINE = re.compile(r"^- \[( |x)\] #(\d+) (.+)$")


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


def _tasks_path() -> Path:
    if _is_link_or_reparse(TASKS_ROOT):
        raise ValueError("tasks directory cannot be a symlink or reparse point")
    root = TASKS_ROOT.resolve()
    if _is_link_or_reparse(root):
        raise ValueError("tasks directory cannot be a symlink or reparse point")
    target = root / TASKS_FILE_NAME
    if _is_link_or_reparse(target):
        raise ValueError("tasks file cannot be a symlink or reparse point")
    resolved = target.resolve(strict=False)
    if not resolved.is_relative_to(root) or resolved.parent != root:
        raise ValueError("task path must remain inside data/tasks")
    return resolved


def _read_tasks() -> list[dict]:
    target = _tasks_path()
    if not target.exists():
        return []
    tasks = []
    seen_ids = set()
    for line in target.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        match = _TASK_LINE.fullmatch(line)
        if match is None:
            raise ValueError("tasks.md contains an invalid task entry")
        task_id = int(match.group(2))
        if task_id < 1 or task_id in seen_ids:
            raise ValueError("tasks.md contains an invalid or duplicate task ID")
        seen_ids.add(task_id)
        tasks.append(
            {
                "id": task_id,
                "done": match.group(1) == "x",
                "description": match.group(3),
            }
        )
    return tasks


def _write_tasks(tasks: list[dict]) -> None:
    if _is_link_or_reparse(TASKS_ROOT):
        raise ValueError("tasks directory cannot be a symlink or reparse point")
    TASKS_ROOT.mkdir(parents=True, exist_ok=True)
    root = TASKS_ROOT.resolve()
    target = _tasks_path()
    if target.parent.resolve() != root or not target.is_relative_to(root):
        raise ValueError("task path must remain inside data/tasks")
    content = "".join(
        f"- [{'x' if item['done'] else ' '}] #{item['id']} {item['description']}\n"
        for item in tasks
    )
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=root,
            prefix=".task-list-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        if _tasks_path() != target:
            raise ValueError("task path changed while writing")
        os.replace(temporary_path, target)
        temporary_path = None
        if _is_link_or_reparse(root) or _is_link_or_reparse(target):
            raise ValueError("final task path cannot be a symlink or reparse point")
        resolved_root = root.resolve(strict=True)
        resolved_target = target.resolve(strict=True)
        if (
            not resolved_target.is_relative_to(resolved_root)
            or resolved_target.parent != resolved_root
        ):
            raise ValueError("final task path must remain inside data/tasks")
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _validate_description(description: str) -> str:
    if not isinstance(description, str):
        raise TypeError("description must be text")
    value = description.strip()
    if not value or len(value) > _DESCRIPTION_LIMIT:
        raise ValueError(f"description must contain 1-{_DESCRIPTION_LIMIT} characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError("description cannot contain control characters or newlines")
    return value


def _validate_task_id(task_id: int) -> int:
    if isinstance(task_id, bool) or not isinstance(task_id, int) or task_id < 1:
        raise ValueError("task_id must be a positive integer")
    return task_id


def run(action_id, params):
    if action_id == "list":
        tasks = _read_tasks()
        if not tasks:
            message = "No tasks yet."
        else:
            visible = tasks[:8]
            lines = [
                f"- [{'x' if item['done'] else ' '}] #{item['id']} {item['description']}"
                for item in visible
            ]
            if len(tasks) > len(visible):
                lines.append(f"... and {len(tasks) - len(visible)} more")
            message = f"Tasks ({len(tasks)}):\n" + "\n".join(lines)
        return {"ok": True, "message": message, "verified": False}

    tasks = _read_tasks()
    if action_id == "add":
        try:
            description = _validate_description(params.description)
        except (TypeError, ValueError) as error:
            return {"ok": False, "message": str(error), "verified": False}
        task_id = max((item["id"] for item in tasks), default=0) + 1
        tasks.append({"id": task_id, "done": False, "description": description})
        _write_tasks(tasks)
        return {"ok": True, "message": f"Added task #{task_id}: {description}", "verified": False}

    try:
        task_id = _validate_task_id(params.task_id)
    except ValueError as error:
        return {"ok": False, "message": str(error), "verified": False}
    task = next((item for item in tasks if item["id"] == task_id), None)
    if task is None:
        return {"ok": False, "message": f"task #{task_id} was not found", "verified": False}
    if action_id == "done":
        task["done"] = True
        _write_tasks(tasks)
        return {"ok": True, "message": f"Completed task #{task_id}", "verified": False}
    if action_id == "remove":
        tasks = [item for item in tasks if item["id"] != task_id]
        _write_tasks(tasks)
        return {"ok": True, "message": f"Removed task #{task_id}", "verified": False}
    raise ValueError("unsupported action")


def verify(action_id, params, result):
    if not result.get("ok"):
        return False
    tasks = _read_tasks()
    if action_id == "list":
        return True
    if action_id == "add":
        description = _validate_description(params.description)
        return any(
            item["description"] == description and not item["done"]
            for item in tasks
        )
    task_id = _validate_task_id(params.task_id)
    if action_id == "done":
        return any(item["id"] == task_id and item["done"] for item in tasks)
    if action_id == "remove":
        return all(item["id"] != task_id for item in tasks)
    return False
