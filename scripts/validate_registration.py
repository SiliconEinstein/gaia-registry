from __future__ import annotations

import argparse
from pathlib import Path

from registry_helpers import load_json


MANIFEST_FILENAMES = ("exports.json", "premises.json", "holes.json", "bridges.json")


def _validate_release_manifests(*, release_dir: Path, source_dir: Path) -> None:
    missing = [filename for filename in MANIFEST_FILENAMES if not (release_dir / filename).exists()]
    if missing:
        missing_text = ", ".join(missing)
        raise SystemExit(f"Release manifest directory is incomplete: missing {missing_text}.")

    source_manifests_dir = source_dir / ".gaia" / "manifests"
    for filename in MANIFEST_FILENAMES:
        compiled_path = source_manifests_dir / filename
        if not compiled_path.exists():
            raise SystemExit(f"Compiled source is missing {compiled_path}.")
        expected = load_json(release_dir / filename)
        actual = load_json(compiled_path)
        if expected != actual:
            raise SystemExit(
                f"Release manifest mismatch for {filename}: registry payload does not match compiled source."
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    args = parser.parse_args()

    release_dir = args.package_dir.resolve() / "releases" / args.version
    if not release_dir.exists():
        print(f"Legacy registration payload detected; no release manifests under {release_dir}.")
        return

    _validate_release_manifests(release_dir=release_dir, source_dir=args.source_dir.resolve())
    print(f"Release manifests OK: {release_dir}")


if __name__ == "__main__":
    main()
