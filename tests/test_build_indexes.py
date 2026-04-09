from __future__ import annotations

import json

from build_indexes import build_indexes


def _write_json(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def test_build_indexes_emits_views_for_premises_holes_and_bridges(tmp_path):
    registry_root = tmp_path / "registry"
    release_a = registry_root / "packages" / "package-a" / "releases" / "1.4.0"
    release_b = registry_root / "packages" / "package-b" / "releases" / "2.1.0"

    _write_json(
        release_a / "premises.json",
        {
            "manifest_schema_version": 1,
            "package": "package-a",
            "version": "1.4.0",
            "ir_hash": "sha256:a",
            "premises": [
                {
                    "qid": "github:package_a::key_missing_lemma",
                    "role": "local_hole",
                    "content_hash": "abc",
                    "interface_hash": "sha256:iface-a",
                    "exported": False,
                    "required_by": ["github:package_a::main_theorem"],
                }
            ],
        },
    )
    _write_json(
        release_a / "holes.json",
        {
            "manifest_schema_version": 1,
            "package": "package-a",
            "version": "1.4.0",
            "ir_hash": "sha256:a",
            "holes": [
                {
                    "qid": "github:package_a::key_missing_lemma",
                    "interface_hash": "sha256:iface-a",
                    "required_by": ["github:package_a::main_theorem"],
                }
            ],
        },
    )
    _write_json(
        release_b / "bridges.json",
        {
            "manifest_schema_version": 1,
            "package": "package-b",
            "version": "2.1.0",
            "ir_hash": "sha256:b",
            "bridges": [
                {
                    "relation_id": "bridge_1234",
                    "relation_type": "fills",
                    "source_qid": "github:package_b::b_result",
                    "source_content_hash": "def",
                    "target_qid": "github:package_a::key_missing_lemma",
                    "target_package": "package-a",
                    "target_dependency_req": ">=1.4.0,<2.0.0",
                    "target_resolved_version": "1.4.0",
                    "target_role": "local_hole",
                    "target_interface_hash": "sha256:iface-a",
                    "strength": "exact",
                    "mode": "deduction",
                    "declared_by_owner_of_source": True,
                }
            ],
        },
    )

    build_indexes(registry_root=registry_root)

    premise_index = next(
        (registry_root / "index" / "premises" / "by-qid").rglob("*.json")
    )
    hole_index = next((registry_root / "index" / "holes" / "by-qid").rglob("*.json"))
    bridge_index = next(
        (registry_root / "index" / "bridges" / "by-target-interface").rglob("*.json")
    )

    premise_payload = json.loads(premise_index.read_text())
    hole_payload = json.loads(hole_index.read_text())
    bridge_payload = json.loads(bridge_index.read_text())
    stats_payload = json.loads((registry_root / "index" / "manifests" / "stats.json").read_text())

    assert premise_payload["qid"] == "github:package_a::key_missing_lemma"
    assert premise_payload["history"][0]["role"] == "local_hole"
    assert hole_payload["hole_versions"][0]["interface_hash"] == "sha256:iface-a"
    assert bridge_payload["target_interface_hash"] == "sha256:iface-a"
    assert bridge_payload["bridges"][0]["declaring_package"] == "package-b"
    assert stats_payload["stats"]["premises"] == 1
    assert stats_payload["stats"]["holes"] == 1
    assert stats_payload["stats"]["bridges"] == 1
