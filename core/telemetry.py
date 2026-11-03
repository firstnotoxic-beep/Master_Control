# อ่าน telemetry ของเครื่องแบบ read-only โดยไม่แก้ไขโปรเซสหรือการตั้งค่าระบบ
from __future__ import annotations

import subprocess
from typing import Any

import psutil


def _memory_mb(bytes_used: int) -> float:
    return round(bytes_used / (1024 * 1024), 2)


def _gpu_info() -> dict[str, Any]:
    empty = {"name": None, "vram_used_mb": None, "vram_total_mb": None, "temperature_c": None}
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return empty
    if completed.returncode != 0 or not completed.stdout.strip():
        return empty
    try:
        name, used, total, temperature = [part.strip() for part in completed.stdout.splitlines()[0].split(",")]
        return {
            "name": name or None,
            "vram_used_mb": float(used),
            "vram_total_mb": float(total),
            "temperature_c": float(temperature),
        }
    except (ValueError, IndexError):
        return empty


def top_processes(limit: int = 5) -> list[dict[str, Any]]:
    processes: list[dict[str, Any]] = []
    for process in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            memory = process.info["memory_info"].rss
            processes.append(
                {
                    "name": process.info.get("name") or "Unknown",
                    "pid": process.info["pid"],
                    "ram_mb": _memory_mb(memory),
                }
            )
        except (psutil.Error, AttributeError, KeyError):
            continue
    return sorted(processes, key=lambda item: item["ram_mb"], reverse=True)[: max(0, limit)]


def read_telemetry(limit: int = 5) -> dict[str, Any]:
    memory = psutil.virtual_memory()
    gpu = _gpu_info()
    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "ram_used_mb": _memory_mb(memory.used),
        "ram_total_mb": _memory_mb(memory.total),
        "gpu_name": gpu["name"],
        "vram_used_mb": gpu["vram_used_mb"],
        "vram_total_mb": gpu["vram_total_mb"],
        "gpu_temperature_c": gpu["temperature_c"],
        "top_processes": top_processes(limit),
    }
