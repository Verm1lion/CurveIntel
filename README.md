# CurveIntel

[![CI](https://github.com/Verm1lion/CurveIntel/actions/workflows/ci.yml/badge.svg)](https://github.com/Verm1lion/CurveIntel/actions/workflows/ci.yml)

CurveIntel is a vendor-agnostic tensile test analysis engine for universal testing machines. It reads raw stress-strain CSV exports, computes ISO 6892-1:2019 properties, persists analysis records in a database, and exposes a FastAPI web application with authentication, RBAC, and audit logging.

See [docs/current_status_and_usage.md](docs/current_status_and_usage.md) for the current baseline status, startup options, and the real operator workflow. Release notes for this baseline are in [docs/release_notes_v2.0.0.md](docs/release_notes_v2.0.0.md).

## Current Baseline

- Deterministic tensile analysis pipeline with PDF reporting
- Database-backed result persistence via SQLAlchemy and Alembic
- Authentication endpoints with JWT cookies and role checks
- Roles: `admin`, `analyst`, `viewer`
- Append-only audit trail for auth, analysis, download, and delete actions
- Web dashboard backed by persisted results instead of an in-memory result store
- Admin backoffice panel for user management, audit filtering, and role-aware dashboard states
- PostgreSQL-ready Docker workflow with automatic `alembic upgrade head` on container startup

## Supported Vendor Profiles

| Vendor | Profile | Encoding | Separator |
| --- | --- | --- | --- |
| ZwickRoell | testXpert II/III | CP1252 | `;` |
| Instron | Bluehill Universal | UTF-8 / UTF-16 | `,` |
| Shimadzu | Trapezium X | Shift-JIS | `,` |
| MTS | TestSuite | UTF-8 | `tab` |
| Tinius Olsen | Horizon | CP1252 | `,` |
| DEVOTRANS | CKS-III | CP1254 | `;` |
| Hegewald & Peschke | LabMaster | CP1252 | `;` |
| NIST | Numisheet 2020 | UTF-8 | `,` |
| Generic CSV | Fallback auto-detection | Auto | Auto |

See [docs/vendor_integration.md](docs/vendor_integration.md) for the actual profile contract and extension workflow.

## Examples

- `examples/sample_nist.csv` is a compact NIST-style sample intended for local smoke runs and demos.
- `examples/C00Al6xxxT4Numisheet2020R01T1.521W17.91-S-Stress-Strain.csv` is a full public NIST Numisheet stress-strain sample for realistic browser uploads.
- See [examples/README.md](examples/README.md) for usage notes and provenance.

## Local Development

1. Create a virtual environment and install the project.

```shell
# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

2. Copy the environment template and set the required values.

```shell
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

When `DATABASE_URL` is unset, local development defaults to SQLite, so this works out of the box. At minimum, review:

- `JWT_SECRET_KEY` — change from the placeholder for any non-throwaway use
- `AUTH_BOOTSTRAP_ADMIN_PASSWORD` — set if you want a startup-seeded admin instead of the `/login` bootstrap form

3. Prepare the schema before starting the app.

```shell
alembic upgrade head
```

4. Run the web app.

```shell
uvicorn web.app:app --reload
```

Open `http://localhost:8000`.

To try the browser workflow with bundled data:

1. Open `/login` and bootstrap the first admin account if the database is empty.
2. Open the dashboard at `/`.
3. Upload `examples/C00Al6xxxT4Numisheet2020R01T1.521W17.91-S-Stress-Strain.csv`.
4. Confirm the result appears in the archive, then download the generated PDF report.

## Docker and PostgreSQL

1. Copy `.env.example` to `.env`, set `JWT_SECRET_KEY`, and leave `DATABASE_URL` unset unless you intentionally want to override the database target.
2. Start the stack.

```shell
docker compose up --build -d
```

The Docker Compose file sets `DATABASE_URL` to PostgreSQL automatically when no override is provided.

The `curveintel` container runs `alembic upgrade head` before starting `uvicorn`, so the schema is created or upgraded automatically.

Default services:

- `postgres`: PostgreSQL 16 on `localhost:5432`
- `curveintel`: FastAPI app on `http://localhost:8000`

## Authentication and Bootstrap

- `GET /login` serves the browser login page.
- If no users exist and `AUTH_BOOTSTRAP_ADMIN_PASSWORD` is blank, the login page shows a bootstrap form that creates the first admin.
- If `AUTH_BOOTSTRAP_ADMIN_PASSWORD` is set, startup seeds a default admin user and records a `seed` audit event.
- JWTs are issued by `POST /api/auth/login` and stored in the auth cookie configured by `AUTH_TOKEN_COOKIE_NAME`.

Role expectations:

- `admin`: full access, user registration, audit log access, delete operations
- `analyst`: upload and review results, download reports
- `viewer`: read-only access to results and reports

## API Surface

| Endpoint | Method | Access | Purpose |
| --- | --- | --- | --- |
| `/` | GET | Authenticated | Dashboard |
| `/login` | GET | Public | Login and first-admin bootstrap page |
| `/guide` | GET | Public | Usage guide |
| `/api/health` | GET | Public | Health check |
| `/api/auth/register` | POST | Public for bootstrap, admin afterwards | Create users |
| `/api/auth/login` | POST | Public | Sign in |
| `/api/auth/logout` | POST | Authenticated | Clear auth cookie |
| `/api/auth/me` | GET | Authenticated | Current user |
| `/api/users` | GET | Admin | List managed users |
| `/api/users/{id}` | PATCH | Admin | Update role and activation state |
| `/api/analyze` | POST | Admin, Analyst | Upload CSV and persist analysis |
| `/api/results` | GET | Authenticated | List persisted results |
| `/api/results/{id}` | GET | Authenticated | Read one persisted result |
| `/api/results/{id}` | DELETE | Admin | Soft-delete one result |
| `/api/results/clear` | DELETE | Admin | Soft-delete all active results |
| `/api/report/{id}/pdf` | GET | Authenticated | Download PDF report |
| `/api/audit-logs` | GET | Admin | Read recent audit events |

## Environment Contract

Important runtime variables:

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

Notes:

- In production-like environments, `JWT_SECRET_KEY` must be set explicitly.
- The application expects the database schema to be ready before serving traffic.
- For local `uvicorn` runs, execute `alembic upgrade head` yourself.
- For the Docker app container, the bundled entrypoint runs migrations automatically.
- Developer-only manual smoke scripts may also use `CURVEINTEL_DATASET_ROOT` to locate optional external datasets.

## Testing

Run the full suite:

```bash
pytest -q
pytest --cov=src --cov=web --cov-report=term-missing -q
```

The current suite covers:

- SQLite migrations
- Auth bootstrap and RBAC flows
- Audit append-only behavior
- Admin user management and role-aware dashboard rendering
- API integration for analyze, read, download, delete, and audit access

Optional live PostgreSQL smoke:

```bash
set CURVEINTEL_TEST_DATABASE_URL=postgresql+psycopg2://curveintel:curveintel@localhost:5432/curveintel
pytest -q tests/test_postgres_smoke.py
```

GitHub Actions runs this smoke flow against PostgreSQL in the dedicated `postgres-smoke` job.

## Development Notes

- Persisted database records are the source of truth for dashboard data.
- PDF generation rehydrates its report context from the persisted snapshot instead of relying on an in-memory result store.
- Admin dashboard controls are layered on top of `/api/users` and filtered `/api/audit-logs`.
- Demo data seeding is opt-in and controlled by `CURVEINTEL_LOAD_DEMO_DATA`.

## License

MIT. See [LICENSE](LICENSE).
