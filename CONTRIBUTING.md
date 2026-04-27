# Contributing to CurveIntel

Thank you for considering contributing to CurveIntel! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.10+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/Verm1lion/CurveIntel.git
cd CurveIntel

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install with development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest --cov=src --cov=web --cov-report=term-missing
```

### Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check .         # Lint
ruff format .        # Format
```

## How to Contribute

### Reporting Bugs

- Use the [Bug Report](https://github.com/Verm1lion/CurveIntel/issues/new?template=bug_report.yml) issue template
- Include CSV sample data if possible (anonymized)
- Include the full error traceback

### Requesting Features

- Use the [Feature Request](https://github.com/Verm1lion/CurveIntel/issues/new?template=feature_request.yml) issue template
- Explain the use case and expected behavior

### Adding Vendor Support

CurveIntel supports multiple test machine vendors. To add a new vendor:

1. Study the CSV output format of the target machine
2. Create a new profile in `src/pipeline/vendor_profiles.py`
3. Add column mappings (force, displacement, stress, strain)
4. Add test data in `examples/`
5. Write tests in `tests/`
6. Submit a PR using the [Vendor Support](https://github.com/Verm1lion/CurveIntel/issues/new?template=vendor_support.yml) template

### Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `pytest`
5. Run linter: `ruff check .`
6. Commit with clear messages: `git commit -m "feat: add Besmak vendor profile"`
7. Push and create a Pull Request

### Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation only
- `test:` — Adding or updating tests
- `refactor:` — Code change that neither fixes a bug nor adds a feature
- `chore:` — Build process or auxiliary tool changes

## Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

## Questions?

Open a [Discussion](https://github.com/Verm1lion/CurveIntel/discussions) for questions, ideas, or general conversation.
