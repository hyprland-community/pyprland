# Run tests quickly
quicktest:
    uv run pytest -q tests

# Run pytest with optional parameters
debug *params='tests':
    uv run pytest --pdb -s {{params}}

# Start the documentation website in dev mode
website: gendoc
    npm i
    npm run docs:dev

# Run linting and dead code detection
lint:
    uv run mypy --install-types --non-interactive --check-untyped-defs pyprland
    uv run ruff format pyprland
    uv run ruff check --fix pyprland
    uv run pylint -E pyprland
    uv run flake8 pyprland
    uv run vulture --ignore-names 'event_*,run_*,fromtop,frombottom,fromleft,fromright,instance' pyprland scripts/v_whitelist.py

# Run version registry checks
vreg:
    uv run --group vreg ./tests/vreg/run_tests.sh

# Build documentation
doc:
    uv run pdoc --docformat google ./pyprland

# Generate wiki pages
wiki:
    ./scripts/generate_plugin_docs.py
    ./scripts/check_plugin_docs.py

# Generate plugin documentation from source
gendoc:
    python scripts/generate_plugin_docs.py

# Generate codebase overview from module docstrings
overview:
    python scripts/generate_codebase_overview.py

# Archive documentation for a specific version (creates static snapshot)
archive-docs version:
    just gendoc
    cd site && ./make_version.sh {{version}}

# Create a new release
release:
    uv lock --upgrade
    git add uv.lock
    ./scripts/make_release

# Generate and open HTML coverage report
htmlcov:
    uv run coverage run --source=pyprland -m pytest tests -q
    uv run coverage html
    uv run coverage report
    xdg-open ./htmlcov/index.html

# Run mypy type checks on pyprland
types:
    uv run mypy --check-untyped-defs pyprland

# Build C client - release (~17K)
compile-c-client:
    gcc -O2 -o client/pypr-client client/pypr-client.c

# Build C client - debug with symbols
compile-c-client-debug:
    gcc -g -O0 -o client/pypr-client client/pypr-client.c

# Build Rust client via Cargo - release with LTO (~312K)
compile-rust-client:
    cargo build --release --manifest-path client/pypr-rs/Cargo.toml
    cp client/pypr-rs/target/release/pypr-client client/pypr-client

# Build Rust client via Cargo - debug
compile-rust-client-debug:
    cargo build --manifest-path client/pypr-rs/Cargo.toml
    cp client/pypr-rs/target/debug/pypr-client client/pypr-client

# Build Rust client via rustc - release (~375K)
compile-rust-client-simple:
    rustc -C opt-level=3 -C strip=symbols client/pypr-client.rs -o client/pypr-client

# Build Rust client via rustc - debug
compile-rust-client-simple-debug:
    rustc client/pypr-client.rs -o client/pypr-client
