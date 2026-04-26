# CurveIntel Remaining Work Handoff

Last updated: 27 April 2026

## Current Snapshot

CurveIntel v2.0.0 baseline is functionally complete. The app is DB-backed, has FastAPI auth/RBAC, audit trail, admin backoffice, Docker/PostgreSQL runtime, CI, and public-readiness documentation.

The latest local work fixed a real PostgreSQL smoke-test bug:

- Branch: `codex/postgres-numeric-snapshot`
- Commit: `6d36cbd` (`Fix Postgres numeric snapshot persistence`)
- Remote branch: `origin/codex/postgres-numeric-snapshot`
- Base branch: `main`
- Current remote `main`: `48ab33f` (`Pin bcrypt below incompatible major`)
- Current `v2.0.0` tag: still points to `48ab33f`

The branch contains:

- `src/curveintel/db/schemas.py`: indexed numeric snapshot fields are coerced to native Python `float` values before DB persistence.
- `src/curveintel/db/serializers.py`: analysis payloads are passed through `make_json_ready`.
- `tests/test_db.py`: regression coverage for NumPy scalar leakage.
- `docs/current_status_and_usage.md`: verification status updated.
- `planlar.md`: source-of-truth status updated.

## Verified State

These checks passed after the latest fix:

```powershell
ruff check .
ruff format --check .
pytest -q
pytest --cov=src --cov-report=term-missing -q
```

Results:

- `pytest -q`: `33 passed, 2 skipped`
- coverage: `33 passed, 2 skipped`, `75%`

Docker/PostgreSQL smoke also passed using `examples/sample_nist.csv`:

- `/api/health`: `200`
- `/`: `303` redirect to `/login`
- `/login`: `200`
- login as seeded admin: `200`
- `/api/auth/me`: `200`
- dashboard `/`: `200`
- `POST /api/analyze`: `200`
- `/api/results`: `200`
- PDF download: `200`, about `88 KB`
- `/api/audit-logs`: `200`

The app was left runnable locally through Docker at:

```text
http://localhost:8000
```

## Important Local Notes

- Local `.env` exists for Docker smoke and is gitignored.
- For unit tests, temporarily move `.env` aside because seeded-admin settings can alter auth/bootstrap tests:

```powershell
Move-Item -LiteralPath .env -Destination .env.local-smoke -Force
# run tests
Move-Item -LiteralPath .env.local-smoke -Destination .env -Force
```

- Do not commit `.env`.
- Do not print or persist any GitHub token. A PAT was previously pasted in chat; recommend the user revoke it after GitHub work is complete.
- `gh` CLI was not installed in this environment.
- Direct push to `main` is intentionally blocked by branch protection:

```text
GH006: Protected branch update failed
Changes must be made through a pull request.
5 of 5 required status checks are expected.
```

## What Is Left

### 1. Open and Merge the Fix PR

Open a PR from:

```text
codex/postgres-numeric-snapshot -> main
```

PR creation URL:

```text
https://github.com/Verm1lion/CurveIntel/pull/new/codex/postgres-numeric-snapshot
```

Suggested PR title:

```text
Fix Postgres numeric snapshot persistence
```

Suggested PR body:

```markdown
## Summary
- Coerce indexed analysis snapshot numeric fields to native Python floats before persistence.
- Normalize analysis payloads with `make_json_ready` so NumPy scalar values do not leak into PostgreSQL JSON/SQL parameters.
- Update baseline status docs after local Docker/PostgreSQL smoke validation.

## Root Cause
PostgreSQL inserts failed during real Docker smoke because NumPy scalar values such as `np.float64(206.3)` could reach SQLAlchemy indexed columns. psycopg2 rendered that representation in SQL, producing a schema lookup error for `np`.

## Validation
- `ruff check .`
- `ruff format --check .`
- `pytest -q` (`33 passed, 2 skipped`)
- `pytest --cov=src --cov-report=term-missing -q` (`33 passed, 2 skipped`, 75% coverage)
- Docker Compose + PostgreSQL smoke: health, login, analyze CSV, results, PDF download, audit logs
```

After PR checks pass, merge it into `main`.

### 2. Move the `v2.0.0` Tag to the Final Closing Commit

After the PR is merged, move `v2.0.0` from `48ab33f` to the merge result or final main commit.

