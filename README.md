# Gaia Official Registry

Knowledge package index for the Gaia ecosystem. Follows the [Julia General Registry](https://github.com/JuliaRegistries/General) model.

## For consumers

Phase 1 is a **source registry**, not an installable wheel index.
Use this repository to discover:
- the canonical GitHub repo for a Gaia package
- the validated git tag and pinned git SHA for a version
- the package's `ir_hash`
- Gaia package dependencies
- release-scoped `exports.json` / `premises.json` / `holes.json` / `bridges.json` manifests
- derived static indexes under `index/`

Consumers currently depend on registered packages via direct Git references, for example:

```bash
uv add "galileo-falling-bodies-gaia @ git+https://github.com/kunyuan/GalileoFallingBodies.gaia@<validated-git-sha>"
```

## For package authors

1. Create a Gaia knowledge package (see [Gaia Lang v5](https://github.com/SiliconEinstein/Gaia))
2. Run `gaia compile` and `gaia check`
3. Push source to GitHub and push a release tag: `git tag v1.0.0 && git push origin v1.0.0`
4. Create a PR to this repo adding package metadata under `packages/`

## Structure

```
packages/<name>/
  Package.toml       # UUID, name, repo URL
  Versions.toml      # Version → ir_hash → git_tag → git_sha
  Deps.toml          # Dependencies per version
  releases/<version>/
    exports.json     # Author-declared exports for the release
    premises.json    # Compiler-derived public premise interface snapshots
    holes.json       # Convenience subset of local holes
    bridges.json     # fills() declarations bound to target interface snapshots

index/
  premises/          # Derived premise indexes
  holes/             # Derived hole indexes
  bridges/           # Derived bridge indexes
  manifests/         # Stats / build outputs
```

## Registry behavior

- Registration PRs remain source-backed and GitHub-native
- CI recompiles the tagged source release and validates any submitted release manifests
- Static indexes under `index/` are generated after merge by GitHub Actions
- No wheel publishing and no PEP 503 package index yet
