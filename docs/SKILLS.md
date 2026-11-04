# Skill Framework

Skills are local Python extensions and are disabled unless explicitly enabled by the owner. Review every Skill source file before enabling it. A Skill runs in the same Python process as MasterControl and is not an OS sandbox. Declared capabilities are permission metadata, not isolation.

## Manifest and code template

Use `skill.toml` with these fields:

```toml
name = "my_skill"
version = "1.0.0"
description = "A short explanation."
enabled-by-default = false

[[actions]]
id = "save"
description = "Save a note."
risk = "SAFE"
capabilities = ["file_write"]

[actions.params]
filename = "str"
```

Parameter types supported by the framework are `str`, `int`, `float`, and `bool`. All declared parameters are required; undeclared fields are rejected.

The Python module must provide `run(action_id, params)` and `verify(action_id, params, result)`. Return a mapping with `ok`, `message`, and `verified`. The framework validates the mapping and calls verification separately.

## Risk floors

| Capability | Minimum risk |
|---|---|
| file_read | LOW |
| file_write | SAFE |
| file_delete | HIGH |
| process_control | MEDIUM |
| network | LOW |
| notify | SAFE |
| system_setting | HIGH |

The framework raises lower declared risks automatically. MEDIUM and higher require approval; CRITICAL actions are refused.

Commands: `skills`, `skill enable NAME` (preview), `skill enable NAME confirm` (confirm), `skill disable NAME`, and `run NAME.ACTION {"field":"value"}`.

A Skill is Python code running in the same process as MasterControl, not an operating-system sandbox. Capability declarations are permission metadata, not isolation. Review all source files and enable only trusted Skills.
