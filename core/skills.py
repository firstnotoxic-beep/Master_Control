# โหลด Skill แบบ opt-in พร้อมตรวจสิทธิ์ อนุมัติ และบันทึกผล
from __future__ import annotations

import importlib.util
import json
import logging
import re
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    create_model,
    model_validator,
)

from core.db import DEFAULT_DB_PATH, execute, fetch_all, fetch_one, init_db
from core.permissions import (
    RiskLevel,
    minimum_risk_for_capabilities,
    register_skill_action,
    requires_approval,
    risk_for_action,
    unregister_skill_actions,
)

LOGGER = logging.getLogger(__name__)
DEFAULT_SKILLS_DIR = Path("skills")
DEFAULT_CONFIG_PATH = Path("config/skills.toml")
DEFAULT_FAILURE_LOG_PATH = Path("data/logs/skill-failures.log")
_CAPABILITY_VALUES = {
    "file_read",
    "file_write",
    "file_delete",
    "process_control",
    "network",
    "notify",
    "system_setting",
}
_PARAM_TYPES: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
}
_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,47}$")


class SkillActionManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,47}$")
    description: str = Field(min_length=1, max_length=240)
    risk: RiskLevel
    capabilities: list[Literal[
        "file_read",
        "file_write",
        "file_delete",
        "process_control",
        "network",
        "notify",
        "system_setting",
    ]] = Field(default_factory=list)
    params: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_params(self) -> SkillActionManifest:
        for field_name, field_type in self.params.items():
            if not _NAME_PATTERN.fullmatch(field_name):
                raise ValueError(f"invalid parameter name: {field_name}")
            if field_type not in _PARAM_TYPES:
                raise ValueError(f"unsupported parameter type for {field_name}: {field_type}")
        return self


class SkillManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,47}$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    description: str = Field(min_length=1, max_length=500)
    enabled_by_default: Literal[False] = Field(alias="enabled-by-default")
    actions: list[SkillActionManifest] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_action_ids(self) -> SkillManifest:
        ids = [action.id for action in self.actions]
        if len(ids) != len(set(ids)):
            raise ValueError("action ids must be unique")
        return self


class SkillResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    message: str = Field(max_length=1000)
    verified: bool = False


