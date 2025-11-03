#!/usr/bin/env python3
"""
Config Validator
Validates YAML/JSON configs: required keys, version, security, schema.
"""

import sys
import json
import yaml
import click
from pathlib import Path
from typing import Dict, List, Any, Tuple
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

# ──────────────────────────────────────────────────────────────
# CONFIG SCHEMA (customize per project)
# ──────────────────────────────────────────────────────────────
SCHEMA = {
    "required_keys": ["name", "version", "api_endpoint"],
    "version_min": "1.0.0",
    "forbidden_keys": ["password", "secret", "token", "api_key"],
    "allowed_formats": [".yaml", ".yml", ".json"],
}

# ──────────────────────────────────────────────────────────────
# VERSION CHECK (uses version_checker.py)
# ──────────────────────────────────────────────────────────────
def is_version_valid(current: str) -> bool:
    """Check if current version meets minimum requirement"""
    try:
        from version_checker import VersionChecker
        checker = VersionChecker()
        return checker.compare_versions(current, SCHEMA["version_min"]) >= 0
    except Exception:
        return False

# ──────────────────────────────────────────────────────────────
# VALIDATE SINGLE FILE
# ──────────────────────────────────────────────────────────────
def validate_file(path: Path) -> Tuple[bool, List[str]]:
    errors = []

    # Format
    if path.suffix not in SCHEMA["allowed_formats"]:
        errors.append(f"Unsupported format: {path.suffix}")
        return False, errors

    # Parse
    try:
        text = path.read_text()
        data = yaml.safe_load(text) if path.suffix in {".yaml", ".yml"} else json.loads(text)
    except Exception as e:
        errors.append(f"Parse error: {e}")
        return False, errors

    if not isinstance(data, dict):
        errors.append("Root must be object/dict")
        return False, errors

    # Required keys
    missing = [k for k in SCHEMA["required_keys"] if k not in data]
    if missing:
        errors.append(f"Missing: {', '.join(missing)}")

    # Version
    if "version" in data and not is_version_valid(data["version"]):
        errors.append(f"Version {data['version']} < {SCHEMA['version_min']}")

    # Forbidden keys
    forbidden = [k for k in SCHEMA["forbidden_keys"] if k in data]
    if forbidden:
        errors.append(f"Forbidden keys: {', '.join(forbidden)}")

    return len(errors) == 0, errors

# ──────────────────────────────────────────────────────────────
# SCAN DIR
# ──────────────────────────────────────────────────────────────
def scan_directory(root: Path) -> Dict:
    results = {"valid": 0, "invalid": 0, "files": []}
    for path in root.rglob("*"):
        if path.suffix in SCHEMA["allowed_formats"]:
            ok, errs = validate_file(path)
            status = "PASS" if ok else "FAIL"
            results["files"].append({"path": str(path), "status": status})
            results["valid" if ok else "invalid"] += 1
    results["total"] = len(results["files"])
    return results

# ──────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────
@click.command()
@click.argument("path", type=click.Path(exists=True), default=".")
def main(path: str):
    root = Path(path)
    console.print(f"[bold blue]Validating configs in:[/] {root.resolve()}")

    report = scan_directory(root)

    table = Table(title="Config Validation", box=box.ROUNDED)
    table.add_column("File", style="cyan")
    table.add_column("Status")
    for f in report["files"]:
        color = "green" if f["status"] == "PASS" else "red"
        table.add_row(f["path"], f"[{color}]{f['status']}[/]")
    console.print(table)

    summary = f"[bold]Total:[/] {report['total']} | [green]PASS: {report['valid']}[/] | [red]FAIL: {report['invalid']}[/]"
    console.print(summary)

    if report["invalid"]:
        sys.exit(1)
    else:
        console.print("\n[bold green]All configs valid![/]")

if __name__ == "__main__":
    main()