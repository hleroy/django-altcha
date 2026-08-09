# Development tasks for django-altcha-widget.
# Requires `just`: https://just.systems (or `pip install rust-just`).

python_exe := env_var_or_default("PYTHON_EXE", "python3")
venv := ".venv"
python := venv + "/bin/python"
pip := venv + "/bin/pip"
pytest := venv + "/bin/pytest"
ruff := venv + "/bin/ruff"

# List the available recipes
default:
    @just --list

# Create the virtualenv and install the development dependencies
dev:
    @echo "-> Bootstrap the virtualenv with {{ python_exe }}"
    {{ python_exe }} -m venv {{ venv }}
    {{ pip }} install --editable ".[dev]"

# Run the test suite, e.g. `just test -k widget`
test *args:
    @echo "-> Run the test suite"
    {{ pytest }} {{ args }}

# Validate formatting and linting with Ruff
check:
    @echo "-> Run Ruff linter validation (pycodestyle, bandit, isort, and more)"
    {{ ruff }} check
    @echo "-> Run Ruff format validation"
    {{ ruff }} format --check

# Apply Ruff formatting and lint autofixes
valid:
    @echo "-> Run Ruff format"
    {{ ruff }} format
    @echo "-> Run Ruff linter"
    {{ ruff }} check --fix

# Vendor the ALTCHA assets pinned in package.json
sync-altcha:
    @echo "-> Vendor the ALTCHA assets pinned in package.json"
    {{ python }} scripts/sync_altcha.py

# Verify the vendored ALTCHA assets match package.json
check-altcha:
    @echo "-> Check the vendored ALTCHA assets against package.json"
    {{ python }} scripts/sync_altcha.py --check

# Build the source and wheel distributions
dist:
    @echo "-> Build source and wheel distributions"
    {{ python }} -m build

# Remove the virtualenv and the build artifacts
clean:
    @echo "-> Clean the Python env"
    rm -rf {{ venv }} .*_cache/ *.egg-info/ build/ dist/
    find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete
