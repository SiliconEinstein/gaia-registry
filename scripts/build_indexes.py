from __future__ import annotations

import argparse
import hashlib
import shutil
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

from registry_helpers import iter_release_dirs, load_json, version_sort_key, write_json


def _shard(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:2]


def _encoded(value: str) -> str:
    return quote(value, safe="")


def _sorted_versions_map(payload: dict[str, dict]) -> dict[str, dict]:
    return {version: payload[version] for version in sorted(payload, key=version_sort_key)}


def build_indexes(*, registry_root: Path) -> None:
    index_root = registry_root / "index"
    if index_root.exists():
        shutil.rmtree(index_root)
    index_root.mkdir(parents=True, exist_ok=True)

    premises_by_package: dict[str, dict[str, list[dict]]] = defaultdict(dict)
    premises_by_qid: dict[str, list[dict]] = defaultdict(list)
    holes_by_package: dict[str, dict[str, list[dict]]] = defaultdict(dict)
    holes_by_qid: dict[str, list[dict]] = defaultdict(list)
    bridges_by_target_qid: dict[str, list[dict]] = defaultdict(list)
    bridges_by_target_interface: dict[str, dict[str, object]] = {}
    bridges_by_source_qid: dict[str, list[dict]] = defaultdict(list)
    bridges_by_declaring_package: dict[str, list[dict]] = defaultdict(list)

    stats = {
        "packages_with_releases": 0,
        "release_versions": 0,
        "premises": 0,
        "holes": 0,
        "bridges": 0,
    }
    seen_packages_with_releases: set[str] = set()

    for package_name, version, release_dir in iter_release_dirs(registry_root):
        seen_packages_with_releases.add(package_name)
        stats["release_versions"] += 1

        premises_path = release_dir / "premises.json"
        if premises_path.exists():
            premises_manifest = load_json(premises_path)
            premises = premises_manifest.get("premises", [])
            if isinstance(premises, list):
                premises_by_package[package_name][version] = premises
                stats["premises"] += len(premises)
                for premise in premises:
                    if not isinstance(premise, dict):
                        continue
                    qid = premise.get("qid")
                    if not isinstance(qid, str) or not qid:
                        continue
                    premises_by_qid[qid].append(
                        {
                            "package": package_name,
                            "version": version,
                            "role": premise.get("role"),
                            "interface_hash": premise.get("interface_hash"),
                            "content_hash": premise.get("content_hash"),
                            "exported": premise.get("exported"),
                            "required_by": premise.get("required_by", []),
                        }
                    )

        holes_path = release_dir / "holes.json"
        if holes_path.exists():
            holes_manifest = load_json(holes_path)
            holes = holes_manifest.get("holes", [])
            if isinstance(holes, list):
                holes_by_package[package_name][version] = holes
                stats["holes"] += len(holes)
                for hole in holes:
                    if not isinstance(hole, dict):
                        continue
                    qid = hole.get("qid")
                    if not isinstance(qid, str) or not qid:
                        continue
                    holes_by_qid[qid].append(
                        {
                            "package": package_name,
                            "version": version,
                            "interface_hash": hole.get("interface_hash"),
                            "required_by": hole.get("required_by", []),
                        }
                    )

        bridges_path = release_dir / "bridges.json"
        if bridges_path.exists():
            bridges_manifest = load_json(bridges_path)
            bridges = bridges_manifest.get("bridges", [])
            if isinstance(bridges, list):
                stats["bridges"] += len(bridges)
                for bridge in bridges:
                    if not isinstance(bridge, dict):
                        continue
                    relation = dict(bridge)
                    relation["declaring_package"] = package_name
                    relation["declaring_version"] = version
                    target_qid = relation.get("target_qid")
                    if isinstance(target_qid, str) and target_qid:
                        bridges_by_target_qid[target_qid].append(relation)
                    source_qid = relation.get("source_qid")
                    if isinstance(source_qid, str) and source_qid:
                        bridges_by_source_qid[source_qid].append(relation)
                    bridges_by_declaring_package[package_name].append(relation)
                    target_interface_hash = relation.get("target_interface_hash")
                    if isinstance(target_interface_hash, str) and target_interface_hash:
                        entry = bridges_by_target_interface.setdefault(
                            target_interface_hash,
                            {
                                "target_interface_hash": target_interface_hash,
                                "target_qid": relation.get("target_qid"),
                                "bridges": [],
                            },
                        )
                        entry["bridges"].append(relation)

    stats["packages_with_releases"] = len(seen_packages_with_releases)

    for package_name, versions in premises_by_package.items():
        write_json(
            index_root / "premises" / "by-package" / f"{package_name}.json",
            {
                "package": package_name,
                "versions": {
                    version: {"premises": versions[version]}
                    for version in sorted(versions, key=version_sort_key)
                },
            },
        )

    for qid, history in premises_by_qid.items():
        ordered = sorted(history, key=lambda item: (item["package"], version_sort_key(item["version"])))
        write_json(
            index_root / "premises" / "by-qid" / _shard(qid) / f"{_encoded(qid)}.json",
            {"qid": qid, "history": ordered},
        )

    for package_name, versions in holes_by_package.items():
        write_json(
            index_root / "holes" / "by-package" / f"{package_name}.json",
            {
                "package": package_name,
                "versions": {
                    version: {"holes": versions[version]}
                    for version in sorted(versions, key=version_sort_key)
                },
            },
        )

    for qid, entries in holes_by_qid.items():
        ordered = sorted(entries, key=lambda item: (item["package"], version_sort_key(item["version"])))
        write_json(
            index_root / "holes" / "by-qid" / _shard(qid) / f"{_encoded(qid)}.json",
            {"qid": qid, "hole_versions": ordered},
        )

    for qid, bridges in bridges_by_target_qid.items():
        ordered = sorted(
            bridges,
            key=lambda item: (item["declaring_package"], version_sort_key(item["declaring_version"]), item["relation_id"]),
        )
        write_json(
            index_root / "bridges" / "by-target-qid" / _shard(qid) / f"{_encoded(qid)}.json",
            {"target_qid": qid, "bridges": ordered},
        )

    for interface_hash, entry in bridges_by_target_interface.items():
        ordered = sorted(
            entry["bridges"],
            key=lambda item: (item["declaring_package"], version_sort_key(item["declaring_version"]), item["relation_id"]),
        )
        write_json(
            index_root
            / "bridges"
            / "by-target-interface"
            / _shard(interface_hash)
            / f"{_encoded(interface_hash)}.json",
            {
                "target_interface_hash": interface_hash,
                "target_qid": entry["target_qid"],
                "bridges": ordered,
            },
        )

    for qid, bridges in bridges_by_source_qid.items():
        ordered = sorted(
            bridges,
            key=lambda item: (item["declaring_package"], version_sort_key(item["declaring_version"]), item["relation_id"]),
        )
        write_json(
            index_root / "bridges" / "by-source-qid" / _shard(qid) / f"{_encoded(qid)}.json",
            {"source_qid": qid, "bridges": ordered},
        )

    for package_name, bridges in bridges_by_declaring_package.items():
        ordered = sorted(
            bridges,
            key=lambda item: (version_sort_key(item["declaring_version"]), item["relation_id"]),
        )
        write_json(
            index_root / "bridges" / "by-declaring-package" / f"{package_name}.json",
            {"package": package_name, "bridges": ordered},
        )

    write_json(index_root / "manifests" / "stats.json", {"stats": stats})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-root", type=Path, required=True)
    args = parser.parse_args()
    build_indexes(registry_root=args.registry_root.resolve())


if __name__ == "__main__":
    main()
