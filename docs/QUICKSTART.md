# Quickstart (Windows 11)

> Use Python 3.12. This is a local development quickstart; Phase 1–4 still need verification on the owner's actual Windows PC. GitHub CI is not device verification.

## 1. Create the environment

Open PowerShell in the repository folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If activation is blocked, use `.\.venv\Scripts\python.exe` instead of `python`; do not change the machine-wide execution policy just for this project.

## 2. Initialize the database and start the dashboard

```powershell
python -c "from core.db import init_db; init_db()"
python -m streamlit run app/dashboard.py
```

The database is `data/mastercontrol.db` (schema v4). The dashboard provides the command box, Skill controls, Pending Approvals, tasks, notifications, and action log.

## 3. Skill CLI

The CLI delegates to the existing `core.commands.handle_command` flow:

```powershell
python -m core.cli skills
python -m core.cli "skill enable quick_note"
python -m core.cli "skill enable quick_note confirm"
python -m core.cli 'run quick_note.save {"filename":"first-note.md","title":"Hello","body":"Saved by MasterControl"}'
python -m core.cli "skill disable quick_note"
```

`skill enable NAME` previews manifest permissions. Review capabilities and risk, then use the `confirm` form. Skills are opt-in and disabled by default.

Other built-in examples (enable each Skill first):

```powershell
python -m core.cli 'run task_list.add {"description":"Review physics notes"}'
python -m core.cli 'run brain_dump.capture {"text":"Remember this idea"}'
python -m core.cli 'run daily_report.generate {}'
```

Use `python -m core.cli --db path\to\test.db status` to select a separate database. The CLI prints JSON and returns non-zero for rejected/failed commands.

## 4. Approvals

The built-in examples above are SAFE/LOW and normally need no approval. MEDIUM and HIGH actions require explicit approval; CRITICAL actions are refused. To create a test approval request:

```powershell
python -m core.cli "test medium"
```

Open the dashboard and use **Pending Approvals** to approve or cancel it. Approval-gated Skill actions are executed by the existing dashboard approval handler after approval.

## 5. Data folders and demo

- `data/mastercontrol.db`: SQLite database.
- `data/notes/`: `quick_note` Markdown notes.
- `data/tasks/tasks.md`: `task_list` data.
- `data/brain_dump/`: append-only Brain Dump notes.
- `data/reports/`: daily reports.
- `data/logs/`: fallback Skill failure log.
- `config/skills.toml`: enabled-Skill list; no Skills are enabled by default.

Run `python -m scripts.demo` to enable and exercise all four example Skills in a temporary directory with a temporary database. The temporary workspace is removed on exit.

**Security:** Skills run as Python code in the MasterControl process; they are not an OS sandbox. Review Skill source before enabling it. Do not put secrets in notes or demo content.

More: [STATUS](STATUS.md) · [Skills](SKILLS.md) · [Security](SECURITY.md) · [Master plan](THE_GRID_MASTER_PLAN.md)
