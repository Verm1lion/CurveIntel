# CurveIntel Current Status and Usage Guide

## 1. Current Project State

CurveIntel is currently in a stable application baseline state.

What is complete now:

- Database-backed persistence for analysis results
- JWT-based authentication with cookie-backed browser sessions
- RBAC with `admin`, `analyst`, and `viewer` roles
- Append-only audit logging for auth and result lifecycle events
- FastAPI web app with dashboard, login page, guide page, and admin backoffice
- Alembic migrations for SQLite and PostgreSQL
- Docker startup that runs `alembic upgrade head` before the app starts
- Automated test coverage for auth, DB, API, dashboard behavior, and PostgreSQL smoke

What is not a product blocker anymore:

- The app no longer depends on an in-memory result store as the primary source of truth.
- The repo no longer exposes local Windows absolute paths in manual smoke scripts.
- A compact sample dataset exists at `examples/sample_nist.csv` for quick local smoke runs.

What still remains outside product development:

- GitHub/release operations
- Demo deployment
- `v2.0.0` tag and GitHub release publication

In short: the coding phase for the baseline is complete, and the remaining work is release/ops-oriented.

## 2. Supported Runtime Modes

CurveIntel can be run in two practical ways.

### Docker + PostgreSQL

This is the closest flow to a real deployment.

1. Copy the template:

```powershell
copy .env.example .env
```

2. Set at minimum:

```env
JWT_SECRET_KEY=replace-with-a-long-random-secret
```

3. Start the stack:

```powershell
docker compose up --build -d
```

4. Open:

```text
http://localhost:8000
```

What happens in this mode:

- PostgreSQL starts on `localhost:5432`
- the `curveintel` container runs `alembic upgrade head`
- FastAPI starts only after migrations complete

### Local Development with `uvicorn`

This is the simplest developer loop.

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

2. Install the project:

```powershell
pip install -e .[dev]
```

3. Copy the environment template:

```powershell
copy .env.example .env
```

4. Set a usable local config. Example:

```env
DATABASE_URL=sqlite:///./curveintel.db
JWT_SECRET_KEY=replace-with-a-long-random-secret
AUTH_BOOTSTRAP_ADMIN_PASSWORD=
```

5. Run migrations manually:

```powershell
alembic upgrade head
```

6. Start the app:

```powershell
uvicorn web.app:app --reload
```

Important difference:

- Docker runs migrations automatically.
- Local `uvicorn` runs require `alembic upgrade head` first.

## 3. Required and Important Environment Variables

Runtime-critical variables:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `AUTH_BOOTSTRAP_ADMIN_EMAIL`
- `AUTH_BOOTSTRAP_ADMIN_FULL_NAME`
- `AUTH_BOOTSTRAP_ADMIN_PASSWORD`
- `CORS_ALLOW_ORIGINS`
- `CORS_ALLOW_METHODS`
- `CORS_ALLOW_HEADERS`
- `CORS_ALLOW_CREDENTIALS`
- `CURVEINTEL_LOAD_DEMO_DATA`
- `CURVEINTEL_DEMO_DATA_DIR`

What they matter for:

- `DATABASE_URL`: where persisted users, results, and audit logs live
- `JWT_SECRET_KEY`: signing and verifying auth tokens
- `AUTH_BOOTSTRAP_ADMIN_*`: first-admin seeding on startup
- `CORS_ALLOW_*`: browser access policy for cookie-based auth
- `CURVEINTEL_LOAD_DEMO_DATA` and `CURVEINTEL_DEMO_DATA_DIR`: optional demo data seeding

Developer-only helper variable:

- `CURVEINTEL_DATASET_ROOT`

This is not required by the web app itself. It is only used by manual smoke/diagnostic scripts to locate optional local datasets such as `nist_numisheet/`.

## 4. Authentication and First-Run Behavior

There are two valid first-run patterns.

### Bootstrap-through-login-page flow

This happens when:

- there are no users in the database
- `AUTH_BOOTSTRAP_ADMIN_PASSWORD` is blank

Behavior:

1. Visit `/login`
2. The page shows the `Bootstrap first admin` form
3. Submit name, email, and password
4. The first user is forced to role `admin`
5. Then sign in normally

### Seeded-admin flow

This happens when:

- `AUTH_BOOTSTRAP_ADMIN_PASSWORD` is set before startup

Behavior:

1. App starts
2. Lifespan hook ensures schema is ready
3. Default admin is seeded if no users exist yet
4. A `seed` audit event is written
5. You can log in immediately with the configured credentials

## 5. Real Operator Workflow

This is the real end-to-end usage flow of the product today.

### Step 1: Start the application

Use Docker or local `uvicorn` as described above.

### Step 2: Create or access an admin account

One of two things happens:

- you bootstrap the first admin from `/login`
- or you sign in with the seeded startup admin

### Step 3: Admin establishes system access

The admin can:

- use the dashboard backoffice to review current users
- update user role and activation state through the admin panel
- inspect audit trail entries

Important current detail:

- The dashboard supports managing existing users.
- New user creation is currently done through `POST /api/auth/register`.
- After bootstrap, that endpoint is admin-only.

