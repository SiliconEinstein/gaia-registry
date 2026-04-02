#!/usr/bin/env python3
"""Detect package versions that were added/changed but not yet published."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib


def main() -> None:
    packages_dir = Path("packages")
    if not packages_dir.exists():
        print("packages=[]", file=sys.stderr)
        _set_output("packages", "[]")
        return

    # Get list of existing releases to skip already-published versions
    result = subprocess.run(
        ["gh", "release", "list", "--json", "tagName", "-q", ".[].tagName"],
        capture_output=True, text=True,
    )
    existing_releases = set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()

    changed = []
    for pkg_dir in sorted(packages_dir.iterdir()):
        if not pkg_dir.is_dir():
            continue

        pkg_path = pkg_dir / "Package.toml"
        versions_path = pkg_dir / "Versions.toml"
        if not pkg_path.exists() or not versions_path.exists():
            continue

        pkg_toml = tomllib.loads(pkg_path.read_text())
        versions_toml = tomllib.loads(versions_path.read_text())

        for version, info in versions_toml.get("versions", {}).items():
            release_tag = f"release/{pkg_toml['pypi_name']}-{version}"
            if release_tag in existing_releases:
                continue  # Already published, skip

            changed.append({
                "name": pkg_toml["name"],
                "pypi_name": pkg_toml["pypi_name"],
                "version": version,
                "repo": pkg_toml["repo"],
                "git_tag": info.get("git_tag", f"v{version}"),
                "git_sha": info.get("git_sha", ""),
                "ir_hash": info.get("ir_hash", ""),
                "wheel": info.get("wheel", ""),
            })

    _set_output("packages", json.dumps(changed))
    print(f"Found {len(changed)} unpublished versions", file=sys.stderr)


def _set_output(name: str, value: str) -> None:
    """Write to GITHUB_OUTPUT if available, otherwise print."""
    output_file = Path(os.environ.get("GITHUB_OUTPUT", ""))
    if output_file.exists():
        with open(output_file, "a") as f:
            f.write(f"{name}={value}\n")
    else:
        print(f"{name}={value}")


import os

if __name__ == "__main__":
    main()
