pyenv := ".tox/py314-linting"
testenv := ".tox/py314-unit"

# Run pytest with optional parameters
test *params='tests':
    {{testenv}}/bin/pytest --pdb -s {{params}}

shorttest:
    {{testenv}}/bin/pytest -q

# Run all checks: unit tests, linting, and wiki generation
all:
    tox run -e unit,linting,wiki

# Start the documentation website in dev mode
website:
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

# Create a new release
release:
    ./scripts/make_release

# Generate and open HTML coverage report
htmlcov:
    tox run -e coverage
    {{pyenv}}/bin/coverage html
    xdg-open ./htmlcov/index.html

# Run mypy type checks on pyprland
types:
    {{pyenv}}/bin/mypy --check-untyped-defs pyprland

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