### Step 4: Admin creates working accounts

Typical production-style setup:

- one or more `analyst` users who upload and review tests
- optional `viewer` users for read-only access
- optionally more `admin` users for operational continuity

### Step 5: Analyst uploads a CSV file

From the dashboard:

1. Click `Upload Data`
2. Choose a CSV export from the testing machine
3. The browser posts the file to `POST /api/analyze`
4. The backend stores the upload temporarily, runs the deterministic pipeline, and persists the result

What the backend does during analysis:

- reads and normalizes the vendor-style CSV
- runs ingestion, preprocessing, extraction, and anomaly checks
- builds the persisted analysis payload
- stores the result in the database
- writes audit log events for the operation

### Step 6: Results become part of the archive

After a successful upload:

- the latest persisted result becomes visible on the dashboard
- recent persisted results appear in the archive list
- the dashboard can be reopened later and still show the saved record because the DB is the source of truth

This is the key runtime truth:

- results are persisted in the database
- they are not just session-memory objects

### Step 7: Users inspect and consume outputs

Authenticated users can:

- list results through `/api/results`
- open a single result through `/api/results/{id}`
- download PDF reports through `/api/report/{id}/pdf`

The report download flow is snapshot-based:

- the report is rebuilt from the persisted snapshot
- it does not depend on a previous in-memory context surviving in RAM

### Step 8: Admin reviews system activity

Admins can:

- open the dashboard audit panel
- filter audit events by actor, action, entity type, entity id, and status
- inspect event metadata and before/after snapshots
- call `/api/audit-logs` directly if needed

Examples of auditable actions:

- register
- login
- logout
- seed
- analyze/create
- report download
- delete result
- user update

### Step 9: Admin manages cleanup and safety

Admins can:

- soft-delete one persisted result
- clear all active persisted results
- deactivate users
- change user roles

There is also a guard to prevent removing the last active admin role from the system.

## 6. Role Matrix

### `admin`

Can:

- sign in
- upload and analyze CSV files
- list and open persisted results
- download reports
- delete one result
- clear all results
- list users
- update user role or active state
- read audit logs

### `analyst`

Can:

- sign in
- upload and analyze CSV files
- list and open persisted results
- download reports

Cannot:

- delete results
- clear all results
- manage users
- read audit logs

### `viewer`

Can:

- sign in
- list and open persisted results
- download reports

Cannot:

- upload/analyze
- delete
- clear
- manage users
- read audit logs

## 7. Main API Surface

Core public/application endpoints:

- `GET /`
- `GET /login`
- `GET /guide`
- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/users`
- `PATCH /api/users/{id}`
- `POST /api/analyze`
- `GET /api/results`
- `GET /api/results/{id}`
- `DELETE /api/results/{id}`
- `DELETE /api/results/clear`
- `GET /api/report/{id}/pdf`
- `GET /api/audit-logs`

Practical usage notes:

- `/api/auth/register` is public only for the very first bootstrap user
- after bootstrap it is admin-only
- `/api/audit-logs` is admin-only
- `/api/users` endpoints are admin-only
- `/api/analyze` is `admin` or `analyst`

## 8. Browser Flow Summary

What an actual browser session looks like:

1. Anonymous user opens `/`
2. App redirects to `/login`
3. User signs in or bootstraps first admin
4. Auth cookie is set after successful login
5. Browser lands on `/`
6. Dashboard renders role-aware content

What changes by role:

- `admin` sees management surfaces
- `analyst` sees upload and operational result surfaces
- `viewer` sees a read-only workspace

## 9. Manual Smoke and Diagnostic Scripts

The repository still contains manual scripts for development and demonstration.

Examples:

- `batch_analyze.py`
- `tests/test_nist.py`
- `tests/test_pipeline.py`
- `tests/test_report.py`
- `tests/test_useries.py`
- `tests/test_validation.py`
- `tests/diagnostic_all_csv.py`

These scripts are now public-share-safe:

- they no longer hardcode a local machine path
- they use `CURVEINTEL_DATASET_ROOT` when external datasets are available
- several of them fall back to `examples/sample_nist.csv`
- scripts that require a real external dataset now exit cleanly with a setup hint instead of failing with a broken local path

Example for manual dataset setup:

```powershell
$env:CURVEINTEL_DATASET_ROOT="D:\datasets\curveintel"
python tests/test_validation.py --quick
```

## 10. Current Verification State

The baseline has already been verified through:

- `ruff check .`
- `ruff format --check .`
- `pytest -q`
- `pytest --cov=src --cov-report=term-missing -q`
- Docker + PostgreSQL smoke validation

This means the current baseline is not just documented; it has already been exercised in both SQLite-oriented tests and PostgreSQL deployment-style flow.

## 11. What Is Left

No critical product development blockers are left in the baseline phase.

What remains:

- `v2.0.0` tag and GitHub release publication
- repo settings and branch protection
- issue/release hygiene
- demo deployment

So the project is now in a public-shareable and release-prep state rather than an unfinished core-development state.
