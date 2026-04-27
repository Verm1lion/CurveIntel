# CurveIntel v2.0.0 Baseline Release Notes

## Summary

CurveIntel v2.0.0 is the first public baseline for the database-backed FastAPI
application. The release combines the open-source cleanup with the production
runtime baseline: persistent analysis records, authenticated browser sessions,
RBAC, audit logging, admin backoffice controls, Docker/PostgreSQL startup, and
the existing deterministic tensile-analysis pipeline.

## Highlights

- MIT-licensed open-source project surface with contributor, security, issue,
  and PR documentation.
- SQLAlchemy/Alembic persistence for users, analysis results, and audit events.
- JWT cookie authentication with first-admin bootstrap and seeded-admin startup
  modes.
- Role-aware access for `admin`, `analyst`, and `viewer` users.
- Admin backoffice controls for user management and audit review.
- Docker Compose PostgreSQL runtime with automatic `alembic upgrade head` before
  the FastAPI app starts.
- Manual smoke scripts no longer depend on local absolute dataset paths; optional
  external datasets are resolved through `CURVEINTEL_DATASET_ROOT`.
- `docs/current_status_and_usage.md` documents the current operator workflow,
  runtime modes, role matrix, API surface, and remaining ops work.

## Validation

Local validation completed for the baseline:

- `ruff check .`
- `ruff format --check .`
- `pytest -q`
- `pytest --cov=src --cov=web --cov-report=term-missing -q`

Latest local result: 34 tests passed, 2 optional PostgreSQL tests skipped when
live database URLs were not configured, and total source coverage was 76%.

## Release Operations

Recommended release target:

- Tag: `v2.0.0`
- Branch: `main`
- Release type: stable baseline

Before publishing from a new machine or CI runner, confirm:

- the GitHub token previously embedded in the local remote URL has been revoked
  or rotated;
- `origin` uses a tokenless HTTPS or SSH URL;
- branch protection and required CI checks are enabled for `main`;
- the Docker/PostgreSQL smoke flow passes in the deployment environment.
