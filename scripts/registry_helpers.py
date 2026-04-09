from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement
from packaging.version import InvalidVersion, Version


@dataclass(frozen=True)
class ResolvedRelease:
    distribution_name: str
    package_name: str
    repo_url: str
    version: str
    git_ref: str
    release_dir: Path
    package_dir: Path


def load_toml(path: Path) -> dict[str, Any]:
    try:
        import tomllib
    except ImportError:  # pragma: no cover
        import tomli as tomllib  # type: ignore[no-redef]
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def package_name_from_distribution(distribution_name: str) -> str:
    if not distribution_name.endswith("-gaia"):
        raise ValueError(f"expected Gaia distribution name, got {distribution_name!r}")
    return distribution_name.removesuffix("-gaia")


def parse_gaia_dependencies(pyproject_path: Path) -> dict[str, str]:
    project = load_toml(pyproject_path).get("project", {})
    dependencies = project.get("dependencies", [])
    if not isinstance(dependencies, list):
        raise ValueError(f"[project].dependencies must be a list in {pyproject_path}")
    parsed: dict[str, str] = {}
    for raw in dependencies:
        if not isinstance(raw, str):
            raise ValueError(f"dependency entries must be strings in {pyproject_path}")
        requirement = Requirement(raw)
        if requirement.name.endswith("-gaia"):
            parsed[requirement.name] = str(requirement.specifier) or "*"
    return parsed


def version_sort_key(version: str) -> tuple[int, Version | str]:
    try:
        return (0, Version(version))
    except InvalidVersion:
        return (1, version)


def resolve_release(
    *,
    registry_root: Path,
    distribution_name: str,
    specifier: str,
) -> ResolvedRelease:
    package_name = package_name_from_distribution(distribution_name)
    package_dir = registry_root / "packages" / package_name
    package_payload = load_toml(package_dir / "Package.toml")
    versions_payload = load_toml(package_dir / "Versions.toml").get("versions", {})
    if not isinstance(versions_payload, dict) or not versions_payload:
        raise SystemExit(f"No registered versions found for dependency {distribution_name}.")

    requirement = Requirement(f"{distribution_name}{specifier if specifier != '*' else ''}")
    matching_versions = []
    for version in versions_payload:
        if not isinstance(version, str):
            continue
        try:
            parsed_version = Version(version)
        except InvalidVersion:
            continue
        if parsed_version in requirement.specifier:
            matching_versions.append((parsed_version, version))

    if not matching_versions:
        raise SystemExit(
            f"No registered version of {distribution_name} matches dependency specifier {specifier!r}."
        )

    _, resolved_version = max(matching_versions, key=lambda item: item[0])
    version_payload = versions_payload[resolved_version]
    git_ref = version_payload.get("git_sha") or version_payload.get("git_tag")
    if not isinstance(git_ref, str) or not git_ref:
        raise SystemExit(
            f"Registered version {distribution_name} {resolved_version} is missing git_sha/git_tag."
        )

    return ResolvedRelease(
        distribution_name=distribution_name,
        package_name=package_name,
        repo_url=package_payload["repo"],
        version=resolved_version,
        git_ref=git_ref,
        release_dir=package_dir / "releases" / resolved_version,
        package_dir=package_dir,
    )


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def run(args: list[str], *, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def iter_release_dirs(registry_root: Path):
    packages_root = registry_root / "packages"
    if not packages_root.exists():
        return
    for package_dir in sorted(
        (candidate for candidate in packages_root.iterdir() if candidate.is_dir()),
        key=lambda item: item.name,
    ):
        releases_dir = package_dir / "releases"
        if not releases_dir.exists():
            continue
        for release_dir in sorted(
            (candidate for candidate in releases_dir.iterdir() if candidate.is_dir()),
            key=lambda item: version_sort_key(item.name),
        ):
            yield package_dir.name, release_dir.name, release_dir
