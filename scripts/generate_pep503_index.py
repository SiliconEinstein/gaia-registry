#!/usr/bin/env python3
"""Generate PEP 503 Simple Repository static index from registry metadata."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

REGISTRY_REPO = "SiliconEinstein/gaia-registry"
RELEASES_URL = f"https://github.com/{REGISTRY_REPO}/releases/download"


def normalize(name: str) -> str:
    """PEP 503 normalization: lowercase, replace [-_.] runs with single dash."""
    return re.sub(r"[-_.]+", "-", name).lower()


def generate(packages_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    package_links = []
    for pkg_dir in sorted(packages_dir.iterdir()):
        if not pkg_dir.is_dir():
            continue

        pkg_toml = tomllib.loads((pkg_dir / "Package.toml").read_text())
        versions_path = pkg_dir / "Versions.toml"
        if not versions_path.exists():
            continue
        versions_toml = tomllib.loads(versions_path.read_text())

        pypi_name = pkg_toml["pypi_name"]
        normalized_name = normalize(pypi_name)

        package_links.append(f'<a href="/{normalized_name}/">{normalized_name}</a>')

        # Per-package index
        pkg_index_dir = output_dir / normalized_name
        pkg_index_dir.mkdir(exist_ok=True)
        version_links = []
        for version, info in versions_toml.get("versions", {}).items():
            wheel = info["wheel"]
            wheel_hash = info.get("wheel_hash", "")
            tag = f"release/{pypi_name}-{version}"
            hash_frag = f"#sha256={wheel_hash}" if wheel_hash else ""
            url = f"{RELEASES_URL}/{tag}/{wheel}{hash_frag}"
            version_links.append(f'<a href="{url}">{wheel}</a>')

        (pkg_index_dir / "index.html").write_text(
            "<!DOCTYPE html>\n<html><body>\n"
            + "\n".join(version_links)
            + "\n</body></html>\n"
        )

    # Root index
    (output_dir / "index.html").write_text(
        "<!DOCTYPE html>\n<html><body>\n"
        + "\n".join(package_links)
        + "\n</body></html>\n"
    )

    print(f"Generated PEP 503 index for {len(package_links)} packages in {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PEP 503 index")
    parser.add_argument("--output-dir", default="simple", help="Output directory")
    parser.add_argument("--packages-dir", default="packages", help="Packages metadata directory")
    args = parser.parse_args()
    generate(Path(args.packages_dir), Path(args.output_dir))


if __name__ == "__main__":
    main()
