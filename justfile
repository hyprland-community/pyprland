lintenv := ".tox/py314-linting"
testenv := ".tox/py314-unit"


quicktest:
    {{testenv}}/bin/pytest -q tests

# Run pytest with optional parameters
debug *params='tests':
    {{testenv}}/bin/pytest --pdb -s {{params}}

# Start the documentation website in dev mode
website: gendoc
    npm i
    npm run docs:dev

# Run linting and dead code detection
lint:
    tox run -e linting,deadcode

# Run version registry checks
vreg:
    tox run -e vreg

# Build documentation
doc:
    tox run -e doc

# Generate wiki pages
wiki:
    tox run -e wiki

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
    uv lock
    poetry lock
    git add poetry.lock uv.lock
    ./scripts/make_release

# Generate and open HTML coverage report
htmlcov:
    tox run -e coverage
    xdg-open ./htmlcov/index.html

# Run mypy type checks on pyprland
types:
    {{lintenv}}/bin/mypy --check-untyped-defs pyprland

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
