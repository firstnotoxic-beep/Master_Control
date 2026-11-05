<!-- ข้อจำกัดด้านความปลอดภัยของ Skill และ quick_note -->
# Skill Security Notes

## quick_note file safety

`quick_note` writes Markdown files using a temporary file created inside `data/notes/` and an atomic replace. It rejects symbolic links, Windows junctions, and paths that resolve outside the notes directory, then checks the final path again after replacement.

**Residual Windows risk:** the implementation uses path-based Python filesystem operations. On Windows, a concurrent process with permission to rename or replace the notes directory can still race the checks and the atomic replace; Python's portable path APIs do not pin the directory identity for the whole operation. The final check detects many resulting link/reparse-point substitutions, but it is not a complete defense against a hostile process that can modify the parent directory concurrently. Keep `data/notes/` and its parent writable only by the trusted user, and do not treat this as an OS-level sandbox. Verify behavior on the target Windows machine before marking it VERIFIED.

## Skill execution and action logs

A Skill action must have a durable `action_log` entry before its `run` function is called. If that preflight write fails, execution is blocked, the Skill is removed from the in-memory registry and disabled in configuration where possible, and the failure is written to `data/logs/skill-failures.log`. If the fallback file cannot be written, the error is allowed to propagate rather than being silently ignored.

## brain_dump file safety

`brain_dump` creates separate timestamped Markdown files with exclusive-create
semantics; it never edits or deletes existing entries. It rejects symbolic links,
junctions, Windows reparse points, and resolved paths outside `data/brain_dump/`,
and rechecks the directory and final file after writing. The action uses only the
framework's `file_write` capability for capture and `file_read` for list/search.

**Residual Windows risk:** like `quick_note`, these checks use portable path-based
operations. A concurrent process with write access to `data/` could attempt to
replace the directory between checks and file creation. The final checks detect
many substitutions but do not pin the directory identity for the entire operation;
this is not an OS sandbox. Keep `data/` and `data/brain_dump/` writable only by
the trusted user, and verify on the target Windows machine before marking VERIFIED.