Recommended sequence:

```powershell
git fetch origin --tags
git switch main
git pull --ff-only origin main
git tag -f v2.0.0 HEAD
git push origin v2.0.0 --force
```

Then update the GitHub release so it points to the final baseline commit. If GitHub does not automatically reflect the moved tag, edit the release target in the UI or recreate the release against the moved tag.

### 3. Confirm GitHub Release and CI

Confirm:

- `main` includes `6d36cbd` or the merged equivalent.
- `v2.0.0` points to the final commit, not `48ab33f`.
- GitHub Actions required checks pass:
  - `test (3.10)`
  - `test (3.11)`
  - `test (3.12)`
  - `postgres-smoke`
  - `docker`
- Release page is still available:

```text
https://github.com/Verm1lion/CurveIntel/releases/tag/v2.0.0
```

### 4. Optional GitHub Repo Hygiene

These are not product blockers, but they make the public repo look more complete:

- Ensure repo description is set.
- Ensure topics are set.
- Create or clean issue labels.
- Create 2-3 `good first issue` items.
- Discussions can remain off unless the user wants community interaction.

Suggested good-first-issue ideas:

1. Add a short troubleshooting note for Docker Desktop startup and `COMPOSE_BAKE=false`.
2. Add a small UI indicator for current database/runtime mode on the admin dashboard.
3. Add one more documented sample CSV variant under `examples/`.

### 5. Optional Demo Deployment

The user clarified they are not going live right now. So no public domain is required.

If demo deployment is still requested later, the realistic target remains Docker Compose + PostgreSQL on a VPS. Required environment items:

- strong `JWT_SECRET_KEY`
- seeded admin password or bootstrap-first-admin flow
- `DATABASE_URL` for Postgres
- CORS origins if accessed through a browser hostname
- persistent volumes for Postgres and generated reports/uploads as needed

Minimum smoke after deployment:

- `/api/health`
- `/login`
- admin bootstrap/login
- CSV analyze with `examples/sample_nist.csv`
- PDF download
- audit log view

## Do Not Reopen Unless Needed

The following are already done and should not be reworked without a specific user request:

- DB-backed persistence architecture
- auth/RBAC baseline
- audit trail baseline
- admin backoffice
- Docker migration-first startup
- CI baseline
- public-readiness documentation
- local Docker/PostgreSQL smoke validation

## Quick Continuation Checklist

1. Inspect `planlar.md`, `docs/current_status_and_usage.md`, and this file.
2. Run `git status --short --branch`.
3. Confirm branch `codex/postgres-numeric-snapshot` is pushed.
4. Open PR to `main`.
5. Wait for checks.
6. Merge PR.
7. Move `v2.0.0` tag to final commit.
8. Update/confirm GitHub release.
9. Optionally handle issue labels and good-first-issues.
10. Tell the user to revoke the previously shared PAT.

## Ready-To-Paste Prompt For Another Agent

```text
CurveIntel repo: C:\Users\MSI\Desktop\Test_Cihazlari_Proje\curveintel

Please continue from the current repo state, not from assumptions. First read:
- planlar.md
- docs/current_status_and_usage.md
- docs/remaining_work_handoff.md

Then run:
- git status --short --branch
- git log --oneline -8 --decorate
- git remote -v

Current known state:
- Latest fix branch is codex/postgres-numeric-snapshot.
- Remote branch origin/codex/postgres-numeric-snapshot exists.
- Latest commit is 6d36cbd, "Fix Postgres numeric snapshot persistence".
- origin/main is at 48ab33f and v2.0.0 currently points there.
- Direct push to main is blocked by branch protection and PR is required.
- The fix branch already passed local lint/tests/coverage and Docker/PostgreSQL smoke.

Your main job:
1. Open a PR from codex/postgres-numeric-snapshot to main.
2. Wait for required GitHub checks.
3. Merge the PR if checks pass.
4. Move v2.0.0 tag to the final merged main commit and update/confirm the GitHub release.
5. Optionally finish GitHub repo hygiene: issue labels and 2-3 good-first-issues.

Do not print, store, or commit any GitHub token. A PAT was previously shared in chat; after finishing, remind the user to revoke it.

Do not redo core product work unless a check fails and the failure proves a real bug. The baseline is complete; remaining work is PR/release/ops hygiene.
```
