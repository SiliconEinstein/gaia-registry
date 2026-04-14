from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

from registry_helpers import ResolvedRelease
from registry_helpers import ensure_clean_dir, parse_gaia_dependencies, resolve_release, run


MANIFEST_FILENAMES = ("exports.json", "premises.json", "holes.json", "bridges.json")


def _hydrate_release_manifests(source_dir: Path, release: ResolvedRelease) -> None:
    if not release.release_dir.exists():
        return
    manifests_dir = source_dir / ".gaia" / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    for filename in MANIFEST_FILENAMES:
        source = release.release_dir / filename
        if source.exists():
            shutil.copy2(source, manifests_dir / filename)


def _strip_uv_sources(source_dir: Path) -> None:
    """Remove [tool.uv.sources] from pyproject.toml.

    Package authors use this section for local development overrides (e.g.
    ``gaia-lang = { path = "../Gaia" }``).  In CI the framework is installed
    from PyPI/Git and Gaia deps are managed by this script, so the section
    must be stripped to avoid ``uv pip install`` resolving non-existent paths.
    """
    pyproject = source_dir / "pyproject.toml"
    if not pyproject.exists():
        return
    text = pyproject.read_text()
    # Remove the entire [tool.uv.sources] table: header + all key = value
    # lines until the next section header or end of file.
    stripped = re.sub(
        r"\n?\[tool\.uv\.sources\]\n(?:[^\[]*(?:\n|$))*",
        "\n",
        text,
    )
    if stripped != text:
        pyproject.write_text(stripped)


def _clone_release(source_dir: Path, release: ResolvedRelease) -> None:
    ensure_clean_dir(source_dir)
    run(["git", "clone", release.repo_url, str(source_dir)], cwd=source_dir.parent)
    run(["git", "checkout", release.git_ref], cwd=source_dir)
    _strip_uv_sources(source_dir)


def install_dependencies(*, registry_root: Path, source_dir: Path, deps_dir: Path) -> None:
    installed: set[str] = set()

    def install_tree(pyproject_path: Path) -> None:
        for distribution_name, specifier in parse_gaia_dependencies(pyproject_path).items():
            if distribution_name in installed:
                continue
            release = resolve_release(
                registry_root=registry_root,
                distribution_name=distribution_name,
                specifier=specifier,
            )
            dep_source = deps_dir / release.package_name
            _clone_release(dep_source, release)
            install_tree(dep_source / "pyproject.toml")
            _hydrate_release_manifests(dep_source, release)
            run(["uv", "pip", "install", "-e", str(dep_source)], cwd=registry_root)
            installed.add(distribution_name)

    install_tree(source_dir / "pyproject.toml")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-root", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--deps-dir", type=Path, required=True)
    args = parser.parse_args()

    install_dependencies(
        registry_root=args.registry_root.resolve(),
        source_dir=args.source_dir.resolve(),
        deps_dir=args.deps_dir.resolve(),
    )


if __name__ == "__main__":
    main()
