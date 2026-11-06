# Contributing to Voxwire

Thanks for helping. Bug reports, fixes, docs and new features are all welcome.

## Before you start

- For anything bigger than a small fix, open an issue first so we can agree on the approach.
- Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
- Report security problems privately, as described in [SECURITY.md](SECURITY.md), not in a public issue.

## Setup

```bash
git clone https://github.com/AnjalLLL/voxwire && cd voxwire
cp .env.example .env
docker compose up --build
```

To work outside Docker:

```bash
cd python && uv sync --extra server && uv run pytest && uv run ruff check
cd js && npm test
cd sfu && go vet ./... && go test ./...     # needs libopus (brew install opus / apt install libopus-dev)
uvx --with mkdocs-material mkdocs serve      # preview the docs
```

## Pull requests

1. Branch off `main`.
2. Keep each PR to one change. Add or update tests for any logic you change.
3. Run the checks above, and add a line under `[Unreleased]` in [CHANGELOG.md](CHANGELOG.md).
4. Open the PR and fill in the template. CI must pass before we merge.

Commit messages should be short and written in the imperative mood ("Fix resampler drift", not "Fixed…").

## Releasing (maintainers)

1. Bump `__version__` in `python/src/voxwire/__init__.py` **and** `version` in `js/package.json` (they must match the tag), and move the `[Unreleased]` notes in the changelog under the new version.
2. Commit, then tag and push: `git tag v0.2.0 && git push origin v0.2.0`.
3. The `release` workflow publishes to PyPI and npm, pushes both Docker images to GHCR, and creates a GitHub release.

By contributing, you agree that your contributions are licensed under the [Apache-2.0 License](LICENSE).
