#!/usr/bin/env python3
"""
Version Checker - System & Tool Version Validator
"""

import sys
import subprocess
import platform
import argparse
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass

# Optional: rich + psutil
try:
    from rich.console import Console
    from rich.table import Table
    from rich import box
    console = Console()
except ImportError:
    console = None

try:
    import psutil
except ImportError:
    psutil = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VersionRequirement:
    name: str
    command: str
    min_version: str
    check_args: List[str]
    required: bool = True

class VersionChecker:
    def __init__(self):
        self.requirements = self._define_requirements()
        self.results = {}

    def _define_requirements(self) -> List[VersionRequirement]:
        return [
            VersionRequirement("Python", "python3", "3.8.0", ["--version"], True),
            VersionRequirement("Git", "git", "2.20.0", ["--version"], True),
            VersionRequirement("Docker", "docker", "20.10.0", ["--version"], False),
            VersionRequirement("Node.js", "node", "14.0.0", ["--version"], False),
            VersionRequirement("npm", "npm", "6.0.0", ["--version"], False),
            VersionRequirement("curl", "curl", "7.0.0", ["--version"], True),
            VersionRequirement("Bash", "bash", "4.0", ["--version"], True),
        ]

    def command_exists(self, cmd: str) -> bool:
        try:
            subprocess.run(
                ["where" if platform.system() == "Windows" else "which", cmd],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return True
        except:
            return False

    def get_version(self, cmd: str, args: List[str]) -> Optional[str]:
        try:
            result = subprocess.run([cmd] + args, capture_output=True, text=True, timeout=5)
            output = result.stdout + result.stderr
            import re
            match = re.search(r'(\d+\.\d+(\.\d+)?)', output)
            if match:
                v = match.group(1).split('.')
                while len(v) < 3: v.append('0')
                return '.'.join(v[:3])
        except:
            pass
        return None

    def compare_versions(self, v1: str, v2: str) -> int:
        def norm(v):
            return [int(x) for x in v.split('.')]
        p1, p2 = norm(v1), norm(v2)
        p1, p2 = p1 + [0]*(3-len(p1)), p2 + [0]*(3-len(p2))
        return (p1 > p2) - (p1 < p2)

    def check_requirement(self, req: VersionRequirement) -> Dict:
        result = {"name": req.name, "required": req.required, "installed": False}
        if not self.command_exists(req.command):
            result["message"] = f"{req.name} not found"
            return result

        result["installed"] = True
        version = self.get_version(req.command, req.check_args)
        result["version"] = version or "unknown"

        if version and self.compare_versions(version, req.min_version) >= 0:
            result["ok"] = True
            result["message"] = f"{req.name} {version} [OK]"
        else:
            result["ok"] = False
            result["message"] = f"{req.name} {version} < {req.min_version}"
            if req.required:
                result["message"] += " [REQUIRED]"
        return result

    def check_all(self):
        for req in self.requirements:
            self.results[req.name] = self.check_requirement(req)

    def check_resources(self) -> Dict:
        if not psutil:
            return {}
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return {
            "cpu_cores": psutil.cpu_count(),
            "memory_gb": round(mem.total / (1024**3), 2),
            "memory_free_gb": round(mem.available / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
        }

    def print_report(self):
        if console:
            table = Table(title="System Check", box=box.ROUNDED)
            table.add_column("Tool", style="cyan")
            table.add_column("Status", style="green")
            for r in self.results.values():
                color = "green" if r.get("ok") else "red"
                table.add_row(r["name"], f"[{color}]{r['message']}[/]")
            console.print(table)

            res = self.check_resources()
            if res:
                res_table = Table(title="Resources")
                res_table.add_column("Metric")
                res_table.add_column("Value")
                for k, v in res.items():
                    res_table.add_row(k.replace("_", " ").title(), str(v))
                console.print(res_table)
        else:
            for r in self.results.values():
                print(r["message"])

        return all(r.get("ok", False) for r in self.results.values() if r.get("required"))

def main():
    parser = argparse.ArgumentParser(description="Version Checker")
    parser.add_argument("--check-all", action="store_true", help="Check all tools")
    parser.add_argument("--check-python", action="store_true", help="Check Python only")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    checker = VersionChecker()
    if args.check_python:
        req = VersionRequirement("Python", "python3", "3.8.0", ["--version"])
        result = checker.check_requirement(req)
        print(result["message"])
        sys.exit(0 if result.get("ok") else 1)
    else:
        checker.check_all()
        success = checker.print_report()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()