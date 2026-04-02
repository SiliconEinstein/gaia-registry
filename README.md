# Gaia Official Registry

Knowledge package index for the Gaia ecosystem. Follows the [Julia General Registry](https://github.com/JuliaRegistries/General) model.

## For consumers

Add this registry to your `pyproject.toml`:

```toml
[[tool.uv.index]]
name = "gaia"
url = "https://siliconeinstein.github.io/gaia-registry/simple/"
```

Then install packages:

```bash
uv add galileo-falling-bodies-gaia
```

## For package authors

1. Create a Gaia knowledge package (see [Gaia Lang v5](https://github.com/SiliconEinstein/Gaia))
2. Tag a release: `git tag v1.0.0 && git push origin v1.0.0`
3. Create a PR to this repo adding your package metadata to `packages/`

## Structure

```
packages/<name>/
  Package.toml       # UUID, name, repo URL
  Versions.toml      # Version → ir_hash → git_sha → wheel
  Deps.toml          # Dependencies per version
```

## Phase 1

- Registration + CI validation + distribution
- Review system deferred to Phase 2
