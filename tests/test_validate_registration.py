from __future__ import annotations

import json

import pytest

from validate_registration import _validate_release_manifests


def _write_manifest(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def test_validate_release_manifests_accepts_matching_payload(tmp_path):
    release_dir = tmp_path / "registry" / "packages" / "pkg-a" / "releases" / "1.0.0"
    source_dir = tmp_path / "source"
    source_manifests_dir = source_dir / ".gaia" / "manifests"
    payload = {"manifest_schema_version": 1, "package": "pkg-a", "version": "1.0.0"}

    for filename in ("exports.json", "premises.json", "holes.json", "bridges.json"):
        _write_manifest(release_dir / filename, payload)
        _write_manifest(source_manifests_dir / filename, payload)

    _validate_release_manifests(release_dir=release_dir, source_dir=source_dir)


def test_validate_release_manifests_rejects_incomplete_release_dir(tmp_path):
    release_dir = tmp_path / "registry" / "packages" / "pkg-a" / "releases" / "1.0.0"
    source_dir = tmp_path / "source"
    source_manifests_dir = source_dir / ".gaia" / "manifests"
    payload = {"manifest_schema_version": 1, "package": "pkg-a", "version": "1.0.0"}

    for filename in ("exports.json", "premises.json", "bridges.json"):
        _write_manifest(release_dir / filename, payload)
        _write_manifest(source_manifests_dir / filename, payload)
    _write_manifest(source_manifests_dir / "holes.json", payload)

    with pytest.raises(SystemExit, match="Release manifest directory is incomplete"):
        _validate_release_manifests(release_dir=release_dir, source_dir=source_dir)