@dataclass(frozen=True)
class PreparedSkillAction:
    skill_name: str
    action_id: str
    action_key: str
    params: BaseModel
    risk: RiskLevel
    capabilities: tuple[str, ...]

    def approval_details(self) -> str:
        return json.dumps(
            {
                "skill_name": self.skill_name,
                "action_id": self.action_id,
                "params": self.params.model_dump(mode="json"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )


class SkillRegistry:
    """Loads only explicitly enabled, locally installed skills."""

    def __init__(
        self,
        skills_dir: str | Path = DEFAULT_SKILLS_DIR,
        config_path: str | Path = DEFAULT_CONFIG_PATH,
        db_path: str | Path = DEFAULT_DB_PATH,
    ) -> None:
        self.skills_dir = Path(skills_dir)
        self.config_path = Path(config_path)
        self.db_path = Path(db_path)
        self._loaded: dict[str, tuple[SkillManifest, Any]] = {}
        self._errors: dict[str, str] = {}
        init_db(self.db_path)
        self.refresh()

    def _enabled_names(self) -> list[str]:
        if not self.config_path.exists():
            return []
        try:
            with self.config_path.open("rb") as config_file:
                config = tomllib.load(config_file)
            names = config.get("enabled", [])
            if not isinstance(names, list) or any(
                not isinstance(name, str) or not _NAME_PATTERN.fullmatch(name)
                for name in names
            ):
                raise ValueError("config/skills.toml must contain enabled = [skill names]")
            return sorted(set(names))
        except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
            LOGGER.error("Cannot read skills config %s: %s", self.config_path, error)
            self._errors["<config>"] = str(error)
            return []

    def _write_enabled_names(self, names: list[str]) -> None:
        if any(not _NAME_PATTERN.fullmatch(name) for name in names):
            raise ValueError("invalid skill name in enabled list")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["enabled = ["]
        lines.extend(f"  {json.dumps(name)}," for name in sorted(set(names)))
        lines.append("]")
        self.config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _skill_folders(self) -> dict[str, Path]:
        if not self.skills_dir.exists():
            return {}
        folders: dict[str, Path] = {}
        for folder in self.skills_dir.iterdir():
            if (
                folder.is_dir()
                and not folder.is_symlink()
                and _NAME_PATTERN.fullmatch(folder.name)
            ):
                folders[folder.name] = folder
        return folders

    def _read_manifest(self, name: str, folder: Path | None = None) -> SkillManifest:
        if not _NAME_PATTERN.fullmatch(name):
            raise ValueError("invalid skill name")
        directory = folder or self._skill_folders().get(name)
        if directory is None or directory.is_symlink():
            raise FileNotFoundError(f"skill folder not found: {name}")
        manifest_path = directory / "skill.toml"
        with manifest_path.open("rb") as manifest_file:
            raw = tomllib.load(manifest_file)
        manifest = SkillManifest.model_validate(raw)
        if manifest.name != name:
            raise ValueError("manifest name must match its folder name")
        if manifest.enabled_by_default is not False:
            raise ValueError("enabled-by-default must be false")
        return manifest

    def _set_state(
        self,
        name: str,
        enabled: bool,
        version: str = "",
        last_error: str | None = None,
    ) -> None:
        execute(
            """
            INSERT INTO skill_state (name, enabled, version, last_error, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                enabled = excluded.enabled,
                version = CASE WHEN excluded.version = '' THEN skill_state.version
                               ELSE excluded.version END,
                last_error = excluded.last_error,
                updated_at = CURRENT_TIMESTAMP
            """,
            (name, int(enabled), version, last_error),
            self.db_path,
        )

    def _load_module(self, name: str, folder: Path) -> Any:
        module_path = folder / "skill.py"
        if not module_path.is_file():
            raise FileNotFoundError(f"skill.py not found for {name}")
        module_name = f"mastercontrol_skill_{name}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load skill module: {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(module_name, None)
            raise
        if not callable(getattr(module, "run", None)):
            raise TypeError("skill.py must define run(action_id, params)")
        if not callable(getattr(module, "verify", None)):
            raise TypeError("skill.py must define verify(action_id, params, result)")
        return module

    def refresh(self) -> None:
        for name in self._loaded:
            sys.modules.pop(f"mastercontrol_skill_{name}", None)
        unregister_skill_actions("skill.")
        self._loaded.clear()
        self._errors = {}
        enabled_names = set(self._enabled_names())
        folders = self._skill_folders()

        for name, folder in folders.items():
            if name not in enabled_names:
                state = fetch_one(
                    "SELECT version FROM skill_state WHERE name = ?", (name,), self.db_path
                )
                self._set_state(name, False, state["version"] if state else "")
                continue
            try:
                manifest = self._read_manifest(name, folder)
                module = self._load_module(name, folder)
                self._loaded[name] = (manifest, module)
                for action in manifest.actions:
                    action_key = f"skill.{name}.{action.id}"
                    final_risk = minimum_risk_for_capabilities(action.capabilities, action.risk)
                    if final_risk != action.risk:
                        LOGGER.warning(
                            "Raised Skill action risk %s from %s to %s due to capabilities %s",
                            action_key, action.risk.value, final_risk.value, action.capabilities,
                        )
                    register_skill_action(action_key, final_risk)
                self._set_state(name, True, manifest.version, None)
            except Exception as error:
                message = str(error)[:1000]
                LOGGER.exception("Skipping invalid skill %s", name)
                self._loaded.pop(name, None)
                unregister_skill_actions(f"skill.{name}.")
                sys.modules.pop(f"mastercontrol_skill_{name}", None)
                self._errors[name] = message
                try:
                    self._set_state(name, False, last_error=message)
                except Exception:
                    LOGGER.exception("Could not persist failed Skill state for %s", name)

        for name in sorted(enabled_names - set(folders)):
            message = f"enabled skill folder does not exist: {name}"
            LOGGER.warning(message)
            self._errors[name] = message

    def preview(self, name: str) -> dict[str, Any]:
        manifest = self._read_manifest(name)
        actions = []
        for action in manifest.actions:
            final_risk = minimum_risk_for_capabilities(action.capabilities, action.risk)
            actions.append(
                {
                    "id": action.id,
                    "description": action.description,
                    "requested_capabilities": list(action.capabilities),
                    "declared_risk": action.risk.value,
                    "final_risk": final_risk.value,
                    "risk_raised": final_risk != action.risk,
                }
            )
        return {
            "name": manifest.name,
            "version": manifest.version,
            "description": manifest.description,
            "enabled_by_default": manifest.enabled_by_default,
            "actions": actions,
        }

    def list_skills(self) -> list[dict[str, Any]]:
        state_rows = {
            row["name"]: dict(row)
            for row in fetch_all("SELECT * FROM skill_state", db_path=self.db_path)
        }
        items: list[dict[str, Any]] = []
        for name, folder in sorted(self._skill_folders().items()):
            row = state_rows.get(name, {})
            try:
                preview = self.preview(name)
                items.append(
                    {
                        "name": name,
                        "installed": True,
                        "enabled": bool(row.get("enabled", 0)) and name in self._loaded,
                        "version": preview["version"],
                        "description": preview["description"],
                        "actions": preview["actions"],
                        "last_error": self._errors.get(name) or row.get("last_error"),
                    }
                )
            except (
                FileNotFoundError,
                OSError,
                TypeError,
                ValueError,
                ValidationError,
                tomllib.TOMLDecodeError,
            ) as error:
                LOGGER.warning("Invalid skill manifest %s: %s", name, error)
                items.append(
                    {
                        "name": name,
                        "installed": True,
                        "enabled": False,
                        "version": row.get("version", ""),
                        "description": "Invalid manifest",
                        "actions": [],
                        "last_error": str(error)[:1000],
                    }
                )
        return items

    def _write_plain_failure_log(self, action: str, message: str) -> None:
        log_path = DEFAULT_FAILURE_LOG_PATH
        log_path.parent.mkdir(parents=True, exist_ok=True)
        record = json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "error": message[:2000],
            },
            ensure_ascii=False,
        )
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(record + "\n")

    def _write_failure_log(self, action: str, message: str, risk: str = "HIGH") -> None:
        try:
            execute(
                """
                INSERT INTO action_log (action, details, risk_level, status, actor)
                VALUES (?, ?, ?, 'failed', 'skill')
                """,
                (action, json.dumps({"error": message[:1000]}), risk),
                self.db_path,
            )
        except Exception as error:
            LOGGER.exception("Could not persist Skill failure log for %s", action)
            self._write_plain_failure_log(
                action, f"Database action-log write failed: {error}; {message}"
            )

    def _disable_after_action_log_failure(self, name: str, message: str) -> None:
        self._loaded.pop(name, None)
        unregister_skill_actions(f"skill.{name}.")
        sys.modules.pop(f"mastercontrol_skill_{name}", None)
        self._errors[name] = message[:1000]
        action = f"skill.{name}.action_log_failure"
        try:
            enabled_names = self._enabled_names()
            if "<config>" in self._errors:
                raise RuntimeError("could not read enabled Skills configuration")
            self._write_enabled_names([item for item in enabled_names if item != name])
        except Exception as error:
            LOGGER.exception("Could not persist disabled config for Skill %s", name)
            self._write_plain_failure_log(
                action, f"Skill disabled in memory; config disable failed: {error}"
            )
        try:
            self._set_state(name, False, last_error=message[:1000])
        except Exception as error:
            LOGGER.exception("Could not persist disabled DB state for Skill %s", name)
            self._write_plain_failure_log(
                action, f"Skill disabled in memory; DB state update failed: {error}"
            )

    def _rollback_skill(self, name: str, version: str, message: str) -> None:
        try:
            enabled_names = self._enabled_names()
            self._write_enabled_names([item for item in enabled_names if item != name])
        except Exception:
            LOGGER.exception("Could not remove failed Skill %s from enabled config", name)
        self._loaded.pop(name, None)
        unregister_skill_actions(f"skill.{name}.")
        sys.modules.pop(f"mastercontrol_skill_{name}", None)
        self._errors[name] = message[:1000]
        try:
            self._set_state(name, False, version, message[:1000])
        except Exception:
            LOGGER.exception("Could not persist disabled state for failed Skill %s", name)

    def enable(self, name: str) -> dict[str, Any]:
        version = ""
        try:
            preview = self.preview(name)
            version = preview["version"]
        except Exception as error:
            message = str(error)[:1000]
            LOGGER.exception("Cannot enable invalid Skill %s", name)
            self._rollback_skill(name, version, message)
            self._write_failure_log(f"skill.{name}.enable", message)
            return {"ok": False, "message": message, "preview": None}

        enabled_names = self._enabled_names()
        if name not in enabled_names:
            enabled_names.append(name)
        try:
            self._write_enabled_names(enabled_names)
            self.refresh()
            if name not in self._loaded:
                message = self._errors.get(name, "skill failed to load")
                self._rollback_skill(name, version, message)
                self._write_failure_log(f"skill.{name}.enable", message)
                return {"ok": False, "message": message, "preview": preview}
            return {
                "ok": True,
                "message": f"Enabled skill: {name}",
                "preview": preview,
            }
        except Exception as error:
            message = str(error)[:1000]
            LOGGER.exception("Could not enable skill %s", name)
            self._rollback_skill(name, version, message)
            self._write_failure_log(f"skill.{name}.enable", message)
            return {"ok": False, "message": message, "preview": preview}

    @classmethod
    def disable_without_loading(
        cls,
        name: str,
        db_path: str | Path = DEFAULT_DB_PATH,
        config_path: str | Path | None = None,
    ) -> dict[str, Any]:
        if not _NAME_PATTERN.fullmatch(name):
            return {"ok": False, "message": "Invalid skill name"}
        config_file = Path(config_path or DEFAULT_CONFIG_PATH)
        try:
            init_db(db_path)
            if config_file.exists():
                with config_file.open("rb") as handle:
                    config = tomllib.load(handle)
                enabled_names = config.get("enabled", [])
                if not isinstance(enabled_names, list) or any(
                    not isinstance(item, str) or not _NAME_PATTERN.fullmatch(item)
                    for item in enabled_names
                ):
                    raise ValueError("config/skills.toml must contain enabled = [skill names]")
            else:
                enabled_names = []
            remaining = sorted({item for item in enabled_names if item != name})
            config_file.parent.mkdir(parents=True, exist_ok=True)
            lines = ["enabled = ["]
            lines.extend(f"  {json.dumps(item)}," for item in remaining)
            lines.append("]")
            config_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            state = fetch_one(
                "SELECT version FROM skill_state WHERE name = ?", (name,), db_path
            )
            version = state["version"] if state else ""
            execute(
                """
                INSERT INTO skill_state (name, enabled, version, last_error, updated_at)
                VALUES (?, 0, ?, NULL, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    enabled = 0,
                    last_error = NULL,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (name, version),
                db_path,
            )
        except (OSError, ValueError, tomllib.TOMLDecodeError) as error:
            return {"ok": False, "message": str(error)}
        unregister_skill_actions(f"skill.{name}.")
        sys.modules.pop(f"mastercontrol_skill_{name}", None)
        return {"ok": True, "message": f"Disabled skill: {name}"}

    def disable(self, name: str) -> dict[str, Any]:
        result = self.disable_without_loading(
            name, db_path=self.db_path, config_path=self.config_path
        )
        if result["ok"]:
            self._loaded.pop(name, None)
        return result

    def prepare_action(
        self, skill_name: str, action_id: str, payload: dict[str, Any]
    ) -> PreparedSkillAction:
        loaded = self._loaded.get(skill_name)
        if loaded is None:
            raise ValueError(f"skill is not enabled or did not load: {skill_name}")
        manifest, _module = loaded
        action = next((item for item in manifest.actions if item.id == action_id), None)
        if action is None:
            raise ValueError(f"unknown action: {skill_name}.{action_id}")
        if not isinstance(payload, dict):
            raise TypeError("action arguments must be a JSON object")
        fields = {
            key: (_PARAM_TYPES[field_type], ...)
            for key, field_type in action.params.items()
        }
        params_model = create_model(
            f"{manifest.name}_{action.id}_Params",
            __config__=ConfigDict(extra="forbid"),
            **fields,
        )
        try:
            params = params_model.model_validate(payload)
        except ValidationError as error:
            raise ValueError(f"invalid action parameters: {error}") from error
        action_key = f"skill.{skill_name}.{action_id}"
        final_risk = minimum_risk_for_capabilities(action.capabilities, action.risk)
        if risk_for_action(action_key) != final_risk:
            raise PermissionError("skill action is not registered in the active permission allowlist")
        return PreparedSkillAction(
            skill_name=skill_name,
            action_id=action_id,
            action_key=action_key,
            params=params,
            risk=final_risk,
            capabilities=tuple(action.capabilities),
        )

    def execute_action(
        self, prepared: PreparedSkillAction, approval_id: int | None = None
    ) -> dict[str, Any]:
        try:
            if not isinstance(prepared.params, BaseModel):
                raise TypeError("prepared parameters are invalid")
            canonical = self.prepare_action(
                prepared.skill_name,
                prepared.action_id,
                prepared.params.model_dump(mode="json"),
            )
            if (
                prepared.action_key != canonical.action_key
                or prepared.risk != canonical.risk
                or prepared.capabilities != canonical.capabilities
                or prepared.params.model_dump(mode="json")
                != canonical.params.model_dump(mode="json")
            ):
                raise PermissionError("Prepared action does not match the active manifest")
            prepared = canonical
        except (AttributeError, TypeError, ValueError, PermissionError) as error:
            return {
                "ok": False,
                "message": f"Prepared action rejected: {str(error)[:500]}",
                "verified": False,
            }

        if prepared.risk == RiskLevel.CRITICAL:
            result = SkillResult(ok=False, message="CRITICAL actions cannot be executed", verified=False)
            self._write_run_log(prepared, result, "refused", approval_id)
            return result.model_dump()
        approval_required = requires_approval(prepared.action_key)
        if approval_required and approval_id is None:
            return {
                "ok": False,
                "message": "This skill action requires approval before execution",
                "verified": False,
                "approval_required": True,
            }
        if approval_id is not None:
            approval = fetch_one(
                """
                SELECT approvals.status, action_log.id AS action_log_id,
                       action_log.action, action_log.details, action_log.risk_level,
                       action_log.status AS action_status
                FROM approvals
                JOIN action_log ON action_log.id = approvals.action_log_id
                WHERE approvals.id = ?
                """,
                (approval_id,),
                self.db_path,
            )
            if (
                approval is None
                or approval["status"] != "approved"
                or approval["action_status"] != "approved"
                or approval["action"] != prepared.action_key
                or approval["risk_level"] != prepared.risk.value
            ):
                result = SkillResult(ok=False, message="Approval is missing, invalid, or does not match this action", verified=False)
                self._write_run_log(prepared, result, "refused", approval_id)
                return result.model_dump()
            try:
                requested = json.loads(approval["details"])
            except (TypeError, json.JSONDecodeError):
                requested = {}
            expected = {
                "skill_name": prepared.skill_name,
                "action_id": prepared.action_id,
                "params": prepared.params.model_dump(mode="json"),
            }
            if requested != expected:
                result = SkillResult(ok=False, message="Approved parameters do not match the requested action", verified=False)
                self._write_run_log(prepared, result, "refused", approval_id)
                return result.model_dump()

        manifest, module = self._loaded[prepared.skill_name]
        action_key = prepared.action_key
        if risk_for_action(action_key) != prepared.risk:
            result = SkillResult(ok=False, message="Permission changed; reload and request approval again", verified=False)
            self._write_run_log(prepared, result, "refused", approval_id)
            return result.model_dump()

        try:
            action_log_id = self._write_run_log(
                prepared,
                SkillResult(ok=False, message="Action execution started", verified=False),
                "started",
                approval_id,
            )
        except Exception as error:
            message = str(error)[:1000]
            LOGGER.exception("Blocking Skill action because its action log could not be written")
            self._disable_after_action_log_failure(prepared.skill_name, message)
            self._write_plain_failure_log(
                action_key,
                f"Execution blocked before Skill code ran because DB action-log write failed: {message}",
            )
            return {
                "ok": False,
                "message": "Action log could not be written; Skill was disabled and execution was blocked",
                "verified": False,
            }

        try:
            raw_result = module.run(prepared.action_id, prepared.params)
            skill_result = SkillResult.model_validate(raw_result)
            verified = False
            if skill_result.ok:
                verified = bool(module.verify(prepared.action_id, prepared.params, skill_result.model_dump()))
            final_result = SkillResult(
                ok=skill_result.ok and verified,
                message=skill_result.message if verified else (
                    skill_result.message if not skill_result.ok else "Action ran, but verification failed"
                ),
                verified=verified,
            )
            self._set_state(prepared.skill_name, True, manifest.version, None if final_result.ok else final_result.message)
            self._write_run_log(
                prepared,
                final_result,
                "completed" if final_result.ok else "failed",
                approval_id,
                action_log_id=action_log_id,
            )
            return final_result.model_dump()
        except Exception as error:
            message = str(error)[:1000]
            LOGGER.exception("Skill action failed: %s", action_key)
            self._rollback_skill(prepared.skill_name, manifest.version, message)
            result = SkillResult(
                ok=False,
                message=f"Skill action failed: {message}",
                verified=False,
            )
            try:
                self._write_run_log(
                    prepared, result, "failed", approval_id, action_log_id=action_log_id
                )
            except Exception:
                LOGGER.exception("Could not update the Skill action log: %s", action_key)
                self._write_failure_log(action_key, message, prepared.risk.value)
            return result.model_dump()

    def _write_run_log(
        self,
        prepared: PreparedSkillAction,
        result: SkillResult,
        status: str,
        approval_id: int | None,
        action_log_id: int | None = None,
    ) -> int:
        details = json.dumps(
            {
                "skill_name": prepared.skill_name,
                "action_id": prepared.action_id,
                "params": prepared.params.model_dump(mode="json"),
                "result": result.model_dump(),
                "requested_capabilities": list(prepared.capabilities),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        if action_log_id is None and approval_id is not None:
            row = fetch_one(
                "SELECT action_log_id FROM approvals WHERE id = ?",
                (approval_id,),
                self.db_path,
            )
            if row is not None:
                action_log_id = int(row["action_log_id"])
        if action_log_id is not None:
            execute(
                """
                UPDATE action_log SET details = ?, status = ?, actor = 'skill'
                WHERE id = ?
                """,
                (details, status, action_log_id),
                self.db_path,
            )
            return action_log_id
        return execute(
            """
            INSERT INTO action_log (action, details, risk_level, status, actor)
            VALUES (?, ?, ?, ?, 'skill')
            """,
            (prepared.action_key, details, prepared.risk.value, status),
            self.db_path,
        )


def execute_approved_skill(
    approval_id: int, db_path: str | Path = DEFAULT_DB_PATH
) -> dict[str, Any]:
    """Run a previously approved Skill request from the existing dashboard approval flow."""
    row = fetch_one(
        """
        SELECT approvals.status, action_log.action, action_log.details, action_log.risk_level
        FROM approvals
        JOIN action_log ON action_log.id = approvals.action_log_id
        WHERE approvals.id = ?
        """,
        (approval_id,),
        db_path,
    )
    if row is None or row["status"] != "approved" or not str(row["action"]).startswith("skill."):
        return {"ok": False, "message": "No approved Skill action found", "verified": False}
    try:
        requested = json.loads(row["details"])
        registry = SkillRegistry(db_path=db_path)
        prepared = registry.prepare_action(
            requested["skill_name"],
            requested["action_id"],
            requested["params"],
        )
        if prepared.action_key != row["action"] or prepared.risk.value != row["risk_level"]:
            raise PermissionError("Approved action no longer matches the active manifest")
        return registry.execute_action(prepared, approval_id=approval_id)
    except Exception as error:
        message = str(error)[:1000]
        LOGGER.exception("Could not execute approved Skill action %s", approval_id)
        execute(
            "UPDATE action_log SET status = 'failed', details = ? WHERE id = (SELECT action_log_id FROM approvals WHERE id = ?)",
            (json.dumps({"error": message}), approval_id),
            db_path,
        )
        return {"ok": False, "message": message, "verified": False}
