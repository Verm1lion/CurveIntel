# CurveIntel

[![CI](https://github.com/Verm1lion/CurveIntel/actions/workflows/ci.yml/badge.svg)](https://github.com/Verm1lion/CurveIntel/actions/workflows/ci.yml)

CurveIntel is a vendor-agnostic tensile test analysis engine for universal testing machines. It reads raw stress-strain CSV exports, computes ISO 6892-1:2019 properties, persists analysis records in a database, and exposes a FastAPI web application with authentication, RBAC, and audit logging.

## Current Baseline

- Deterministic tensile analysis pipeline with PDF reporting
- Database-backed result persistence via SQLAlchemy and Alembic
- Authentication endpoints with JWT cookies and role checks
- Roles: `admin`, `analyst`, `viewer`
- Append-only audit trail for auth, analysis, download, and delete actions
- Web dashboard backed by persisted results instead of an in-memory result store
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
- See [examples/README.md](examples/README.md) for usage notes and provenance.

## Local Development

1. Create a virtual environment and install the project.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

2. Copy the environment template and set the required values.

```bash
copy .env.example .env
```

At minimum, set:

- `JWT_SECRET_KEY`
- `DATABASE_URL` if you do not want the default PostgreSQL value
- `AUTH_BOOTSTRAP_ADMIN_PASSWORD` if you want a startup-seeded admin instead of the `/login` bootstrap form

3. Prepare the schema before starting the app.

```bash
alembic upgrade head
```

4. Run the web app.

```bash
uvicorn web.app:app --reload
```

Open `http://localhost:8000`.

## Docker and PostgreSQL

1. Copy `.env.example` to `.env` and set `JWT_SECRET_KEY`.
2. Start the stack.

```bash
docker compose up --build -d
```

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

## Testing

Run the full suite:

```bash
pytest -q
```

The current suite covers:

- SQLite migrations
- Auth bootstrap and RBAC flows
- Audit append-only behavior
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
- Demo data seeding is opt-in and controlled by `CURVEINTEL_LOAD_DEMO_DATA`.

## License

MIT. See [LICENSE](LICENSE).
